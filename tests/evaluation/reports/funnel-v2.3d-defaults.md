# Agent-context funnel (k=4)

| case | category | retrievals | call sizes | gold chunks | gold in context | label | completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| answer-001 | clause_specific | 1 | [3] | 1 | True | pending_review | None |
| answer-002 | simple_fact | 1 | [3] | 1 | True | pending_review | None |
| answer-003 | numeric_date | 1 | [3] | 1 | True | pending_review | None |
| answer-004 | semantic_rewrite | 1 | [3] | 2 | True | pending_review | None |
| answer-005 | cross_paragraph | 1 | [3] | 2 | True | pending_review | None |
| answer-006 | clause | 1 | [3] | 1 | True | pending_review | None |
| answer-007 | clause | 1 | [3] | 1 | True | pending_review | None |
| answer-008 | semantic_rewrite | 1 | [3] | 1 | True | pending_review | None |
| answer-009 | clause | 1 | [3] | 1 | True | pending_review | None |
| answer-010 | cross_paragraph | 1 | [3] | 3 | False | pending_review | None |
| answer-011 | not_in_kb | 1 | [3] | 0 | None | not_applicable | None |
| answer-012 | not_in_kb | 1 | [3] | 0 | None | not_applicable | None |
| answer-013 | cross_paragraph | 1 | [3] | 3 | False | pending_review | None |

## Counts

- not_applicable: 2
- not_retrieved: 0
- document_only: 0
- found_beyond_budget: 0
- returned_not_used: 0
- used: 0
- pending_review: 11

agent_context_recall@4 = 9/11 = 0.8182
