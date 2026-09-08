# 07: 9addb1a 双层回归套件

**What to build:** 检索级回归：queries.jsonl 内 reg-001/reg-002（clause_specific），
runner 硬门禁 Recall@5==1；工具级回归：`test_review_fixes.py` 现有 top_k=1 →
MIN_TOP_K=3 floor 用例**保留不移除**，新增检查确保评测套件引用/覆盖两层；两层的
职责边界写清（recall 是行为门禁，score gap 是诊断）。

**Blocked by:** 02（reg-001/002 随 dataset 落地）

**Status:** resolved

- [ ] reg-001/reg-002 存在于 queries.jsonl 且分别指向 rental_contract_01
      p8/p9 两条近义条款；query 文本不泄露条款号，使 MRR/Recall 能衡量
      语义匹配条款是否排在近似干扰项之前
- [ ] runner 门禁与报告 FAIL/PASS 语义一致（见 06）
- [ ] `test_review_fixes.py` 工具级回归保持原样并纳入套件说明
- [ ] 套件说明文档写明双层职责与"评测框架不迁移既有工程回归"

## Comments

## Answer

已实现并验证：

- `tests/evaluation/regression/README.md`：9addb1a 双层回归职责说明（Retrieval
  level = reg-001/002 + runner Recall@5==1 硬门禁；Tool level =
  test_review_fixes.py 的 top_k=1 → MIN_TOP_K=3 floor；score gap 仅诊断；
  评测框架不得迁移既有工程回归）。
- `tests/evaluation/regression/test_9addb1a_regression_suite.py`：4 个 fast
  canary 用例全绿：
  - reg-001/reg-002 存在于 queries.jsonl 且分别指向 rental p8/p9；
  - 问题文本不泄露条款号；
  - runner 门禁语义：任一 reg chunk Recall@5<1 → 报告 FAIL；
  - 工具级工程回归仍存在于 `test_review_fixes.py`
    （函数名 + top_k=1 + effective top_k==3 断言），被误删/误迁移会立刻失败。

验收清单满足。剩余 V2.0-09：`python -m tests.evaluation.runners.retrieval_eval
live --reset`（需 Docker + DashScope key）产出并提交 baseline 报告。
