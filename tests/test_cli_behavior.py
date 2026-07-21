import json as jsonlib


def test_help_lists_groups(run_cli):
    r = run_cli("--help", json=False)
    assert r.ok()
    for word in ("repo", "file", "user", "stats"):
        assert word in r.out


def test_json_flag_emits_valid_json(run_cli, a_repo):
    owner, name, repo_id = a_repo
    r = run_cli("repo", "get", repo_id)
    jsonlib.loads(r.out)  # must parse


def test_human_output_is_not_json(run_cli, a_repo):
    owner, name, repo_id = a_repo
    r = run_cli("repo", "get", repo_id, json=False)
    assert r.ok()
    assert repo_id in r.out


def test_error_exit_code_and_payload(run_cli, uniq):
    r = run_cli("repo", "get", f"{uniq('u')}/{uniq('m')}")
    assert r.code == 1
    assert "error" in r.json


def test_bare_name_without_user_errors(run_cli, uniq, tmp_path):
    # No --as and an empty config dir -> no acting user available.
    r = run_cli("repo", "create", uniq("m"), "--type", "model",
                config_dir=tmp_path / "empty")
    assert r.code == 1
    assert "acting user" in r.json["error"].lower()


def test_login_whoami_logout_flow(run_cli, uniq, tmp_path):
    cfg = tmp_path / "session"
    name = uniq("user")
    assert run_cli("login", name, config_dir=cfg).ok()
    who = run_cli("whoami", config_dir=cfg).json
    assert who["user"] == name
    # A bare-name create now works because the saved user is the owner.
    assert run_cli("repo", "create", uniq("m"), "--type", "model", config_dir=cfg).ok()
    assert run_cli("logout", config_dir=cfg).ok()
    assert run_cli("whoami", config_dir=cfg).json["user"] is None


def test_config_set_url(run_cli, base_url, tmp_path):
    cfg = tmp_path / "cfg"
    # Set URL in config, then call WITHOUT --url by using a raw command.
    assert run_cli("cfg", "set-url", base_url, config_dir=cfg).ok()
    shown = run_cli("cfg", "show", config_dir=cfg).json
    assert shown["url"] == base_url


def test_repo_url_command(run_cli, a_repo, base_url):
    owner, name, repo_id = a_repo
    r = run_cli("repo", "url", repo_id)
    assert r.json["url"] == f"{base_url}/{owner}/{name}"
