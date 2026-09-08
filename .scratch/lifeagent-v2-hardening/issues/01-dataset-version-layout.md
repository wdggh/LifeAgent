# 01: Dataset 版本目录迁移（v1 冻结 / v2 就位）

**What to build:** 把现有 v1 评测资产用 `git mv` 收敛到
`tests/evaluation/datasets/synthetic-personal-kb-v1/`（corpus/pdf/fonts/
generators/dataset/queries… 及其相对引用），并新建空的
`tests/evaluation/datasets/synthetic-personal-kb-v2/`；harness/runner/
validator/测试全部参数化为 dataset root，默认指向 v2。v1 资产保持字节不变，
不再被任何 active 代码引用为默认路径。

**Blocked by:** None（可直接开工）

**Status:** resolved

- [ ] `git mv` 后 v1 内容与 baseline-v2.0.json 保持可复现（fast 校验仍绿）
- [ ] dataset root 参数化：manifest/queries/corpus 路径由 dataset 目录驱动
- [ ] 默认 dataset = synthetic-personal-kb-v2（尚未填充时允许空 manifest 报清晰错误）
- [ ] v1 目录 README 标注 FROZEN/historical
- [ ] 全量 fast 测试（tests/evaluation）通过

## Comments

## Answer

已实现并验证：

- v1 评测资产 `git mv` 到
  `tests/evaluation/datasets/synthetic-personal-kb-v1/`（fixtures: corpus/pdf/
  fonts；dataset: queries/answer_cases），内容字节不变；
- 生成器/校验器脚本从 v1 fixtures 移到共享 `tests/evaluation/tools/`
  （generate_pdfs / validate_corpus / prepare_font_subset），按 `--dataset`
  定位目标数据集；
- 新增 `tests/evaluation/datasets/paths.py`：dataset root 注册表
  （corpus/pdf/fonts/data/manifest/queries/answer_cases），ACTIVE 默认
  `synthetic-personal-kb-v2`（env `EVAL_DATASET` 可覆盖）；v2 尚未填充时所有
  active 命令以清晰 FileNotFoundError 失败；
- runner（retrieval_eval/ingest_corpus）、dataset validator、answer_review 全部
  参数化为 dataset；v1 README 标注 FROZEN/historical，v2 README 标注 ACTIVE；
- tests/evaluation/README 更新 dataset 状态与带 `--dataset` 的命令；
- 验证：tests/evaluation 42 个 fast 用例全绿；v1 dataset/corpus 校验通过
  （30 queries / 12 answer cases / 6 docs / 31 pages）；v2 默认命令报
  "dataset not ready" 清晰错误。

验收清单全部满足。下一步 V2.0.1-02 V2 语料（10 份文档 + decoy zone）。
