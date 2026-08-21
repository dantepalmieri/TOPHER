# confirms the path-resolution logic every other module in this project leans on -
# a packaged install only works correctly if these paths stay siblings under one
# project root no matter what absolute path the project lives at

import os

from second_brain import config


def test_project_root_directory_is_parent_of_second_brain_package():
    second_brain_package_directory = os.path.dirname(os.path.abspath(config.__file__))
    expected_root = os.path.dirname(second_brain_package_directory)
    assert config.PROJECT_ROOT_DIRECTORY == expected_root


def test_env_file_path_is_direct_child_of_project_root():
    expected_path = os.path.join(config.PROJECT_ROOT_DIRECTORY, ".env")
    assert config.ENV_FILE_PATH == expected_path


def test_dashboard_database_path_is_direct_child_of_project_root():
    expected_path = os.path.join(config.PROJECT_ROOT_DIRECTORY, "dashboard.db")
    assert config.DASHBOARD_DATABASE_PATH == expected_path


def test_team_workspace_directory_path_is_direct_child_of_project_root():
    expected_path = os.path.join(config.PROJECT_ROOT_DIRECTORY, "workspace")
    assert config.TEAM_WORKSPACE_DIRECTORY_PATH == expected_path


def test_venv_python_executable_path_matches_embeddable_python_layout():
    # no Scripts\ subfolder - build_venv.ps1 builds this from python.org's
    # embeddable distribution, not `python -m venv` (see build_venv.ps1 for why)
    expected_path = os.path.join(config.PROJECT_ROOT_DIRECTORY, "venv", "python.exe")
    assert config.VENV_PYTHON_EXECUTABLE_PATH == expected_path


def test_dashboard_server_host_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("DASHBOARD_SERVER_HOST", raising=False)
    import importlib
    reloaded_config = importlib.reload(config)
    assert reloaded_config.DASHBOARD_SERVER_HOST == "127.0.0.1"
    importlib.reload(config)
