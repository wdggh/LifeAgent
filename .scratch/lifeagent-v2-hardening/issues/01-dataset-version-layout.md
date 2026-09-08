# 01: Dataset 版本目录迁移（v1 冻结 / v2 就位）

**What to build:** 把现有 v1 评测资产用 `git mv` 收敛到
`tests/evaluation/datasets/synthetic-personal-kb-v1/`（corpus/pdf/fonts/
generators/dataset/queries… 及其相对引用），并新建空的
`tests/evaluation/datasets/synthetic-personal-kb-v2/`；harness/runner/
validator/测试全部参数化为 dataset root，默认指向 v2。v1 资产保持字节不变，
不再被任何 active 代码引用为默认路径。

**Blocked by:** None（可直接开工）

**Status:** claimed

- [ ] `git mv` 后 v1 内容与 baseline-v2.0.json 保持可复现（fast 校验仍绿）
- [ ] dataset root 参数化：manifest/queries/corpus 路径由 dataset 目录驱动
- [ ] 默认 dataset = synthetic-personal-kb-v2（尚未填充时允许空 manifest 报清晰错误）
- [ ] v1 目录 README 标注 FROZEN/historical
- [ ] 全量 fast 测试（tests/evaluation）通过

## Comments
