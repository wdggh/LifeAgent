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
