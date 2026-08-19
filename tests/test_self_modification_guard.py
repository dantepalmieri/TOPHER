# codifies the one-off manual verification pass documented in the readme's phase 6
# history as a permanent regression gate - this is the highest-stakes logic in the
# project, since a hole here would let self-improvement mode touch its own guardrails
# or secrets

from second_brain.agents.self_modification_guard import (
    _bash_command_touches_protected_entry,
    _path_touches_protected_entry,
    _search_root_reaches_protected_entry,
)
from second_brain.config import PROJECT_ROOT_DIRECTORY

SELF_IMPROVE_CWD = PROJECT_ROOT_DIRECTORY


def test_denies_env_file():
    assert _path_touches_protected_entry(".env", SELF_IMPROVE_CWD) is True


def test_denies_config_py():
    assert _path_touches_protected_entry("second_brain/config.py", SELF_IMPROVE_CWD) is True


def test_denies_self_modification_guard_itself():
    guard_path = "second_brain/agents/self_modification_guard.py"
    assert _path_touches_protected_entry(guard_path, SELF_IMPROVE_CWD) is True


def test_denies_git_directory():
    assert _path_touches_protected_entry(".git", SELF_IMPROVE_CWD) is True


def test_denies_path_inside_git_directory():
    assert _path_touches_protected_entry(".git/config", SELF_IMPROVE_CWD) is True


def test_denies_venv_directory():
    assert _path_touches_protected_entry("venv", SELF_IMPROVE_CWD) is True


def test_allows_readme():
    assert _path_touches_protected_entry("README.md", SELF_IMPROVE_CWD) is False


def test_allows_prompt_file_edit():
    # the prompt/wiring split is the whole point of phase 6's design - the team
    # must still be able to improve its own personality
    prompt_path = "second_brain/agents/developer_prompt.py"
    assert _path_touches_protected_entry(prompt_path, SELF_IMPROVE_CWD) is False


def test_allows_workspace_file():
    assert _path_touches_protected_entry("workspace/add.py", SELF_IMPROVE_CWD) is False


def test_denies_unscoped_search_from_project_root():
    # an unscoped grep/glob from the project root never names .env directly, but
    # walks straight through it - the ancestor-direction check this guards against
    assert _search_root_reaches_protected_entry(SELF_IMPROVE_CWD, SELF_IMPROVE_CWD) is True


def test_denies_search_scoped_to_agents_directory():
    # this directory contains several protected files (self_modification_guard.py,
    # workspace_guard.py, config.py's sibling agent modules)
    assert _search_root_reaches_protected_entry("second_brain/agents", SELF_IMPROVE_CWD) is True


def test_allows_search_scoped_to_vault_directory():
    # no protected entry lives under second_brain/vault - a legitimate, safely
    # scoped search
    assert _search_root_reaches_protected_entry("second_brain/vault", SELF_IMPROVE_CWD) is False


def test_denies_bash_relative_path_to_env_file():
    assert _bash_command_touches_protected_entry("cat .env", SELF_IMPROVE_CWD) is True


def test_denies_bash_mklink_command():
    command_text = "mklink C:\\evil C:\\Users\\palmi\\obsidian-claude\\.env"
    assert _bash_command_touches_protected_entry(command_text, SELF_IMPROVE_CWD) is True


def test_denies_bash_fsutil_hardlink_command():
    command_text = "fsutil hardlink create link.txt .env"
    assert _bash_command_touches_protected_entry(command_text, SELF_IMPROVE_CWD) is True


def test_denies_bash_powershell_symlink_command():
    command_text = "New-Item -ItemType SymbolicLink -Path link -Target .env"
    assert _bash_command_touches_protected_entry(command_text, SELF_IMPROVE_CWD) is True


def test_allows_bash_git_commit_with_no_protected_token():
    # this is the exact mechanism "the team may commit directly" relies on - a
    # plain git commit has no denylisted path token in it
    command_text = "git commit -m \"improve error messages\""
    assert _bash_command_touches_protected_entry(command_text, SELF_IMPROVE_CWD) is False


def test_denies_bash_git_add_of_protected_file():
    command_text = "git add second_brain/config.py"
    assert _bash_command_touches_protected_entry(command_text, SELF_IMPROVE_CWD) is True


def test_allows_bash_unrelated_command():
    assert _bash_command_touches_protected_entry("pytest workspace/test_add.py", SELF_IMPROVE_CWD) is False
