# 04: 评测指标 Recall / MRR / NDCG

**What to build:** `tests/evaluation/metrics/{recall,mrr,ndcg}.py` 纯函数实现：
Recall@5/10、MRR@5（first relevant）、NDCG@5（binary relevance），支持
document/page/chunk-derived 三级；逐 query 计算 + macro 平均；无 gold 的 query
记入计数但排除在均值外；配套手工列表单测覆盖空结果、gold 在 K 外、多 gold 去重、
K 截断、IDCG 饱和等边界。

**Blocked by:** 03（相关性与投影语义）

**Status:** resolved

- [ ] recall/mrr/ndcg 纯函数实现，参数化 K
- [ ] 三级指标统一入口：输入结果列表 + gold（doc/pages/G）→ 各级 metric dict
- [ ] macro 平均与按类分组聚合
- [ ] 边界单测：空 gold、K=0/超出、首相关不在 top-K、多个 gold 项、去重
- [ ] 单元测试全部可在无 Chroma/DashScope 环境运行（fast）

## Comments

## Answer

已实现并验证（纯函数，fast 无外部依赖；未串联 Retriever/Chroma）：

- `tests/evaluation/metrics/{recall,mrr,ndcg}.py`：Recall@K、MRR@K
  （first relevant result）、NDCG@K（binary relevance）。NDCG 的 IDCG 按
  `min(k, gold_total)` 个理想相关项计算（gold=3 只召回 1 时不会得 1.0，
  有专门饱和测试）。
- `tests/evaluation/metrics/levels.py`：`compute_query_metrics` 统一入口，
  输入结果列表 + gold（document/pages/G）→ document/page/chunk 三级指标
  （recall@5/10、mrr@5、ndcg@5）；document/page/chunk 逐级按首现去重；
  no-gold query（not_in_kb）返回 None，不计入指标平均。
- `tests/evaluation/metrics/aggregate.py`：macro 平均与按 category 分组聚合。
- `tests/evaluation/metrics/test_metrics.py`：10 个 fast 用例全绿，覆盖：
  recall 截断、MRR 空/越界、NDCG binary 与 IDCG 饱和、三级投影（同 query 下
  document MRR=0.5、page MRR=1/3、chunk recall/ndcg 分列）、跨页 chunk 覆盖
  两个 gold pages、重复结果去重、空结果、no-gold→None、gold page 超出覆盖、
  macro/按类聚合。

验收清单全部满足。下一步 V2.0-05 Real ingestion & isolated harness
（或先做 V2.0-08 answer-level 审查清单，二者互不阻塞）。
