"""Edge cases and bug probes.

These assert the *expected correct* behavior for suspicious areas, so a failure
here flags a real defect rather than a test problem.
"""
import pytest


def test_unicode_fields_roundtrip(run_cli, uniq):
    owner = uniq("u")
    run_cli("user", "create", owner, "--bio", "héllo 世界 🚢")
    assert run_cli("user", "get", owner).json["bio"] == "héllo 世界 🚢"
    name = uniq("m")
    run_cli("repo", "create", f"{owner}/{name}", "--type", "model",
            "--desc", "café ☕ données", user=owner)
    assert run_cli("repo", "get", f"{owner}/{name}").json["description"] == "café ☕ données"


def test_large_file_size_roundtrip(run_cli, a_repo):
    owner, name, repo_id = a_repo
    big = 5 * 10**12  # 5 TB, exercises BIGINT
    run_cli("file", "add", repo_id, "huge.bin", "https://h.example/huge.bin",
            "--size", big, user=owner)
    assert run_cli("file", "list", repo_id).json[0]["size_bytes"] == big


def test_whitespace_only_tags_dropped(run_cli, uniq, a_user):
    name = uniq("m")
    run_cli("repo", "create", f"{a_user}/{name}", "--type", "model",
            "-t", "   ", "-t", "real", user=a_user)
    assert run_cli("repo", "get", f"{a_user}/{name}").json["tags"] == ["real"]


def test_tag_with_spaces_preserved(run_cli, uniq, a_user):
    name = uniq("m")
    run_cli("repo", "create", f"{a_user}/{name}", "--type", "model",
            "-t", "multi word tag", user=a_user)
    assert run_cli("repo", "get", f"{a_user}/{name}").json["tags"] == ["multi word tag"]


def test_search_nonexistent_returns_empty(run_cli, uniq):
    res = run_cli("repo", "list", "-q", uniq("zzdefinitelymissing"), "--limit", 50).json
    assert res["total"] == 0
    assert res["items"] == []


def test_search_matches_description(run_cli, uniq, a_user):
    marker = uniq("marker")
    name = uniq("m")
    run_cli("repo", "create", f"{a_user}/{name}", "--type", "model",
            "--desc", f"contains {marker} word", user=a_user)
    res = run_cli("repo", "list", "-q", marker, "--limit", 50).json
    assert res["total"] == 1
    assert res["items"][0]["repo_id"] == f"{a_user}/{name}"


# ---- probes for LIKE-wildcard / substring leakage ------------------------- #
def test_search_wildcard_is_literal(run_cli):
    """A query of '%' must be treated literally, not as a SQL LIKE wildcard."""
    res = run_cli("repo", "list", "-q", "%", "--limit", 5).json
    # No repo id/desc/tag literally contains '%', so this must be empty.
    assert res["total"] == 0, "user '%' is leaking through as a LIKE wildcard"


def test_search_underscore_is_literal(run_cli):
    res = run_cli("repo", "list", "-q", "_", "--limit", 5).json
    assert res["total"] == 0, "user '_' is leaking through as a LIKE wildcard"


def test_tag_filter_is_exact_not_substring(run_cli, uniq, a_user):
    """Filtering --tag 'cat' must NOT match a repo tagged 'category'."""
    name = uniq("m")
    run_cli("repo", "create", f"{a_user}/{name}", "--type", "model",
            "-t", "category", user=a_user)
    res = run_cli("repo", "list", "--owner", a_user, "--tag", "cat", "--limit", 50).json
    assert res["total"] == 0, "tag filter is matching substrings ('cat' ⊂ 'category')"


def test_tag_with_comma_splits_into_separate_tags(run_cli, uniq, a_user):
    """A comma is a tag separator: 'red,blue' normalizes to two clean tags."""
    name = uniq("m")
    run_cli("repo", "create", f"{a_user}/{name}", "--type", "model",
            "-t", "red,blue", user=a_user)
    tags = run_cli("repo", "get", f"{a_user}/{name}").json["tags"]
    assert tags == ["red", "blue"]
