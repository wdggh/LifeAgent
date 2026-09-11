# 02: Live budget-faithful runs + 13-case answer rerun + funnel diagnosis

**What to build:** the measurement itself, on the real stack.

1. Budget-faithful live run with production defaults → the primary
   `agent_context_recall@4` (overall / hard-10 / easy-40) plus the existing
   capability metrics, which must reproduce the recorded baseline or the run is
   void.
2. Identity re-read with the V2.3c reserved slot enabled → how much context
   recall the slot actually buys at the production budget, versus the L=10
   number recorded in V2.3c.
3. Re-run the 13 answer cases with per-call chunk ids recorded, then classify
   each case into the funnel and report the `answer-013` chain end to end
   (retrieved → returned → used), including whether the previous "Agent top-4"
   claim survives the trace.
4. Apply the pre-registered D1/D2 decision rule from the spec and write the
   result as an attribution report.

**Blocked by:** 01

**Status:** resolved

- [x] baseline reproduction check before any agent-context number is reported
- [x] agent-context recall at the production budget (defaults + reserved slot)
- [x] 13-case funnel classification, manual and auditable
- [x] `get_document` calls handled: they deliver page text, not chunks, so a
      case whose step trace contains a `get_document` read of the gold document
      must be read manually (its `args_summary` has document_id/page) instead of
      being auto-labelled `not_retrieved`
- [x] D1/D2 decision applied exactly as pre-registered; no threshold change
- [x] failure types attributed (no-new-recall vs returned-not-used vs not-retrieved)

## Comments

## Answer

Full analysis: `reports/experiment-v2.3d-analysis.md`; raw transcripts and
reports gitignored.

**Decision: D2.** hard-10 `agent_context_recall@4` = **0.70** (< 0.90), overall
0.90 (easy 0.95). Capability reproduction equalled baseline-v2.0.2 exactly, so
the run is valid.

- The Agent consumes much less than the reports implied: hard-10 consumed-set
  recall 0.5667, and 3/10 hard cases never get the gold chunk into the window.
  All-gold variant 0.78 vs any-gold 0.90 (16 queries have multi-chunk gold).
- The reserved slot is not the answer: 49/50 slots filled, gold once (`v2-019`,
  already in context), **zero** context misses rescued, hard-10 recall −0.0333
  and NDCG −0.0202 versus defaults.
- 13-case funnel: 8–10 of the 11 gold-bearing cases have gold in context
  depending on the run — noisy at n=13. The manual `used` half is
  `pending_review` (four new runs, not yet scored); D2 does not depend on it.
- **answer-013 root cause found (revises V2.3c).** The trace shows the Agent
  calling the Tool with `document_type="warranty"` and `top_k=3`; the seven-day
  return rule lives in `purchase_record_01`, which that filter excludes, and
  sparse runs under the same filter. So the evidence never arrived — this is
  not an answer-synthesis failure as V2.3c recorded, and no fusion/reranker
  change can fix it. Both V2.3d runs reproduce it identically.
- Second finding: the Agent asked `top_k=3` in every call, so the effective
  window is 3, not the 4 the budget allows.
- New failure layer surfaced that the pre-registration did not anticipate:
  **agent tool-argument filtering** (neither ranking nor synthesis). Scope
  decision deferred to the user; V2.4 is now a ranking/delivery question under
  the pre-registered rule.
