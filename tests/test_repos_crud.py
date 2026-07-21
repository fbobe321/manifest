import pytest


def test_create_model(run_cli, uniq):
    owner, name = uniq("u"), uniq("m")
    r = run_cli("repo", "create", f"{owner}/{name}", "--type", "model",
                "--desc", "d", "--task", "text-generation", "--library", "transformers",
                "--license", "mit", "-t", "a", "-t", "b", user=owner)
    assert r.ok(), r.err
    got = run_cli("repo", "get", f"{owner}/{name}").json
    assert got["repo_type"] == "model"
    assert got["task"] == "text-generation"
    assert got["library"] == "transformers"
    assert got["license"] == "mit"
    assert got["tags"] == ["a", "b"]


def test_create_dataset(run_cli, uniq):
    owner, name = uniq("u"), uniq("d")
    assert run_cli("repo", "create", f"{owner}/{name}", "--type", "dataset", user=owner).ok()
    assert run_cli("repo", "get", f"{owner}/{name}").json["repo_type"] == "dataset"


def test_create_bare_name_uses_acting_user(run_cli, a_user, uniq):
    name = uniq("m")
    r = run_cli("repo", "create", name, "--type", "model", user=a_user)
    assert r.ok(), r.err
    assert r.json["repo_id"] == f"{a_user}/{name}"


def test_duplicate_create_conflicts(run_cli, a_repo):
    owner, name, repo_id = a_repo
    r = run_cli("repo", "create", repo_id, "--type", "model", user=owner)
    assert not r.ok()
    assert "already exists" in r.json["error"].lower()


def test_update_fields(run_cli, a_repo):
    owner, name, repo_id = a_repo
    r = run_cli("repo", "update", repo_id, "--desc", "new desc",
                "--task", "fill-mask", "-t", "x", "-t", "y", user=owner)
    assert r.ok(), r.err
    got = run_cli("repo", "get", repo_id).json
    assert got["description"] == "new desc"
    assert got["task"] == "fill-mask"
    assert got["tags"] == ["x", "y"]


def test_update_replaces_tags(run_cli, a_repo):
    owner, name, repo_id = a_repo
    run_cli("repo", "update", repo_id, "-t", "one", "-t", "two", user=owner)
    run_cli("repo", "update", repo_id, "-t", "solo", user=owner)
    assert run_cli("repo", "get", repo_id).json["tags"] == ["solo"]


def test_update_missing_repo_fails(run_cli, uniq):
    r = run_cli("repo", "update", f"{uniq('u')}/{uniq('m')}", "--desc", "x", user="nobody")
    assert not r.ok()


def test_delete_repo(run_cli, a_repo):
    owner, name, repo_id = a_repo
    assert run_cli("repo", "delete", repo_id, "--yes", user=owner).ok()
    assert not run_cli("repo", "get", repo_id).ok()


def test_delete_missing_repo_fails(run_cli, uniq):
    assert not run_cli("repo", "delete", f"{uniq('u')}/{uniq('m')}", "--yes").ok()


def test_like_increments(run_cli, a_repo):
    owner, name, repo_id = a_repo
    start = run_cli("repo", "get", repo_id).json["likes"]
    run_cli("repo", "like", repo_id)
    run_cli("repo", "like", repo_id)
    assert run_cli("repo", "get", repo_id).json["likes"] == start + 2


def test_download_increments(run_cli, a_repo):
    owner, name, repo_id = a_repo
    start = run_cli("repo", "get", repo_id).json["downloads"]
    run_cli("repo", "download", repo_id)
    assert run_cli("repo", "get", repo_id).json["downloads"] == start + 1


def test_card_roundtrip(run_cli, uniq, a_user):
    name = uniq("m")
    body = "# Title\n\nSome **markdown** body."
    run_cli("repo", "create", f"{a_user}/{name}", "--type", "model", "--readme", body, user=a_user)
    r = run_cli("repo", "card", f"{a_user}/{name}")
    assert r.json["readme"] == body


def test_repo_name_with_slash_rejected(run_cli, a_user):
    # "o/n/extra" -> owner=o, name="n/extra"; the name pattern forbids slashes.
    r = run_cli("repo", "create", f"{a_user}/bad/name", "--type", "model", user=a_user)
    assert not r.ok()
