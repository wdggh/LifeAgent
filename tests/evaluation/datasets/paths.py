"""Versioned dataset registry for evaluation assets (V2.0.1-01).

Datasets are physically isolated under ``tests/evaluation/datasets/``:

- ``synthetic-personal-kb-v1``: FROZEN / historical (V2.0 assets).
- ``synthetic-personal-kb-v2``: ACTIVE (Benchmark Hardening, populated by
  V2.0.1-02/03).

The active dataset name comes from ``EVAL_DATASET`` and defaults to v2. Code
that still needs the frozen v1 data (framework regression, historical review)
passes the dataset name explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent
V1 = "synthetic-personal-kb-v1"
V2 = "synthetic-personal-kb-v2"


def active_dataset_name() -> str:
    return os.environ.get("EVAL_DATASET", V2)


def dataset_dir(name: str | None = None) -> Path:
    return DATASETS_DIR / (name or active_dataset_name())


def fixtures_dir(name: str | None = None) -> Path:
    return dataset_dir(name) / "fixtures"


def corpus_dir(name: str | None = None) -> Path:
    return fixtures_dir(name) / "corpus"


def pdf_dir(name: str | None = None) -> Path:
    return fixtures_dir(name) / "pdf"


def fonts_dir(name: str | None = None) -> Path:
    return fixtures_dir(name) / "fonts"


def data_dir(name: str | None = None) -> Path:
    return dataset_dir(name) / "dataset"


def manifest_path(name: str | None = None) -> Path:
    return corpus_dir(name) / "manifest.json"


def queries_path(name: str | None = None) -> Path:
    return data_dir(name) / "queries.jsonl"


def answer_cases_path(name: str | None = None) -> Path:
    return data_dir(name) / "answer_cases.jsonl"


def require_manifest(name: str | None = None) -> Path:
    path = manifest_path(name)
    if not path.exists():
        raise FileNotFoundError(
            f"dataset '{name or active_dataset_name()}' not ready: "
            f"missing {path}"
        )
    return path
