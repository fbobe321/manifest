"""Direct API validation / boundary checks."""
import pytest


def test_bad_repo_type_rejected(api, uniq):
    r = api.post("/repos", {"owner": uniq("u"), "name": uniq("m"), "repo_type": "banana"})
    assert r.status_code == 422


def test_description_max_length(api, uniq):
    owner, name = uniq("u"), uniq("m")
    ok = api.post("/repos", {"owner": owner, "name": name, "repo_type": "model",
                             "description": "d" * 280})
    assert ok.status_code == 201
    too_long = api.post("/repos", {"owner": uniq("u"), "name": uniq("m"),
                                   "repo_type": "model", "description": "d" * 281})
    assert too_long.status_code == 422


def test_name_pattern_enforced(api, uniq):
    r = api.post("/repos", {"owner": uniq("u"), "name": "bad name!", "repo_type": "model"})
    assert r.status_code == 422


@pytest.mark.parametrize("limit", [0, 101, -1])
def test_list_limit_bounds(api, limit):
    r = api.get("/repos", limit=limit)
    assert r.status_code == 422


def test_negative_offset_rejected(api):
    assert api.get("/repos", offset=-1).status_code == 422


def test_like_missing_repo_404(api, uniq):
    assert api.post(f"/repos/{uniq('u')}/{uniq('m')}/like").status_code == 404


def test_delete_file_missing_404(api, uniq):
    owner, name = uniq("u"), uniq("m")
    api.post("/repos", {"owner": owner, "name": name, "repo_type": "model"})
    assert api.delete(f"/repos/{owner}/{name}/files/999999").status_code == 404


def test_create_repo_missing_required_fields(api):
    assert api.post("/repos", {"name": "x", "repo_type": "model"}).status_code == 422
