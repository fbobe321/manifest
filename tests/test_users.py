def test_create_and_get_user(run_cli, uniq):
    name = uniq("user")
    r = run_cli("user", "create", name, "--name", "Full Name", "--bio", "hello")
    assert r.ok(), r.err
    assert r.json["username"] == name

    prof = run_cli("user", "get", name).json
    assert prof["username"] == name
    assert prof["full_name"] == "Full Name"
    assert prof["bio"] == "hello"
    assert prof["repositories"] == []


def test_user_list_contains_created(run_cli, uniq):
    name = uniq("user")
    run_cli("user", "create", name)
    users = run_cli("user", "list").json
    assert any(u["username"] == name for u in users)


def test_create_user_is_idempotent(api, uniq):
    name = uniq("user")
    r1 = api.post("/users", {"username": name, "full_name": "First"})
    r2 = api.post("/users", {"username": name, "full_name": "Second"})
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)
    # Second create must not duplicate or error; same identity comes back.
    assert r2.json()["username"] == name


def test_profile_lists_owned_repos(run_cli, uniq):
    owner = uniq("user")
    run_cli("user", "create", owner)
    m = uniq("m")
    d = uniq("d")
    run_cli("repo", "create", f"{owner}/{m}", "--type", "model", user=owner)
    run_cli("repo", "create", f"{owner}/{d}", "--type", "dataset", user=owner)
    prof = run_cli("user", "get", owner).json
    ids = {r["repo_id"] for r in prof["repositories"]}
    assert ids == {f"{owner}/{m}", f"{owner}/{d}"}


def test_get_missing_user_fails(run_cli, uniq):
    r = run_cli("user", "get", uniq("nope"))
    assert not r.ok()
    assert "error" in r.json


def test_invalid_username_rejected(api):
    r = api.post("/users", {"username": "has space"})
    assert r.status_code == 422


def test_empty_username_rejected(api):
    r = api.post("/users", {"username": ""})
    assert r.status_code == 422
