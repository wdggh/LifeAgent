# Hybrid retrieval adds a sparse/BM25 channel fused with RRF

Status: accepted

V2.2's attribution showed the remaining hard-case bottleneck is lexical, not
semantic: 7 of 10 hard queries produced no new recall from query expansion, and
the exact-term / numeric / document-scoping failures (`七天退货`, `整机保修`,
`购买记录`, identifiers) come from dense embeddings preferring the wrong
document family. V2.3 therefore adds a sparse/BM25 lexical channel beside the
dense channel, rather than continuing to tune rewriting, prompts or RRF
weights.

The sparse channel uses `rank_bm25` with `jieba` tokenisation, keeps numbers and
identifiers verbatim, builds one in-memory index per user from that user's
stored chunks, and applies the same user/document-type/document-id scoping as
dense retrieval. The index is cached per user and invalidated through a
Redis corpus version counter bumped on ingestion and deletion; if Redis is
unavailable the reader falls back to a short TTL rebuild, and any index failure
degrades to dense-only instead of failing retrieval.

The two ranked lists (dense top-8, sparse top-8) are deduplicated and fused
with equal-weight Reciprocal Rank Fusion (`k = 60`) using a dense-priority
tie-break, then truncated to the normal per-call budget. Query expansion stays
disabled during the V2.3 experiment so the experiment changes exactly one
thing: the presence of a lexical channel.

Consequences: `rank_bm25` and `jieba` become production dependencies; the
worker and API must maintain the per-user corpus version; the AgentRun trace
now carries both channels' hit lists, fusion candidates and index metadata so
that dense-hit / sparse-new-recall / sparse-hit-but-not-fused / neither can be
attributed per case; V2.4 will add the cross-encoder reranker on top of the
fused candidates; query expansion code remains available but disabled, and
revisiting multi-variant expansion requires a new, pre-registered decision.

Update (2026-09-11): the V2.3 A/B (equal-weight RRF) failed — hard-10 NDCG@5
fell 0.4974 → 0.4410 and easy-40 MRR@5 fell 0.9000 → 0.8250 — because
equal-weight RRF over heterogeneous channels dilutes the stronger dense
ranking. The pre-registered V2.3b fusion-policy ablation showed that
`dense-priority supplement` is a no-op for metrics (sparse only fills slots
beyond the dense top-8 and beyond the agent's 4-chunk budget) and
`weighted RRF 2:1` still regresses easy-40 by 0.0667. `answer-013`'s
seven-day-return chunk (purchase p3) is retrieved by the sparse channel
(rank 3) but never enters the agent's top-4 under any fusion policy. Fusion
policy alone is therefore not the fix: the next pre-registered step is either
a reserved sparse slot (V2.3c) or the cross-encoder reranker over a wider
candidate set (V2.4). The sparse channel remains valuable as the source of the
missing lexical evidence; the fusion/budget interaction is the binding
constraint.
