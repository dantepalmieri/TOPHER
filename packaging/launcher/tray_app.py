# phase 7: the packaged app's process supervisor. deliberately kept small and
# free of heavy dependencies (pystray, pillow, pywin32, stdlib only) so it can be
# pyinstaller-frozen on its own, separately from the ml-heavy backend - the actual
# dashboard server always runs through the bundled venv's own python.exe as a
# subprocess, never imported into this process directly

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

import win32com.client
from PIL import Image, ImageDraw
import pystray

LAUNCHER_ICON_TITLE = "TOPHER"
STARTUP_SHORTCUT_NAME = "TOPHER.lnk"
SETTINGS_ARGUMENT = "--settings"
# generous, and empirically justified, not guessed: measured directly against
# two separate fresh installer runs (fresh venv copy, never executed before) -
# first launch took ~90 seconds one time and ~150 seconds another, right up
# against the timeout that was set from the first measurement alone. almost
# certainly windows defender's real-time scanner inspecting torch/onnxruntime's
# many never-before-seen dlls on first execution, with enough variance run to
# run that one data point wasn't safe to treat as a ceiling. every launch
# after the first is fast (observed well under 10s) once those files are
# marked clean. real headroom above the worst case actually observed, not
# just above the average
SERVER_START_TIMEOUT_SECONDS = 240
SERVER_READY_POLL_INTERVAL_SECONDS = 0.5

# the running-state icon color - matches the "T" favicon in the dashboard
# frontend (dashboard-frontend/public/favicon.svg) so the tray icon and the
# browser tab read as the same brand rather than two unrelated colors
TOPHER_ORANGE = "#e8791f"


def _resolve_install_directory():
    # when frozen by pyinstaller, sys.executable is the launcher exe itself,
    # sitting directly inside the installed app directory. when run unfrozen
    # (local development), walk up from packaging/launcher/tray_app.py to the
    # project root three directories up
    if getattr(sys, "frozen", False) is True:
        return os.path.dirname(sys.executable)
    this_file_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(this_file_directory))


def _resolve_launcher_executable_path():
    if getattr(sys, "frozen", False) is True:
        return sys.executable
    return os.path.abspath(__file__)


INSTALL_DIRECTORY = _resolve_install_directory()
LAUNCHER_EXECUTABLE_PATH = _resolve_launcher_executable_path()

# importing second_brain.config here is deliberate and safe: that module's own
# imports are just os + python-dotenv, nothing from the ml-heavy stack, and
# inserting INSTALL_DIRECTORY onto sys.path first means PROJECT_ROOT_DIRECTORY
# resolves to the installed location automatically, with zero path duplication
sys.path.insert(0, INSTALL_DIRECTORY)
from second_brain.config import (
    DASHBOARD_SERVER_HOST,
    DASHBOARD_SERVER_PORT,
    ENV_FILE_PATH,
    OBSIDIAN_VAULT_PATH,
    VENV_PYTHON_EXECUTABLE_PATH
)

from setup_dialog import show_setup_dialog

# cosmetic only - the readiness check and the actual server bind still use
# DASHBOARD_SERVER_HOST exactly as configured. "localhost" is just nicer to
# read in a browser tab than the bare loopback address; a real remote/tailscale
# host the user has deliberately configured is shown as-is, since "localhost"
# would be actively wrong for that case
if DASHBOARD_SERVER_HOST == "127.0.0.1":
    DASHBOARD_DISPLAY_HOST = "localhost"
else:
    DASHBOARD_DISPLAY_HOST = DASHBOARD_SERVER_HOST

DASHBOARD_URL = "http://" + DASHBOARD_DISPLAY_HOST + ":" + str(DASHBOARD_SERVER_PORT) + "/"
LOG_DIRECTORY = os.path.join(os.environ["LOCALAPPDATA"], "TOPHER", "logs")
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "dashboard.log")


def _configuration_looks_complete():
    # ANTHROPIC_API_KEY has no second_brain.config constant of its own - the
    # anthropic sdk reads it straight from the environment itself, so this is
    # the only place that needs to check it directly
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return api_key != "" and OBSIDIAN_VAULT_PATH.strip() != ""


def _startup_shortcut_path():
    startup_folder = os.path.join(
        os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    return os.path.join(startup_folder, STARTUP_SHORTCUT_NAME)


def _startup_shortcut_exists():
    return os.path.isfile(_startup_shortcut_path())


def _create_startup_shortcut():
    windows_shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = windows_shell.CreateShortCut(_startup_shortcut_path())
    shortcut.TargetPath = LAUNCHER_EXECUTABLE_PATH
    shortcut.WorkingDirectory = INSTALL_DIRECTORY
    shortcut.IconLocation = LAUNCHER_EXECUTABLE_PATH
    shortcut.save()


def _remove_startup_shortcut():
    shortcut_path = _startup_shortcut_path()
    if os.path.isfile(shortcut_path) is True:
        os.remove(shortcut_path)


def _wait_for_server_ready(timeout_seconds):
    # a plain tcp connect check is enough here - no need for a full http
    # request just to confirm the server has finished starting and is
    # accepting connections
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            probe_connection = socket.create_connection(
                (DASHBOARD_SERVER_HOST, DASHBOARD_SERVER_PORT), timeout=1
            )
            probe_connection.close()
            return True
        except OSError:
            time.sleep(SERVER_READY_POLL_INTERVAL_SECONDS)

    return False


def _build_tray_icon_image(status_color):
    # drawn procedurally rather than shipped as a static asset - a plain circle
    # with a "T" is enough to be recognizable in the tray and to show status
    # (orange = running, gray = stopped, red = error) at a glance
    image_size = 64
    icon_image = Image.new("RGBA", (image_size, image_size), (0, 0, 0, 0))
    drawing_context = ImageDraw.Draw(icon_image)
    drawing_context.ellipse((2, 2, image_size - 2, image_size - 2), fill=status_color)
    drawing_context.rectangle((18, 16, 46, 24), fill="white")
    drawing_context.rectangle((28, 16, 36, 48), fill="white")
    return icon_image


class TopherTrayApp:
    def __init__(self):
        self._dashboard_process = None
        self._process_lock = threading.Lock()
        self._icon = pystray.Icon(
            LAUNCHER_ICON_TITLE,
            _build_tray_icon_image("gray"),
            LAUNCHER_ICON_TITLE,
            menu=self._build_menu()
        )

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._on_open_dashboard, default=True),
            pystray.MenuItem("Restart Server", self._on_restart_server),
            pystray.MenuItem("Stop Server", self._on_stop_server, enabled=self._is_server_running),
            pystray.MenuItem("View Logs", self._on_view_logs),
            pystray.MenuItem("Settings...", self._on_open_settings),
            pystray.MenuItem(
                "Start on Login",
                self._on_toggle_start_on_login,
                checked=lambda menu_item: _startup_shortcut_exists()
            ),
            pystray.MenuItem("Exit", self._on_exit)
        )

    def _is_server_running(self, menu_item=None):
        with self._process_lock:
            if self._dashboard_process is None:
                return False
            return self._dashboard_process.poll() is None

    def _start_server(self):
        with self._process_lock:
            if self._dashboard_process is not None and self._dashboard_process.poll() is None:
                return

            os.makedirs(LOG_DIRECTORY, exist_ok=True)
            log_file = open(LOG_FILE_PATH, "a", encoding="utf-8")
            self._dashboard_process = subprocess.Popen(
                [VENV_PYTHON_EXECUTABLE_PATH, "-m", "second_brain.dashboard.server"],
                cwd=INSTALL_DIRECTORY,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        # loading the embedding model at import time (semantic_search.py) makes
        # startup take a real, noticeable few seconds - block here and reflect
        # actual readiness in the icon color rather than flipping to green the
        # instant the process merely exists
        server_became_ready = _wait_for_server_ready(SERVER_START_TIMEOUT_SECONDS)
        if server_became_ready is True:
            self._icon.icon = _build_tray_icon_image(TOPHER_ORANGE)
        else:
            self._icon.icon = _build_tray_icon_image("red")
        self._icon.update_menu()

    def _stop_server(self):
        with self._process_lock:
            if self._dashboard_process is None:
                return
            if self._dashboard_process.poll() is None:
                # windows offers no reliable graceful-shutdown signal here for a
                # console-less child process; every dashboard write is already
                # a committed sqlite transaction, so a hard terminate is safe
                self._dashboard_process.terminate()
                self._dashboard_process.wait()
            self._dashboard_process = None

        self._icon.icon = _build_tray_icon_image("gray")
        self._icon.update_menu()

    def _on_open_dashboard(self, icon, menu_item):
        if self._is_server_running() is False:
            self._start_server()
        webbrowser.open(DASHBOARD_URL)

    def _on_restart_server(self, icon, menu_item):
        self._stop_server()
        self._start_server()

    def _on_stop_server(self, icon, menu_item):
        self._stop_server()

    def _on_view_logs(self, icon, menu_item):
        os.makedirs(LOG_DIRECTORY, exist_ok=True)
        os.startfile(LOG_FILE_PATH)

    def _on_open_settings(self, icon, menu_item):
        subprocess.Popen([LAUNCHER_EXECUTABLE_PATH, SETTINGS_ARGUMENT], cwd=INSTALL_DIRECTORY)

    def _on_toggle_start_on_login(self, icon, menu_item):
        if _startup_shortcut_exists() is True:
            _remove_startup_shortcut()
        else:
            _create_startup_shortcut()
        self._icon.update_menu()

    def _on_exit(self, icon, menu_item):
        self._stop_server()
        self._icon.stop()

    def run(self):
        self._start_server()
        self._icon.run()


def main():
    if SETTINGS_ARGUMENT in sys.argv:
        show_setup_dialog(ENV_FILE_PATH, VENV_PYTHON_EXECUTABLE_PATH)
        return

    if _configuration_looks_complete() is False:
        configuration_was_saved = show_setup_dialog(ENV_FILE_PATH, VENV_PYTHON_EXECUTABLE_PATH)
        if configuration_was_saved is False:
            return

    tray_app = TopherTrayApp()
    tray_app.run()


if __name__ == "__main__":
    main()
