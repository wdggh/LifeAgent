# 07: 9addb1a 双层回归套件

**What to build:** 检索级回归：queries.jsonl 内 reg-001/reg-002（clause_specific），
runner 硬门禁 Recall@5==1；工具级回归：`test_review_fixes.py` 现有 top_k=1 →
MIN_TOP_K=3 floor 用例**保留不移除**，新增检查确保评测套件引用/覆盖两层；两层的
职责边界写清（recall 是行为门禁，score gap 是诊断）。

**Blocked by:** 02（reg-001/002 随 dataset 落地）

**Status:** open

- [ ] reg-001/reg-002 存在于 queries.jsonl 且分别指向 rental_contract_01
      p8/p9 两条近义条款；query 文本不泄露条款号，使 MRR/Recall 能衡量
      语义匹配条款是否排在近似干扰项之前
- [ ] runner 门禁与报告 FAIL/PASS 语义一致（见 06）
- [ ] `test_review_fixes.py` 工具级回归保持原样并纳入套件说明
- [ ] 套件说明文档写明双层职责与"评测框架不迁移既有工程回归"

## Comments
