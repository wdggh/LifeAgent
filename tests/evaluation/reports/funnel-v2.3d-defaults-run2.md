# Agent-context funnel (k=4)

| case | category | retrievals | call sizes | gold chunks | gold in context | label | completeness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| answer-001 | clause_specific | 1 | [3] | 1 | True | used | 1 |
| answer-002 | simple_fact | 1 | [3] | 1 | True | used | 1 |
| answer-003 | numeric_date | 1 | [3] | 1 | True | used | 1 |
| answer-004 | semantic_rewrite | 1 | [3] | 2 | True | used | 1 |
| answer-005 | cross_paragraph | 1 | [3] | 2 | True | used | 1 |
| answer-006 | clause | 1 | [3] | 1 | True | used | 1 |
| answer-007 | clause | 1 | [3] | 1 | True | returned_not_used | 0 |
| answer-008 | semantic_rewrite | 1 | [3] | 1 | True | used | 1 |
| answer-009 | clause | 1 | [3] | 1 | True | used | 1 |
| answer-010 | cross_paragraph | 1 | [3] | 3 | False | not_retrieved | 0 |
| answer-011 | not_in_kb | 1 | [3] | 0 | None | not_applicable | 1 |
| answer-012 | not_in_kb | 1 | [3] | 0 | None | not_applicable | 1 |
| answer-013 | cross_paragraph | 1 | [3] | 3 | False | not_retrieved | 0 |

## Counts

- not_applicable: 2
- not_retrieved: 2
- document_only: 0
- found_beyond_budget: 0
- returned_not_used: 1
- used: 8
- pending_review: 0

agent_context_recall@4 = 9/11 = 0.8182
