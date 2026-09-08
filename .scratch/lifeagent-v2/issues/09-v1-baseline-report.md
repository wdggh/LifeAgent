# 09: V1 baseline 实验与报告

**What to build:** 跑通真实 V1 dense baseline（PostgreSQL + Chroma + DashScope +
KnowledgeService/Retriever），产出并提交受控 `reports/baseline-v2.0.json`：
experiment/dataset_version/retriever 配置/commit、三级指标 macro + by-category、
reg 门禁结果、near-tie score gap、answer-level 状态（READY/PARTIAL，允许先发布
Retrieval READY + Answer PARTIAL）；README 进度表由 TBD 占位替换为真实数字；
raw/log 产物不提交。

**Blocked by:** 06（runner，含 07 门禁）；08 不阻塞（可部分状态发布）

**Status:** open

- [ ] live 全链路跑通：摄取 6 份语料 → 30 条 query → 三级指标
- [ ] reg-001/002 门禁 PASS（FAIL 则报告不发布）
- [ ] baseline-v2.0.json 结构与 spec 一致并提交；原始输出 gitignore
- [ ] near-tie score gap 记录（<0.1 复现 / >=0.1 未复现）
- [ ] answer-level 人工审查完成或明确标 PARTIAL；不阻塞 retrieval baseline
- [ ] README 指标表更新为真实数字（来源指向报告文件）

## Comments
