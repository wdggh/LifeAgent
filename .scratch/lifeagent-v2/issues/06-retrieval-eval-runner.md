# 06: Retrieval evaluation runner（fast/live）

**What to build:** `tests/evaluation/runners/retrieval_eval.py`：fast 模式（schema/
锚点/页界校验 + metrics 纯函数路径，无需外部服务）与 live 模式（经 05 摄取后调真实
`Retriever.search(top_k=10)` → 03 mapping → 04 metrics → 报告）；逐 query 结果、
macro/按类聚合、near-tie score gap 诊断（<0.1 复现，>=0.1 标注未复现）、回归硬门禁
（reg-001/002 chunk Recall@5==1，否则 FAIL）；输出受控 `reports/baseline-v2.0.json`，
`*.raw.json/*.log/*.tmp.json` gitignore。

**Blocked by:** 03（gold mapping）、04（metrics）、05（摄取 harness）

**Status:** open

- [ ] fast 模式在无 Chroma/DashScope 环境可跑全绿
- [ ] live 模式输出逐 query + macro + by-category 三级指标
- [ ] 回归门禁：reg-001/002 Recall@5==1 → PASS，否则整报告 FAIL
- [ ] near-tie score gap 写入报告（诊断性，不独立判失败）
- [ ] 报告 schema 受控提交；raw/log/tmp 产物 gitignore
- [ ] README 只表述"CI 验证评测框架；Live 验证真实检索"

## Comments
