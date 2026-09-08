# 04: 评测指标 Recall / MRR / NDCG

**What to build:** `tests/evaluation/metrics/{recall,mrr,ndcg}.py` 纯函数实现：
Recall@5/10、MRR@5（first relevant）、NDCG@5（binary relevance），支持
document/page/chunk-derived 三级；逐 query 计算 + macro 平均；无 gold 的 query
记入计数但排除在均值外；配套手工列表单测覆盖空结果、gold 在 K 外、多 gold 去重、
K 截断、IDCG 饱和等边界。

**Blocked by:** 03（相关性与投影语义）

**Status:** claimed

- [ ] recall/mrr/ndcg 纯函数实现，参数化 K
- [ ] 三级指标统一入口：输入结果列表 + gold（doc/pages/G）→ 各级 metric dict
- [ ] macro 平均与按类分组聚合
- [ ] 边界单测：空 gold、K=0/超出、首相关不在 top-K、多个 gold 项、去重
- [ ] 单元测试全部可在无 Chroma/DashScope 环境运行（fast）

## Comments
