"""Thin REST client over the Manifest API. Every site operation lives here."""
from __future__ import annotations

import requests


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class Client:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # -- low level -------------------------------------------------------- #
    def _request(self, method: str, path: str, **kw):
        url = f"{self.base}/api{path}"
        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kw)
        except requests.RequestException as e:
            raise ApiError(f"Cannot reach server at {self.base}: {e}") from e
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except ValueError:
                pass
            if isinstance(detail, list):  # pydantic validation errors
                detail = "; ".join(
                    f"{'.'.join(str(p) for p in d.get('loc', []))}: {d.get('msg')}" for d in detail
                )
            raise ApiError(str(detail), resp.status_code)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def get(self, path, **params):
        clean = {k: v for k, v in params.items() if v is not None}
        return self._request("GET", path, params=clean)

    def post(self, path, body=None):
        return self._request("POST", path, json=body)

    def put(self, path, body=None):
        return self._request("PUT", path, json=body)

    def delete(self, path):
        return self._request("DELETE", path)

    # -- meta ------------------------------------------------------------- #
    def health(self):
        return self.get("/health")

    def stats(self):
        return self.get("/stats")

    def facets(self, repo_type=None):
        return self.get("/facets", repo_type=repo_type)

    # -- users ------------------------------------------------------------ #
    def create_user(self, username, full_name="", bio=""):
        return self.post("/users", {"username": username, "full_name": full_name, "bio": bio})

    def list_users(self):
        return self.get("/users")

    def get_user(self, username):
        return self.get(f"/users/{username}")

    # -- repositories ----------------------------------------------------- #
    def list_repos(self, **filters):
        return self.get("/repos", **filters)

    def get_repo(self, owner, name):
        return self.get(f"/repos/{owner}/{name}")

    def create_repo(self, **body):
        return self.post("/repos", body)

    def update_repo(self, owner, name, **body):
        clean = {k: v for k, v in body.items() if v is not None}
        return self.put(f"/repos/{owner}/{name}", clean)

    def delete_repo(self, owner, name):
        return self.delete(f"/repos/{owner}/{name}")

    def like_repo(self, owner, name):
        return self.post(f"/repos/{owner}/{name}/like")

    def register_download(self, owner, name):
        return self.post(f"/repos/{owner}/{name}/download")

    # -- files ------------------------------------------------------------ #
    def add_file(self, owner, name, filename, url, size_bytes=0):
        return self.post(
            f"/repos/{owner}/{name}/files",
            {"filename": filename, "url": url, "size_bytes": size_bytes},
        )

    def delete_file(self, owner, name, file_id):
        return self.delete(f"/repos/{owner}/{name}/files/{file_id}")
