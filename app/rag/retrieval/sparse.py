"""Sparse/BM25 retrieval channel with per-user lazy indexing (V2.3, ADR-0011).

The index is built from the user's stored chunks, tokenised with jieba for
Chinese, keeps identifiers and numbers verbatim, and is cached per user. Cache
freshness is decided by a corpus-version counter (Redis) with a short TTL
fallback when the counter is unavailable. Any index failure degrades to
dense-only at the Tool seam; this module therefore raises and lets the caller
record the fallback.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import jieba
from rank_bm25 import BM25Okapi

from app.core.config import Settings, get_settings
from app.domain.models.search_result import SearchResult

ID_PATTERN = re.compile(r"[A-Za-z]{2,5}-\d{4}-\d{3,4}")
ASCII_TOKEN = re.compile(r"[A-Za-z0-9]+")
CJK_RANGE = ("\u4e00", "\u9fff")


class SparseIndexError(RuntimeError):
    """Raised when the sparse index cannot be built or queried."""


def tokenize(text: str) -> list[str]:
    """Tokenise for BM25: jieba for Chinese, identifiers kept verbatim."""

    tokens: list[str] = []
    for match in ID_PATTERN.finditer(text):
        tokens.append(match.group(0).lower())
    stripped = ID_PATTERN.sub(" ", text)
    for piece in jieba.lcut(stripped):
        token = piece.strip()
        if not token:
            continue
        if ASCII_TOKEN.fullmatch(token):
            tokens.append(token.lower())
            continue
        if any(CJK_RANGE[0] <= char <= CJK_RANGE[1] for char in token):
            tokens.append(token)
    return tokens


@dataclass(frozen=True)
class SparseEntry:
    chunk_id: str
    content: str
    document_id: str
    document_name: str
    document_type: str
    start_page: int | None
    end_page: int | None
    chunk_index: int
    tokens: list[str] = field(default_factory=list)


class BM25Index:
    def __init__(
        self, entries: Sequence[SparseEntry], *, k1: float, b: float
    ) -> None:
        self._entries = list(entries)
        self._bm25 = (
            BM25Okapi(
                [entry.tokens for entry in self._entries], k1=k1, b=b
            )
            if self._entries
            else None
        )

    @property
    def size(self) -> int:
        return len(self._entries)

    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        if self._bm25 is None:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = [float(score) for score in self._bm25.get_scores(tokens)]
        if not scores or max(scores) <= 0:
            # Tiny corpora can push BM25 IDFs to zero (e.g. N=2, df=1).
            # Fall back to a deterministic lexical-overlap score so the
            # channel still behaves lexically instead of returning nothing.
            query_tokens = set(tokens)
            scores = [
                float(len(query_tokens & set(entry.tokens)))
                for entry in self._entries
            ]
        candidates: list[tuple[float, int]] = []
        for index, (score, entry) in enumerate(
            zip(scores, self._entries)
        ):
            if score <= 0:
                continue
            if document_type and entry.document_type != document_type:
                continue
            if document_id and entry.document_id != document_id:
                continue
            candidates.append((float(score), index))
        candidates.sort(
            key=lambda item: (-item[0], self._entries[item[1]].chunk_id)
        )
        return [
            SearchResult(
                chunk_id=self._entries[index].chunk_id,
                document_id=self._entries[index].document_id,
                document_name=self._entries[index].document_name,
                content=self._entries[index].content,
                score=round(score, 4),
                start_page=self._entries[index].start_page,
                end_page=self._entries[index].end_page,
                document_type=self._entries[index].document_type,
            )
            for score, index in candidates[: max(0, top_k)]
        ]


@dataclass(frozen=True)
class SparseSearchOutcome:
    results: list[SearchResult]
    index_version: int | None
    rebuild_ms: float
    cache_hit: bool


class RedisCorpusVersionStore:
    """Best-effort per-user corpus version counter (Redis)."""

    def __init__(self, redis_url: str, timeout: float = 1.0) -> None:
        self._url = redis_url
        self._timeout = timeout

    def _key(self, user_id: str) -> str:
        return f"kb:{user_id}:corpus_version"

    async def _client(self):
        import redis.asyncio as aioredis

        return aioredis.from_url(
            self._url,
            socket_connect_timeout=self._timeout,
            socket_timeout=self._timeout,
        )

    async def current(self, user_id: str) -> int | None:
        try:
            client = await self._client()
            try:
                value = await client.get(self._key(user_id))
                return int(value) if value is not None else 0
            finally:
                await client.aclose()
        except Exception:
            return None

    async def bump(self, user_id: str) -> int | None:
        try:
            client = await self._client()
            try:
                return int(await client.incr(self._key(user_id)))
            finally:
                await client.aclose()
        except Exception:
            return None


class BM25SparseSearcher:
    """Lazy, per-user BM25 index over stored chunks."""

    def __init__(
        self,
        document_source: Any,
        vector_repository_provider: Callable[[], Any],
        version_store: RedisCorpusVersionStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._documents = document_source
        self._vector_provider = vector_repository_provider
        self._versions = version_store
        self._settings = settings or get_settings()
        self._cache: dict[str, tuple[int | None, BM25Index, float]] = {}
        self._lock = asyncio.Lock()

    async def _list_documents(self, user_id: str, page: int, size: int):
        if hasattr(self._documents, "list_by_user"):
            return await self._documents.list_by_user(user_id, page, size)
        return await self._documents.list_documents(user_id, page, size)

    async def _load_entries(self, user_id: str) -> list[SparseEntry]:
        vector_repository = self._vector_provider()
        entries: list[SparseEntry] = []
        page = 1
        while True:
            documents = await self._list_documents(user_id, page, 100)
            for document in documents:
                chunks = await vector_repository.fetch_document_chunks(
                    document.id
                )
                for chunk in chunks:
                    entries.append(
                        SparseEntry(
                            chunk_id=chunk.chunk_id,
                            content=chunk.content,
                            document_id=document.id,
                            document_name=document.filename,
                            document_type=document.document_type,
                            start_page=chunk.start_page,
                            end_page=chunk.end_page,
                            chunk_index=chunk.chunk_index,
                            tokens=tokenize(chunk.content),
                        )
                    )
            if len(documents) < 100:
                break
            page += 1
        return entries

    async def _index_for(
        self, user_id: str, version: int | None
    ) -> tuple[BM25Index, float, bool]:
        ttl = self._settings.query_sparse_version_ttl_seconds
        async with self._lock:
            cached = self._cache.get(user_id)
            if cached is not None:
                cached_version, index, built_at = cached
                if version is not None:
                    fresh = cached_version == version
                else:
                    fresh = (time.monotonic() - built_at) < ttl
                if fresh:
                    return index, 0.0, True
            started = time.perf_counter()
            entries = await self._load_entries(user_id)
            index = BM25Index(
                entries,
                k1=self._settings.query_sparse_bm25_k1,
                b=self._settings.query_sparse_bm25_b,
            )
            rebuild_ms = round((time.perf_counter() - started) * 1000, 2)
            self._cache[user_id] = (version, index, time.monotonic())
            return index, rebuild_ms, False

    async def search(
        self,
        *,
        user_id: str,
        query: str,
        top_k: int,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> SparseSearchOutcome:
        try:
            version = (
                await self._versions.current(user_id)
                if self._versions is not None
                else None
            )
            index, rebuild_ms, cache_hit = await self._index_for(
                user_id, version
            )
            results = index.search(
                query,
                top_k=top_k,
                document_type=document_type,
                document_id=document_id,
            )
        except Exception as exc:  # fail-open at the Tool seam
            raise SparseIndexError(str(exc)) from exc
        return SparseSearchOutcome(
            results=results,
            index_version=version,
            rebuild_ms=rebuild_ms,
            cache_hit=cache_hit,
        )
