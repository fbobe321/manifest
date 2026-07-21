def test_health(run_cli):
    r = run_cli("health")
    assert r.ok()
    assert r.json["status"] == "ok"


def test_stats_shape(run_cli):
    s = run_cli("stats").json
    for key in ("total_repos", "models", "datasets", "users", "total_files", "total_size_bytes"):
        assert key in s and isinstance(s[key], int)


def test_stats_track_creation(api, run_cli, uniq):
    before = run_cli("stats").json
    owner = uniq("user")
    name = uniq("model")
    assert run_cli("repo", "create", f"{owner}/{name}", "--type", "model", user=owner).ok()
    after = run_cli("stats").json
    assert after["total_repos"] == before["total_repos"] + 1
    assert after["models"] == before["models"] + 1
    assert after["users"] >= before["users"] + 1


def test_stats_size_tracks_files(run_cli, a_repo):
    owner, name, repo_id = a_repo
    before = run_cli("stats").json
    assert run_cli("file", "add", repo_id, "w.bin", "https://h.example/w.bin",
                   "--size", 1000, user=owner).ok()
    after = run_cli("stats").json
    assert after["total_files"] == before["total_files"] + 1
    assert after["total_size_bytes"] == before["total_size_bytes"] + 1000
