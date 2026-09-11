# Hybrid retrieval reserves one output slot for the best sparse-only chunk

Status: accepted (pre-registered experiment pending)

V2.3b showed that the sparse/BM25 channel reaches evidence the dense channel
misses — for `answer-013` the seven-day-return rule is sparse rank 3 — but no
fusion policy brings it inside the Agent's 4-chunk round budget: dense-priority
only fills slots beyond the dense top-8, and equal/weighted RRF dilute the
stronger dense ordering while still leaving the chunk at fused rank 6–9.

V2.3c therefore changes only the final slot allocation: with a limit of L, take
the dense top (L−1) in order and reserve the last slot for the highest-ranked
sparse chunk that is **not present in any dense candidate** — not merely absent
from the selected dense slots. A dense candidate that only lost its slot is not
eligible, so the experiment adds genuinely new lexical evidence instead of
silently swapping one dense result for another. If no such chunk exists (or the
sparse channel is unavailable), the allocation falls back to the dense-priority
fill. Candidate generation, any fusion scores, the dense retriever, BM25 index,
tokenisation, candidate width and the Agent budget stay exactly as they are, so
the experiment tests one hypothesis: that the binding constraint is budget
allocation rather than recall capability or the fusion paradigm.

Consequences: the reserved chunk, its sparse rank and the slot counts are
recorded in the AgentRun trace; changing the number of reserved slots is a new
pre-registered experiment; if the reserved slot still fails the criteria
(hard-10 +0.03 or NDCG +0.03, easy-40 regression ≤0.01, gates, answer-013
source = 1), the next step is V2.4 (wider candidates plus cross-encoder
reranking ordered down to the budget); if it succeeds, the slot policy becomes
the default hybrid allocation and the reranker is evaluated on top of it.

Update (2026-09-11): the V2.3c A/B ran. A (dense-only) reproduced
baseline-v2.0.2 exactly. B (reserved slot) left MRR@5 / NDCG@5 / Recall@5 /
hard-10 / easy-40 unchanged but reduced overall Recall@10 from 0.9100 to
0.8767, because the reserved slot displaces dense rank-9/10 gold chunks. The
targeted criterion passed: `answer-013` source_correctness improved 0 → 1 — the
sparse seven-day-return chunk (purchase p3) entered the Agent's top-4 through
the reserved slot and the answer now cites the purchase record and the 24-month
warranty. Completeness and no-hallucination remain 0 because the model still
did not quote the seven-day rule it had in context: the failure has moved from
retrieval to answer synthesis. The experiment also exposed a measurement gap —
top-5 metrics cannot see an intervention confined to the final consumed slot —
so the next pre-registered step is an agent-context metric (gold inside the
Agent's top-4) plus an answer-synthesis diagnosis, before deciding on V2.4.
