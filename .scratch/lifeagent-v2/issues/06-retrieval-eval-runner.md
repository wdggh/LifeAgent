# 06: Retrieval evaluation runner（fast/live）

**What to build:** `tests/evaluation/runners/retrieval_eval.py`：fast 模式（schema/
锚点/页界校验 + metrics 纯函数路径，无需外部服务）与 live 模式（经 05 摄取后调真实
`Retriever.search(top_k=10)` → 03 mapping → 04 metrics → 报告）；逐 query 结果、
macro/按类聚合、near-tie score gap 诊断（<0.1 复现，>=0.1 标注未复现）、回归硬门禁
（reg-001/002 chunk Recall@5==1，否则 FAIL）；输出受控 `reports/baseline-v2.0.json`，
`*.raw.json/*.log/*.tmp.json` gitignore。

**Blocked by:** 03（gold mapping）、04（metrics）、05（摄取 harness）

**Status:** resolved

- [ ] fast 模式在无 Chroma/DashScope 环境可跑全绿
- [ ] live 模式输出逐 query + macro + by-category 三级指标
- [ ] 回归门禁：reg-001/002 Recall@5==1 → PASS，否则整报告 FAIL
- [ ] near-tie score gap 写入报告（诊断性，不独立判失败）
- [ ] 报告 schema 受控提交；raw/log/tmp 产物 gitignore
- [ ] README 只表述"CI 验证评测框架；Live 验证真实检索"

## Comments

## Answer

已实现并验证（代码完成；live 真跑随 V2.0-09 执行）：

- `tests/evaluation/runners/retrieval_eval.py`：
  - `evaluate_query`：单条 query → 真实 Retriever.search(top_k=10) →
    V2.0-03 runtime gold mapping → V2.0-04 三级指标；near-tie dense score gap
    诊断（<0.1 复现 / >=0.1 未复现 / decoy 未召回为 None，仅诊断不判失败）；
  - `build_report`：overall 三级 macro + by-category + regression gate
    （reg-001/002 chunk Recall@5==1，否则 status=FAIL）+ answer_level 占位；
  - CLI：`fast`（dataset/corpus/PDF 校验 + canned metrics，CI 安全）与
    `live`（复用 V2.0-05 live_harness 摄取 → 真实 Retriever → 写
    `reports/baseline-v2.0.json`）；
- `tests/evaluation/runners/test_retrieval_eval.py`：3 个 fast 用例全绿
  （回归 PASS + near-tie 复现、gold 掉出 Top5 时门禁 FAIL、decoy 缺失时 gap 仅
  诊断不阻断）。
- README 记录 fast/live 命令；.gitignore 覆盖 reports 的 raw/log/tmp 产物。

验收清单满足。下一步 V2.0-07 9addb1a 双层回归套件（工具级回归引用与套件说明），
然后 V2.0-09 用 `live --reset` 产出 baseline。
