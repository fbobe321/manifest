def test_add_and_list_file(run_cli, a_repo):
    owner, name, repo_id = a_repo
    r = run_cli("file", "add", repo_id, "model.safetensors",
                "https://cdn.example/model.safetensors", "--size", 2048, user=owner)
    assert r.ok(), r.err
    files = run_cli("file", "list", repo_id).json
    assert len(files) == 1
    assert files[0]["filename"] == "model.safetensors"
    assert files[0]["size_bytes"] == 2048
    assert files[0]["url"] == "https://cdn.example/model.safetensors"


def test_size_mb_conversion(run_cli, a_repo):
    owner, name, repo_id = a_repo
    run_cli("file", "add", repo_id, "big.bin", "https://h.example/big.bin",
            "--size-mb", 2, user=owner)
    files = run_cli("file", "list", repo_id).json
    assert files[0]["size_bytes"] == 2 * 1024 * 1024


def test_duplicate_filename_conflicts(run_cli, a_repo):
    owner, name, repo_id = a_repo
    run_cli("file", "add", repo_id, "a.bin", "https://h.example/a.bin", user=owner)
    r = run_cli("file", "add", repo_id, "a.bin", "https://h.example/a2.bin", user=owner)
    assert not r.ok()


def test_remove_file(run_cli, a_repo):
    owner, name, repo_id = a_repo
    add = run_cli("file", "add", repo_id, "x.bin", "https://h.example/x.bin", user=owner)
    fid = add.json["id"]
    assert run_cli("file", "rm", repo_id, fid, "--yes", user=owner).ok()
    assert run_cli("file", "list", repo_id).json == []


def test_files_included_in_repo_detail(run_cli, a_repo):
    owner, name, repo_id = a_repo
    run_cli("file", "add", repo_id, "c.json", "https://h.example/c.json", "--size", 10, user=owner)
    detail = run_cli("repo", "get", repo_id).json
    assert detail["num_files"] == 1
    assert detail["total_size_bytes"] == 10
    assert detail["files"][0]["filename"] == "c.json"


def test_delete_repo_cascades_files(api, run_cli, a_repo):
    owner, name, repo_id = a_repo
    run_cli("file", "add", repo_id, "z.bin", "https://h.example/z.bin", user=owner)
    run_cli("repo", "delete", repo_id, "--yes", user=owner)
    # Re-create the same repo id: it must come back with zero files (no orphans).
    run_cli("repo", "create", repo_id, "--type", "model", user=owner)
    assert run_cli("repo", "get", repo_id).json["files"] == []


def test_add_file_bad_url_rejected(api, a_repo):
    owner, name, repo_id = a_repo
    r = api.post(f"/repos/{owner}/{name}/files",
                 {"filename": "x", "url": "not-a-url", "size_bytes": 1})
    assert r.status_code == 422


def test_add_file_negative_size_rejected(api, a_repo):
    owner, name, repo_id = a_repo
    r = api.post(f"/repos/{owner}/{name}/files",
                 {"filename": "x", "url": "https://h.example/x", "size_bytes": -1})
    assert r.status_code == 422


def test_add_file_missing_repo_fails(run_cli, uniq):
    r = run_cli("file", "add", f"{uniq('u')}/{uniq('m')}", "f", "https://h.example/f")
    assert not r.ok()
