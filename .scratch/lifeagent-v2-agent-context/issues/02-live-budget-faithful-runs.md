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

**Status:** open

- [ ] baseline reproduction check before any agent-context number is reported
- [ ] agent-context recall at the production budget (defaults + reserved slot)
- [ ] 13-case funnel classification, manual and auditable
- [ ] `get_document` calls handled: they deliver page text, not chunks, so a
      case whose step trace contains a `get_document` read of the gold document
      must be read manually (its `args_summary` has document_id/page) instead of
      being auto-labelled `not_retrieved`
- [ ] D1/D2 decision applied exactly as pre-registered; no threshold change
- [ ] failure types attributed (no-new-recall vs returned-not-used vs not-retrieved)

## Comments

## Answer
