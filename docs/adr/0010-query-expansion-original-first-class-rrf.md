# Query expansion keeps the original as a first-class member and fuses two branches safely

Status: accepted

V2.1 showed that replacing the user's query with a single LLM rewrite is a
destructive, single-point-of-failure transformation: the rewrite dropped
discriminative terms, injected dates into non-temporal questions and varied
between runs, regressing the hard-10 ranking. Mature implementations keep the
original query and fuse multiple retrieval lists instead (LangChain
MultiQueryRetriever's option, LlamaIndex QueryFusionRetriever's default, R2R's
hybrid retrieval).

V2.2 therefore keeps the **original query as a first-class member** — never a
fallback — and adds exactly **one generated query variant** (2+ variants, RRF
weight tuning and query decomposition belong to later stages). The two branches
are retrieved in parallel and fused with **equal-weight Reciprocal Rank Fusion**
(`score = Σ 1 / (k + rank)`, k = 60) with a deterministic
**original-priority tie-break**.

Equal weights would be unsafe with three or more lists, because two weaker
variant lists can outvote the original's rank-1 correct chunk. With exactly two
branches the counterexample degenerates into a tie (each branch contributes
`1/(k+1)`), and breaking that tie in favour of the original branch prevents a
bad rewrite from displacing the original's best hit. This is why V2.2 uses
equal weights plus tie-break rather than a tuned weight: the weight question
only becomes meaningful once a multi-variant or multi-channel (V2.3: dense +
BM25) fusion exists, and it must be pre-registered before that experiment
rather than chosen after seeing results.

Variant generation reuses the V2.1 rewriter with two defect fixes — date
resolution only for explicit relative-date expressions, and preservation of
entities, identifiers, numbers and discriminative nouns — and runs
deterministically. Any generation failure simply leaves the original-only path
running.

Consequences: each `search_knowledge` call still counts as one retrieval for
the Agent while internally issuing two candidate searches and one expansion LLM
call; the AgentRun trace carries the original, the variant, per-branch hits,
fusion candidates and the fusion parameters; disabling expansion reproduces the
frozen v2.0.2 baseline exactly; V2.3 adds the sparse/BM25 channel to the same
fusion step, and V2.4 reranks the fused candidates. HyDE and query
decomposition remain separate, later candidates.

Update (2026-09-11): the pre-registered V2.2 A/B ran. A (expansion disabled,
tool path) reproduced baseline-v2.0.2 exactly. B (original + 1 variant,
equal-weight RRF + tie-break) moved hard-10 chunk MRR@5 from 0.5867 to 0.6167
(+0.0300, exactly the pre-registered boundary) with no easy regression and both
gates passing, **but** the per-case attribution showed 7 of 10 hard cases
`no_new_recall`, 2 `original_sufficient`, 1 `rank_only_gain` and 0
`new_recall_but_fusion_missed`/`expansion_error`: the whole gain came from one
reorder, and expansion added no new hard-subset recall. `answer-013` was
0/0/0. Query expansion therefore remains **disabled by default**
(`QUERY_EXPANSION_ENABLED=false`) and is kept as an experiment switch; V2.2b
multi-variant work is skipped. The next stage (V2.3, ADR-0011) adds a
sparse/BM25 channel to the same fusion to attack the observed lexical-recall
failure mode, with expansion disabled to keep the experiment single-variable.
