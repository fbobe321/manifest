"""Pydantic request/response models."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(default="", max_length=120)
    bio: str = Field(default="", max_length=2000)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    bio: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #
class RepoFileCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    url: HttpUrl
    size_bytes: int = Field(default=0, ge=0)


class RepoFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    url: str
    size_bytes: int
    created_at: datetime


# --------------------------------------------------------------------------- #
# Repositories
# --------------------------------------------------------------------------- #
class RepoCreate(BaseModel):
    owner: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9_.-]+$")
    repo_type: str = "model"
    description: str = Field(default="", max_length=280)
    readme: str = Field(default="", max_length=100_000)
    license: str | None = None
    task: str | None = None
    library: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("repo_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ("model", "dataset"):
            raise ValueError("repo_type must be 'model' or 'dataset'")
        return v


class RepoUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=280)
    readme: str | None = Field(default=None, max_length=100_000)
    license: str | None = None
    task: str | None = None
    library: str | None = None
    tags: list[str] | None = None


class _RepoBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: str
    owner_username: str
    name: str
    repo_type: str
    description: str
    license: str | None
    task: str | None
    library: str | None
    tags: list[str]
    likes: int
    downloads: int
    num_files: int
    total_size_bytes: int
    created_at: datetime
    updated_at: datetime


class RepoSummary(_RepoBase):
    """List/card view — omits the README body and file list."""


class RepoDetail(_RepoBase):
    readme: str
    files: list[RepoFileOut]


class RepoPage(BaseModel):
    items: list[RepoSummary]
    total: int
    limit: int
    offset: int


class UserProfile(UserOut):
    repositories: list[RepoSummary]


# --------------------------------------------------------------------------- #
# Facets & stats
# --------------------------------------------------------------------------- #
class FacetValue(BaseModel):
    value: str
    count: int


class Facets(BaseModel):
    tasks: list[FacetValue]
    libraries: list[FacetValue]
    licenses: list[FacetValue]
    tags: list[FacetValue]


class Stats(BaseModel):
    total_repos: int
    models: int
    datasets: int
    users: int
    total_files: int
    total_size_bytes: int
