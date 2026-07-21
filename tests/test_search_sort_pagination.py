import pytest


@pytest.fixture
def dataset_group(run_cli, uniq):
    """A user with several tagged repos for search/sort/paging tests."""
    owner = uniq("srch")
    run_cli("user", "create", owner)
    tag = uniq("tag")
    made = []
    for i in range(5):
        name = f"m{i}-{uniq('n')}"
        run_cli("repo", "create", f"{owner}/{name}", "--type",
                "model" if i % 2 == 0 else "dataset", "-t", tag,
                "--task", "text-generation", user=owner)
        made.append(f"{owner}/{name}")
    return owner, tag, made


def test_search_by_owner(run_cli, dataset_group):
    owner, tag, made = dataset_group
    res = run_cli("repo", "list", "--owner", owner, "--limit", 50).json
    assert res["total"] == 5
    assert {r["repo_id"] for r in res["items"]} == set(made)


def test_search_by_tag(run_cli, dataset_group):
    owner, tag, made = dataset_group
    res = run_cli("repo", "list", "--tag", tag, "--limit", 50).json
    assert res["total"] == 5


def test_filter_by_type(run_cli, dataset_group):
    owner, tag, made = dataset_group
    models = run_cli("repo", "list", "--owner", owner, "--type", "model", "--limit", 50).json
    assert all(r["repo_type"] == "model" for r in models["items"])
    assert models["total"] == 3


def test_query_search(run_cli, dataset_group):
    owner, tag, made = dataset_group
    res = run_cli("repo", "search", owner, "--limit", 50).json
    assert res["total"] >= 5


def test_query_is_case_insensitive(run_cli, dataset_group):
    owner, tag, made = dataset_group
    res = run_cli("repo", "list", "-q", owner.upper(), "--limit", 50).json
    assert res["total"] >= 5


def test_pagination(run_cli, dataset_group):
    owner, tag, made = dataset_group
    page1 = run_cli("repo", "list", "--owner", owner, "--limit", 2, "--offset", 0).json
    page2 = run_cli("repo", "list", "--owner", owner, "--limit", 2, "--offset", 2).json
    assert page1["total"] == page2["total"] == 5
    assert len(page1["items"]) == 2 and len(page2["items"]) == 2
    ids1 = {r["repo_id"] for r in page1["items"]}
    ids2 = {r["repo_id"] for r in page2["items"]}
    assert ids1.isdisjoint(ids2)  # no overlap between pages


@pytest.mark.parametrize("sort", ["trending", "recent", "downloads", "likes", "created", "name"])
def test_sort_options_work(run_cli, dataset_group, sort):
    owner, tag, made = dataset_group
    res = run_cli("repo", "list", "--owner", owner, "--sort", sort, "--limit", 50)
    assert res.ok(), res.err
    assert res.json["total"] == 5


def test_sort_by_likes_orders_desc(run_cli, dataset_group):
    owner, tag, made = dataset_group
    run_cli("repo", "like", made[3])
    run_cli("repo", "like", made[3])
    run_cli("repo", "like", made[1])
    res = run_cli("repo", "list", "--owner", owner, "--sort", "likes", "--limit", 50).json
    likes = [r["likes"] for r in res["items"]]
    assert likes == sorted(likes, reverse=True)
    assert res["items"][0]["repo_id"] == made[3]


def test_facets_reflect_data(run_cli, dataset_group):
    owner, tag, made = dataset_group
    facets = run_cli("facets").json
    tasks = {t["value"]: t["count"] for t in facets["tasks"]}
    assert tasks.get("text-generation", 0) >= 5
    tagvals = {t["value"] for t in facets["tags"]}
    assert tag in tagvals
