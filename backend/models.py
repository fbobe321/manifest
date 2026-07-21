"""SQLAlchemy ORM models.

A local Hugging Face clone: users own *repositories* (models or datasets).
A repository holds a markdown model-card plus a list of files. Files are NOT
stored here — each file is just an external link to wherever the bytes live.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String, default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # "owner/name" — the natural key, like a Hub repo id.
    repo_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    owner_username: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    repo_type: Mapped[str] = mapped_column(String, index=True, default="model")

    # Short one-line tagline shown on cards.
    description: Mapped[str] = mapped_column(String, default="")
    # Full markdown model-/dataset-card.
    readme: Mapped[str] = mapped_column(Text, default="")

    license: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    task: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    library: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    tags_csv: Mapped[str] = mapped_column(String, default="")

    likes: Mapped[int] = mapped_column(Integer, default=0)
    downloads: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped[User] = relationship(back_populates="repositories")
    files: Mapped[list["RepoFile"]] = relationship(
        back_populates="repo", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def tags(self) -> list[str]:
        return [t for t in self.tags_csv.split(",") if t]

    @property
    def num_files(self) -> int:
        return len(self.files)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)


class RepoFile(Base):
    __tablename__ = "repo_files"
    __table_args__ = (UniqueConstraint("repo_pk", "filename", name="uq_repofile_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_pk: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String)
    # External link to the actual bytes (on another server / object store).
    url: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    repo: Mapped[Repository] = relationship(back_populates="files")


Index("ix_repo_type_owner", Repository.repo_type, Repository.owner_username)
