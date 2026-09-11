# 03: V2.3d closure and V2.4 direction

**What to build:** close the feature and publish the direction.

- ADR (new, or an update to ADR-0012) recording the agent-context metric
  definition, the budget-faithfulness defect it corrects, and the D1/D2
  outcome.
- Evaluation README section with the three-level funnel numbers and the
  classification counts; CONTEXT.md decision (add a term or record why not).
- Resolve all V2.3d tickets and state plainly whether V2.4 is ranking or
  evidence-aware synthesis, with the evidence that forced the choice.

**Blocked by:** 02

**Status:** resolved

- [x] ADR records metric definition + budget-faithfulness correction + decision
- [x] README funnel section; CONTEXT.md judged explicitly
- [x] all tickets resolved; V2.4 direction stated with its evidence
- [x] production defaults unchanged and stated as such

## Comments

## Answer

V2.3d is closed. ADR-0013 records the metric definition, the budget-faithfulness
defect, the pre-registered D1/D2 rule, the measured D2 outcome and the V2.4
scope. ADR-0012 and `experiment-v2.3c-analysis.md` carry forward-corrections,
because V2.3d falsified V2.3c's "answer synthesis" attribution.

- **V2.4 is named — Agent Retrieval Scope Safety**, not "reranker" and not
  "synthesis": fix the Agent's over-narrowing of the search space and build the
  evaluation that catches it. Priority order: (1) tool argument
  validation / calibration, (2) inappropriate hard-filter detection,
  (3) fallback / scope widening, (4) evaluation coverage,
  (5) re-assess retrieval / reranking. The cross-encoder reranker is deferred,
  not cancelled.
- **CONTEXT.md judged explicitly and changed**: two terms added because ADR-0012
  and the funnel need them — *Agent context* (the Chunks one AgentRun actually
  received; previously only listed as an anti-synonym of AgentState) and
  *Retrieval scope* (what one search_knowledge call is allowed to return, set by
  the Agent's own arguments plus the per-round budget).
- **Answer reviews:** the four V2.3d runs are scored as a diagnostic baseline
  with the existing three axes only — `answer_review_v2.3d-defaults.json`,
  `-defaults-b.json`, `-reserved-slot.json`, `-reserved-slot-b.json`
  (12/11/12, 11/10/12, 10/9/11, 11/10/12). Funnel labels in
  `reports/funnel-v2.3d-*.md`; the drafts await user confirmation.
- Production defaults unchanged: `QUERY_REWRITE_ENABLED=false`,
  `QUERY_EXPANSION_ENABLED=false`, `QUERY_SPARSE_ENABLED=false`; the reserved
  slot and every budget constant keep their values.
