# 9addb1a Double-Layer Regression Suite (V2.0-07)

The `9addb1a` retrieval miss has two distinct layers that must both stay
guarded:

```text
                    9addb1a
                       |
            +----------+-----------+
            |                      |
    Retrieval level          Tool level
    (evaluation suite)       (engineering suite)
            |                      |
     reg-001 / reg-002       top_k=1 request
     rental p8 / p9          must not bypass the
     near-tie clauses        MIN_TOP_K=3 floor
            |                      |
     Recall@5 == 1 gate     effective top_k == 3
     (behaviour gate)       and correct clause present
```

## Layer A: retrieval level (evaluation)

- Lives in `datasets/synthetic-personal-kb-v1/dataset/queries.jsonl` as
  `reg-001` (rental page 8, clause 4) and `reg-002` (rental page 9, clause 5).
- The questions must never leak the clause number, so MRR/Recall can observe
  whether the semantically matching clause outranks its near-tie decoy.
- Enforced by `runners/retrieval_eval.py`: chunk-level `Recall@5 == 1` for
  both reg ids, otherwise the live report is `FAIL`.
- The dense score gap between the target clause and its decoy is diagnostic
  only (`< 0.1` = near-tie reproduced); it never fails the gate by itself.

## Layer B: tool level (engineering)

- Lives in the repository's engineering test suite:
  `tests/test_review_fixes.py::test_search_tool_never_retrieves_single_chunk_on_request`.
- Verifies that a `top_k=1` request through `search_knowledge` is floored to
  `MIN_TOP_K = 3`, so a near-tie clause cannot be silently dropped.
- This test must NOT be migrated into the evaluation framework: it exercises
  the production tool seam with its own fakes. The canary test in
  `test_9addb1a_regression_suite.py` asserts the function still exists so any
  future removal or move fails loudly.

## Rules

- Recall is the behaviour gate; the score gap is information.
- The evaluation framework never replaces existing engineering regressions.
- Live verification of the full gate happens in V2.0-09 via
  `python -m tests.evaluation.runners.retrieval_eval live --reset`.
