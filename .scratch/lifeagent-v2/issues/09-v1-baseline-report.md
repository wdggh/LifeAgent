# 09: V1 baseline 实验与报告

**What to build:** 跑通真实 V1 dense baseline（PostgreSQL + Chroma + DashScope +
KnowledgeService/Retriever），产出并提交受控 `reports/baseline-v2.0.json`：
experiment/dataset_version/retriever 配置/commit、三级指标 macro + by-category、
reg 门禁结果、near-tie score gap、answer-level 状态（READY/PARTIAL，允许先发布
Retrieval READY + Answer PARTIAL）；README 进度表由 TBD 占位替换为真实数字；
raw/log 产物不提交。

**Blocked by:** 06（runner，含 07 门禁）；08 不阻塞（可部分状态发布）

**Status:** resolved

- [ ] live 全链路跑通：摄取 6 份语料 → 30 条 query → 三级指标
- [ ] reg-001/002 门禁 PASS（FAIL 则报告不发布）
- [ ] baseline-v2.0.json 结构与 spec 一致并提交；原始输出 gitignore
- [ ] near-tie score gap 记录（<0.1 复现 / >=0.1 未复现）
- [ ] answer-level 人工审查完成或明确标 PARTIAL；不阻塞 retrieval baseline
- [ ] README 指标表更新为真实数字（来源指向报告文件）

## Comments

## Answer

已跑通并提交（2026-09-09，真实栈：PostgreSQL + Chroma + DashScope
text-embedding-v3:1024）：

命令：`python -m tests.evaluation.runners.retrieval_eval live --reset`

- 结果：`status=PASS`；30 条 query；overall 三级指标
  document/page/chunk 的 MRR@5 与 Recall@5/10 均为 1.0000，chunk NDCG@5
  = 0.9973（唯一非满分来自 cross_paragraph 类 0.9732——理赔材料多 chunk 的
  排序衰减，属真实可观察信号）。
- Regression gate：reg-001/reg-002 chunk Recall@5=1 → PASS；near-tie 复现
  （dense score gap 0.0947 / 0.0135，均 <0.1）。
- 受控报告 `tests/evaluation/reports/baseline-v2.0.json` 已提交；raw/log/tmp
  产物保持 gitignore。
- `tests/evaluation/README.md` 指标表已由 TBD 替换为真实数字并指向报告。
- Answer-level review 状态 PENDING（人工审查不阻塞 retrieval baseline 发布，
  与 spec 一致）。

V2.0（Evaluation & Baseline）至此全部 9 张 ticket resolved。V2.0 目标达成：
先测出 V1 baseline，后续 V2.1 起的每次检索改动都可与此报告对比。
