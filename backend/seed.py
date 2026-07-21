"""Seed a fresh database with a few example users and repositories.

Files point at external URLs on purpose — this hub stores links, not bytes.
Runs only when the repositories table is empty.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import RepoFile, Repository, User

GB = 1024**3
MB = 1024**2


def _md(title: str, body: str) -> str:
    return f"# {title}\n\n{body}\n"


DEMO = [
    {
        "user": ("meta-llama", "Meta Llama", "Open foundation models from Meta AI."),
        "name": "Llama-3.1-8B-Instruct",
        "type": "model",
        "description": "Instruction-tuned 8B parameter chat model.",
        "task": "text-generation",
        "library": "transformers",
        "license": "llama3.1",
        "tags": ["text-generation", "chat", "llama", "conversational"],
        "likes": 4210,
        "downloads": 1_820_000,
        "readme": _md(
            "Llama 3.1 8B Instruct",
            "A multilingual, instruction-tuned generative model optimized for "
            "dialogue use cases.\n\n## Intended use\n\nAssistant-style chat, "
            "summarization and reasoning.\n\n## Files\n\nWeights are sharded "
            "`safetensors`; download via the links in **Files and versions**.",
        ),
        "files": [
            ("config.json", "https://example-mirror.local/meta-llama/llama-3.1-8b/config.json", 4 * 1024),
            ("model-00001-of-00004.safetensors", "https://example-mirror.local/meta-llama/llama-3.1-8b/model-00001-of-00004.safetensors", 4 * GB),
            ("model-00002-of-00004.safetensors", "https://example-mirror.local/meta-llama/llama-3.1-8b/model-00002-of-00004.safetensors", 4 * GB),
            ("tokenizer.json", "https://example-mirror.local/meta-llama/llama-3.1-8b/tokenizer.json", 9 * MB),
        ],
    },
    {
        "user": ("openai", "OpenAI", "Research org — automatic speech recognition and more."),
        "name": "whisper-large-v3",
        "type": "model",
        "description": "Robust speech recognition across many languages.",
        "task": "automatic-speech-recognition",
        "library": "transformers",
        "license": "apache-2.0",
        "tags": ["audio", "asr", "speech", "whisper"],
        "likes": 3120,
        "downloads": 2_540_000,
        "readme": _md(
            "Whisper large-v3",
            "A Transformer encoder-decoder model for speech-to-text.\n\n"
            "Supports transcription and translation for 90+ languages.",
        ),
        "files": [
            ("config.json", "https://example-mirror.local/openai/whisper-large-v3/config.json", 2 * 1024),
            ("model.safetensors", "https://example-mirror.local/openai/whisper-large-v3/model.safetensors", 3 * GB),
            ("tokenizer.json", "https://example-mirror.local/openai/whisper-large-v3/tokenizer.json", 2 * MB),
        ],
    },
    {
        "user": ("stabilityai", "Stability AI", "Generative models for images and beyond."),
        "name": "stable-diffusion-xl-base-1.0",
        "type": "model",
        "description": "High-resolution text-to-image latent diffusion model.",
        "task": "text-to-image",
        "library": "diffusers",
        "license": "openrail++",
        "tags": ["diffusion", "text-to-image", "stable-diffusion"],
        "likes": 5890,
        "downloads": 980_000,
        "readme": _md(
            "Stable Diffusion XL Base 1.0",
            "SDXL generates and modifies images from text prompts.\n\n"
            "Use the base model together with the refiner for best quality.",
        ),
        "files": [
            ("sd_xl_base_1.0.safetensors", "https://example-mirror.local/stabilityai/sdxl/sd_xl_base_1.0.safetensors", 6 * GB + 900 * MB),
            ("model_index.json", "https://example-mirror.local/stabilityai/sdxl/model_index.json", 1 * 1024),
        ],
    },
    {
        "user": ("google", "Google", "Datasets and models from Google Research."),
        "name": "wikipedia",
        "type": "dataset",
        "description": "Cleaned Wikipedia dumps in many languages.",
        "task": "text-generation",
        "library": "datasets",
        "license": "cc-by-sa-3.0",
        "tags": ["text", "wikipedia", "multilingual", "pretraining"],
        "likes": 1450,
        "downloads": 640_000,
        "readme": _md(
            "Wikipedia",
            "Wikipedia dataset containing cleaned articles built from the "
            "Wikimedia dumps.\n\nOne split per language.",
        ),
        "files": [
            ("dataset_infos.json", "https://example-mirror.local/datasets/wikipedia/dataset_infos.json", 120 * 1024),
            ("20231101.en/train-00000-of-00041.parquet", "https://example-mirror.local/datasets/wikipedia/en/train-00000-of-00041.parquet", 512 * MB),
            ("20231101.en/train-00001-of-00041.parquet", "https://example-mirror.local/datasets/wikipedia/en/train-00001-of-00041.parquet", 512 * MB),
        ],
    },
    {
        "user": ("rajpurkar", "Pranav Rajpurkar", "Author of the SQuAD reading-comprehension datasets."),
        "name": "squad",
        "type": "dataset",
        "description": "Stanford Question Answering Dataset (SQuAD).",
        "task": "question-answering",
        "library": "datasets",
        "license": "cc-by-4.0",
        "tags": ["question-answering", "nlp", "reading-comprehension"],
        "likes": 720,
        "downloads": 410_000,
        "readme": _md(
            "SQuAD",
            "A reading comprehension dataset of questions posed on Wikipedia "
            "articles, where the answer is a span of text from the passage.",
        ),
        "files": [
            ("plain_text/train-00000-of-00001.parquet", "https://example-mirror.local/datasets/squad/train.parquet", 30 * MB),
            ("plain_text/validation-00000-of-00001.parquet", "https://example-mirror.local/datasets/squad/validation.parquet", 5 * MB),
        ],
    },
]


def seed_if_empty(db: Session) -> None:
    existing = db.execute(select(func.count()).select_from(Repository)).scalar_one()
    if existing:
        return

    users: dict[str, User] = {}
    for spec in DEMO:
        uname, full, bio = spec["user"]
        user = users.get(uname)
        if user is None:
            user = db.execute(select(User).where(User.username == uname)).scalar_one_or_none()
            if user is None:
                user = User(username=uname, full_name=full, bio=bio)
                db.add(user)
                db.flush()
            users[uname] = user

        repo = Repository(
            repo_id=f"{uname}/{spec['name']}",
            owner_id=user.id,
            owner_username=uname,
            name=spec["name"],
            repo_type=spec["type"],
            description=spec["description"],
            readme=spec["readme"],
            license=spec["license"],
            task=spec["task"],
            library=spec["library"],
            tags_csv=",".join(spec["tags"]),
            likes=spec["likes"],
            downloads=spec["downloads"],
        )
        db.add(repo)
        db.flush()
        for fname, url, size in spec["files"]:
            db.add(RepoFile(repo_pk=repo.id, filename=fname, url=url, size_bytes=size))

    db.commit()
