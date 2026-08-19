# phase 7: the packaged app's only configuration surface. .env needs a real
# anthropic api key and vault path before topher is usable at all - this dialog
# collects both with a live validation step before ever writing the file. reused
# for both first-run (no .env yet) and the tray app's later "settings..." menu item

import os
import subprocess
import tkinter as tk
from tkinter import filedialog

from dotenv import dotenv_values, set_key

WINDOW_TITLE = "TOPHER Setup"
VALIDATION_TIMEOUT_SECONDS = 20
EMPTY_API_KEY_MESSAGE = "An Anthropic API key is required."
INVALID_VAULT_PATH_MESSAGE = "Choose a valid vault folder."
VALIDATING_MESSAGE = "Validating API key..."
INVALID_API_KEY_MESSAGE = "That API key could not be validated."


def _read_existing_values(env_file_path):
    if os.path.isfile(env_file_path) is False:
        return {"ANTHROPIC_API_KEY": "", "OBSIDIAN_VAULT_PATH": ""}

    existing_values = dotenv_values(env_file_path)
    api_key = existing_values.get("ANTHROPIC_API_KEY")
    vault_path = existing_values.get("OBSIDIAN_VAULT_PATH")

    if api_key is None:
        api_key = ""
    if vault_path is None:
        vault_path = ""

    return {"ANTHROPIC_API_KEY": api_key, "OBSIDIAN_VAULT_PATH": vault_path}


def _validate_api_key(venv_python_executable_path, api_key):
    # delegates the live check to the bundled venv's own python.exe, so the
    # frozen launcher never needs the anthropic sdk as a dependency of its own
    validation_script = (
        "import sys\n"
        "import anthropic\n"
        "client = anthropic.Anthropic(api_key=sys.argv[1])\n"
        "client.models.list(limit=1)\n"
    )
    process_result = subprocess.run(
        [venv_python_executable_path, "-c", validation_script, api_key],
        capture_output=True,
        timeout=VALIDATION_TIMEOUT_SECONDS
    )
    return process_result.returncode == 0


class SetupDialog:
    def __init__(self, env_file_path, venv_python_executable_path):
        self._env_file_path = env_file_path
        self._venv_python_executable_path = venv_python_executable_path
        self._saved_successfully = False

        existing_values = _read_existing_values(env_file_path)

        self._root = tk.Tk()
        self._root.title(WINDOW_TITLE)
        self._root.resizable(False, False)

        api_key_label = tk.Label(self._root, text="Anthropic API key")
        api_key_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))

        self._api_key_entry = tk.Entry(self._root, width=48, show="*")
        self._api_key_entry.insert(0, existing_values["ANTHROPIC_API_KEY"])
        self._api_key_entry.grid(row=1, column=0, columnspan=2, padx=10)

        vault_path_label = tk.Label(self._root, text="Obsidian vault folder")
        vault_path_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))

        self._vault_path_entry = tk.Entry(self._root, width=40)
        self._vault_path_entry.insert(0, existing_values["OBSIDIAN_VAULT_PATH"])
        self._vault_path_entry.grid(row=3, column=0, padx=(10, 0))

        browse_button = tk.Button(self._root, text="Browse...", command=self._browse_for_vault)
        browse_button.grid(row=3, column=1, padx=(4, 10))

        self._status_label = tk.Label(self._root, text="", fg="red")
        self._status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=(6, 0))

        save_button = tk.Button(self._root, text="Validate & Save", command=self._on_save)
        save_button.grid(row=5, column=0, columnspan=2, pady=10)

    def _browse_for_vault(self):
        chosen_directory = filedialog.askdirectory()
        if chosen_directory != "":
            self._vault_path_entry.delete(0, tk.END)
            self._vault_path_entry.insert(0, chosen_directory)

    def _set_status(self, message_text, text_color):
        self._status_label.config(text=message_text, fg=text_color)
        self._root.update_idletasks()

    def _on_save(self):
        api_key = self._api_key_entry.get().strip()
        vault_path = self._vault_path_entry.get().strip()

        if api_key == "":
            self._set_status(EMPTY_API_KEY_MESSAGE, "red")
            return

        if vault_path == "" or os.path.isdir(vault_path) is False:
            self._set_status(INVALID_VAULT_PATH_MESSAGE, "red")
            return

        self._set_status(VALIDATING_MESSAGE, "black")
        key_is_valid = _validate_api_key(self._venv_python_executable_path, api_key)

        if key_is_valid is False:
            self._set_status(INVALID_API_KEY_MESSAGE, "red")
            return

        set_key(self._env_file_path, "ANTHROPIC_API_KEY", api_key)
        set_key(self._env_file_path, "OBSIDIAN_VAULT_PATH", vault_path)
        self._saved_successfully = True
        self._root.destroy()

    def run(self):
        self._root.mainloop()
        return self._saved_successfully


def show_setup_dialog(env_file_path, venv_python_executable_path):
    dialog = SetupDialog(env_file_path, venv_python_executable_path)
    return dialog.run()
