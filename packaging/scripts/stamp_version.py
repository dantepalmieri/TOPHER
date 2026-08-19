# phase 7: single source of truth for the release version - reads pyproject.toml
# once and prints it to stdout, so every build script (powershell, ISCC, pyinstaller)
# derives the same version string instead of each hand-repeating it

import os
import tomllib

THIS_FILE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIRECTORY = os.path.dirname(os.path.dirname(THIS_FILE_DIRECTORY))
PYPROJECT_FILE_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "pyproject.toml")


def read_project_version():
    with open(PYPROJECT_FILE_PATH, "rb") as pyproject_file:
        pyproject_data = tomllib.load(pyproject_file)
    return pyproject_data["project"]["version"]


if __name__ == "__main__":
    print(read_project_version())
