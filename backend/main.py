"""FastAPI application: a local, self-hosted model & dataset repository.

Users create model/dataset repositories, write a markdown card, and list files
as external links (the bytes live on other servers — we only store the link).
Serves a JSON API under /api and the compiled React SPA for everything else,
so the whole product ships as a single hardened container (see PRD.md).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

import seed
from config import get_settings
from database import SessionLocal, get_session, init_db
from models import RepoFile, Repository, User
from schemas import (
    Facets,
    FacetValue,
    RepoCreate,
    RepoDetail,
    RepoFileCreate,
    RepoFileOut,
    RepoPage,
    RepoSummary,
    RepoUpdate,
    Stats,
    UserCreate,
    UserOut,
    UserProfile,
)

settings = get_settings()
STATIC_DIR = Path(settings.static_dir)
INDEX_HTML = STATIC_DIR / "index.html"

app = FastAPI(title="Local AI Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed.seed_if_empty(db)


def _like_escape(term: str) -> str:
    """Escape LIKE wildcards so user input can't act as a pattern."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _normalize_tags(tags: list[str]) -> str:
    """Flatten/trim/dedupe tags into CSV. Commas are separators, so a value
    like 'a,b' becomes two tags; individual tags therefore never contain commas.
    """
    seen: list[str] = []
    for raw in tags:
        for part in raw.split(","):
            part = part.strip()
            if part and part not in seen:
                seen.append(part)
    return ",".join(seen)


# --------------------------------------------------------------------------- #
# API sub-application (mounted at /api)
# --------------------------------------------------------------------------- #
api = FastAPI(title="Local AI Hub API")


@api.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---- Users ---------------------------------------------------------------- #
def _get_or_create_user(db: Session, username: str, full_name: str = "") -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        user = User(username=username, full_name=full_name or username)
        db.add(user)
        db.flush()
    return user


@api.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> UserOut:
    exists = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if exists is not None:
        # Idempotent-ish: return the existing user rather than erroring, so the
        # lightweight "sign in as <name>" flow just works.
        return UserOut.model_validate(exists)
    user = User(username=payload.username, full_name=payload.full_name or payload.username, bio=payload.bio)
    db.add(user)
    db.commit()
    return UserOut.model_validate(user)


@api.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_session)) -> list[UserOut]:
    users = db.execute(select(User).order_by(User.username)).scalars()
    return [UserOut.model_validate(u) for u in users]


@api.get("/users/{username}", response_model=UserProfile)
def get_user(username: str, db: Session = Depends(get_session)) -> UserProfile:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    repos = db.execute(
        select(Repository)
        .where(Repository.owner_id == user.id)
        .order_by(Repository.updated_at.desc())
    ).scalars()
    profile = UserProfile.model_validate(user)
    profile.repositories = [RepoSummary.model_validate(r) for r in repos]
    return profile


# ---- Repositories --------------------------------------------------------- #
_SORTS = {
    "trending": (Repository.downloads + Repository.likes * 10).desc(),
    "likes": Repository.likes.desc(),
    "downloads": Repository.downloads.desc(),
    "recent": Repository.updated_at.desc(),
    "created": Repository.created_at.desc(),
    "name": Repository.repo_id.asc(),
}


@api.get("/repos", response_model=RepoPage)
def list_repos(
    q: str | None = Query(default=None),
    repo_type: str | None = None,
    owner: str | None = None,
    task: str | None = None,
    library: str | None = None,
    license: str | None = None,
    tag: str | None = None,
    sort: str = "trending",
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
) -> RepoPage:
    conds = []
    if repo_type in ("model", "dataset"):
        conds.append(Repository.repo_type == repo_type)
    if owner:
        conds.append(Repository.owner_username == owner)
    if task:
        conds.append(Repository.task == task)
    if library:
        conds.append(Repository.library == library)
    if license:
        conds.append(Repository.license == license)
    if tag:
        # Exact-token match against a delimiter-wrapped CSV, wildcards escaped:
        # ',cat,' will not match ',category,'.
        esc = _like_escape(tag)
        wrapped = literal(",").concat(Repository.tags_csv).concat(",")
        conds.append(wrapped.like(f"%,{esc},%", escape="\\"))
    if q:
        like = f"%{_like_escape(q)}%"
        conds.append(
            Repository.repo_id.ilike(like, escape="\\")
            | Repository.tags_csv.ilike(like, escape="\\")
            | Repository.description.ilike(like, escape="\\")
        )

    total = db.execute(select(func.count()).select_from(Repository).where(*conds)).scalar_one()
    order = _SORTS.get(sort, _SORTS["trending"])
    stmt = select(Repository).where(*conds).order_by(order).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars())

    return RepoPage(
        items=[RepoSummary.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


def _get_repo(db: Session, owner: str, name: str) -> Repository:
    repo = db.execute(
        select(Repository).where(Repository.repo_id == f"{owner}/{name}")
    ).scalar_one_or_none()
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@api.post("/repos", response_model=RepoDetail, status_code=201)
def create_repo(payload: RepoCreate, db: Session = Depends(get_session)) -> RepoDetail:
    repo_id = f"{payload.owner}/{payload.name}"
    if db.execute(select(Repository).where(Repository.repo_id == repo_id)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Repository '{repo_id}' already exists")

    user = _get_or_create_user(db, payload.owner)
    repo = Repository(
        repo_id=repo_id,
        owner_id=user.id,
        owner_username=user.username,
        name=payload.name,
        repo_type=payload.repo_type,
        description=payload.description,
        readme=payload.readme,
        license=payload.license or None,
        task=payload.task or None,
        library=payload.library or None,
        tags_csv=_normalize_tags(payload.tags),
    )
    db.add(repo)
    db.commit()
    return RepoDetail.model_validate(repo)


@api.get("/repos/{owner}/{name}", response_model=RepoDetail)
def repo_detail(owner: str, name: str, db: Session = Depends(get_session)) -> RepoDetail:
    return RepoDetail.model_validate(_get_repo(db, owner, name))


@api.put("/repos/{owner}/{name}", response_model=RepoDetail)
def update_repo(
    owner: str, name: str, payload: RepoUpdate, db: Session = Depends(get_session)
) -> RepoDetail:
    repo = _get_repo(db, owner, name)
    data = payload.model_dump(exclude_unset=True)
    if "tags" in data and data["tags"] is not None:
        repo.tags_csv = _normalize_tags(data.pop("tags"))
    else:
        data.pop("tags", None)
    for key, value in data.items():
        setattr(repo, key, value)
    db.commit()
    return RepoDetail.model_validate(repo)


@api.delete("/repos/{owner}/{name}")
def delete_repo(owner: str, name: str, db: Session = Depends(get_session)) -> dict:
    repo = _get_repo(db, owner, name)
    db.delete(repo)
    db.commit()
    return {"deleted": True}


@api.post("/repos/{owner}/{name}/like", response_model=RepoSummary)
def like_repo(owner: str, name: str, db: Session = Depends(get_session)) -> RepoSummary:
    repo = _get_repo(db, owner, name)
    repo.likes += 1
    db.commit()
    return RepoSummary.model_validate(repo)


@api.post("/repos/{owner}/{name}/download", response_model=RepoSummary)
def register_download(owner: str, name: str, db: Session = Depends(get_session)) -> RepoSummary:
    """Called by the SPA when a user follows a file link, to bump the counter."""
    repo = _get_repo(db, owner, name)
    repo.downloads += 1
    db.commit()
    return RepoSummary.model_validate(repo)


# ---- Files ---------------------------------------------------------------- #
@api.post("/repos/{owner}/{name}/files", response_model=RepoFileOut, status_code=201)
def add_file(
    owner: str, name: str, payload: RepoFileCreate, db: Session = Depends(get_session)
) -> RepoFileOut:
    repo = _get_repo(db, owner, name)
    if any(f.filename == payload.filename for f in repo.files):
        raise HTTPException(status_code=409, detail="A file with that name already exists")
    rf = RepoFile(
        repo_pk=repo.id,
        filename=payload.filename,
        url=str(payload.url),
        size_bytes=payload.size_bytes,
    )
    db.add(rf)
    db.commit()
    return RepoFileOut.model_validate(rf)


@api.delete("/repos/{owner}/{name}/files/{file_id}")
def delete_file(
    owner: str, name: str, file_id: int, db: Session = Depends(get_session)
) -> dict:
    repo = _get_repo(db, owner, name)
    rf = db.execute(
        select(RepoFile).where(RepoFile.id == file_id, RepoFile.repo_pk == repo.id)
    ).scalar_one_or_none()
    if rf is None:
        raise HTTPException(status_code=404, detail="File not found")
    db.delete(rf)
    db.commit()
    return {"deleted": True}


# ---- Facets & stats ------------------------------------------------------- #
@api.get("/facets", response_model=Facets)
def facets(repo_type: str | None = None, db: Session = Depends(get_session)) -> Facets:
    base = []
    if repo_type in ("model", "dataset"):
        base.append(Repository.repo_type == repo_type)

    def grouped(column) -> list[FacetValue]:
        stmt = (
            select(column, func.count())
            .where(*base, column.isnot(None), column != "")
            .group_by(column)
            .order_by(func.count().desc())
        )
        return [FacetValue(value=v, count=c) for v, c in db.execute(stmt).all()]

    tag_counts: dict[str, int] = {}
    for csv in db.execute(select(Repository.tags_csv).where(*base)).scalars():
        for tag in (t for t in (csv or "").split(",") if t):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda kv: kv[1], reverse=True)[:30]

    return Facets(
        tasks=grouped(Repository.task),
        libraries=grouped(Repository.library),
        licenses=grouped(Repository.license),
        tags=[FacetValue(value=v, count=c) for v, c in top_tags],
    )


@api.get("/stats", response_model=Stats)
def stats(db: Session = Depends(get_session)) -> Stats:
    def rcount(*conds) -> int:
        stmt = select(func.count()).select_from(Repository)
        for c in conds:
            stmt = stmt.where(c)
        return db.execute(stmt).scalar_one()

    total_files = db.execute(select(func.count()).select_from(RepoFile)).scalar_one()
    total_size = db.execute(
        select(func.coalesce(func.sum(RepoFile.size_bytes), 0))
    ).scalar_one()
    users = db.execute(select(func.count()).select_from(User)).scalar_one()

    return Stats(
        total_repos=rcount(),
        models=rcount(Repository.repo_type == "model"),
        datasets=rcount(Repository.repo_type == "dataset"),
        users=users,
        total_files=int(total_files),
        total_size_bytes=int(total_size),
    )


app.mount("/api", api)


# --------------------------------------------------------------------------- #
# Static SPA (mounted last so /api wins)
# --------------------------------------------------------------------------- #
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str):
    if not INDEX_HTML.is_file():
        return JSONResponse(
            status_code=200,
            content={
                "app": "Local AI Hub",
                "message": "Frontend not built. Run the Vite dev server (npm run dev) "
                "or build the SPA (npm run build).",
                "api_docs": "/api/docs",
            },
        )
    candidate = (STATIC_DIR / full_path).resolve()
    if full_path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
        return FileResponse(candidate)
    return FileResponse(INDEX_HTML)
