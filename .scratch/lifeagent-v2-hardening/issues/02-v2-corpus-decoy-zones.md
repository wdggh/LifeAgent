# 02: V2 语料：10 份文档 + decoy zone

**What to build:** synthetic-personal-kb-v2 语料 = v1 六份（按 v2 规则微调/保留）
+ 产品族 A（bike_warranty_01、bike_service_record_01）+ 产品族 B
（air_purifier_purchase_01、air_purifier_warranty_01）；每份文档满足 D1–D4
（≥3 页、1 个 >1000 字符页、near-tie zone、exact-term 全局唯一），manifest v2
带每页 anchor 与 near-tie zone 声明。

**Blocked by:** 01（目录迁移）

**Status:** resolved

- [ ] 10 份文档 + manifest v2（pages/anchors/document_type/file_type）
- [ ] 两族三件套共享实体事实（型号/购买日期/金额），职责互不重叠
- [ ] D1–D4 逐文档满足；near-tie zone 在 manifest 中声明
- [ ] v2 corpus 校验（页数/锚点/唯一性/zone 字符数）通过
- [ ] 无真实个人信息与版权文本；`not_in_kb` 词（健身等）不出现

## Comments

## Answer

已实现并验证：

- `synthetic-personal-kb-v2` 语料 10 份文档（47 页）落
  `tests/evaluation/datasets/synthetic-personal-kb-v2/fixtures/corpus/`：
  - 产品族 A（自行车）：purchase_record_01（v2 扩充保修页）、bike_warranty_01
    （WTY-2025-0888）、bike_service_record_01（SRV-2025-0266）；
  - 产品族 B（净化器）：air_purifier_purchase_01（PO-2025-0113）、
    air_purifier_warranty_01（WTY-2025-0990）、device_manual_01（v2 扩充保养页）；
  - 单文档上下文：rental（9 页 near-tie p8/p9）、insurance（p4 理赔长页）、
    employment、personal_notes。
- D1–D4 验证：6 份产品族文档均 ≥3 页且至少 1 页 >1000 字符（实测各文档
  longPages≥1：purchase 1147 / manual 1096 / bike_warranty 1113 /
  bike_service 1147 / purifier_purchase 1207 / purifier_warranty 1138）；
  near-tie zone 已写入 manifest（8 份 PDF 文档声明）；exact-term 由 manifest
  `unique_terms`（10 个编号）驱动且全局唯一。
- manifest v2：corpus_version、每份文档 pages/anchors/document_type/
  file_type/near_tie_zones。
- 生成链路：OFL 字体子集（1039 字符，272KB）→ 9 份 PDF 全部生成且页数匹配；
  `validate_corpus --dataset synthetic-personal-kb-v2` 全绿：
  "10 documents, 47 pages, unique terms verified"。
- 校验器升级：unique_terms 支持 manifest 驱动（v1 缺省回退旧列表，v1 校验不变）。
- tests/evaluation 42 个 fast 用例保持全绿。

验收清单满足。下一步 V2.0.1-03 V2 queries（50 条 schema v2，含 hard candidates）。
