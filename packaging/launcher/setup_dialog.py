# the packaged app's only first-run message: there is no API key or vault path to
# collect anymore (see decision 4 of the rescope) - the agent team authenticates
# through the Claude Code CLI's own login, using the user's Claude Pro/Max
# subscription. this is now a stateless informational dialog, not a form.

import tkinter as tk
from tkinter import messagebox

WINDOW_TITLE = "TOPHER Setup"
LOGIN_REQUIRED_MESSAGE_TEMPLATE = (
    "TOPHER's agent team runs through the Claude Code CLI, authenticated by your "
    "Claude Pro or Max subscription - no API key needed.\n\n"
    "Before TOPHER can start, open a terminal and run:\n\n"
    "    claude login\n\n"
    "The bundled CLI TOPHER uses is at:\n{claude_cli_path}\n\n"
    "Once you're logged in, reopen TOPHER."
)


def show_claude_login_required_dialog(claude_cli_path):
    # a plain informational dialog, not a form - there is nothing left to collect
    # or save. the caller (tray_app.py) is responsible for not starting the server
    # until claude login has actually happened
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(WINDOW_TITLE, LOGIN_REQUIRED_MESSAGE_TEMPLATE.format(claude_cli_path=claude_cli_path))
    root.destroy()
