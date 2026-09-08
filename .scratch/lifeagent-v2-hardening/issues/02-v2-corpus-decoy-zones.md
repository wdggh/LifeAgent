# 02: V2 语料：10 份文档 + decoy zone

**What to build:** synthetic-personal-kb-v2 语料 = v1 六份（按 v2 规则微调/保留）
+ 产品族 A（bike_warranty_01、bike_service_record_01）+ 产品族 B
（air_purifier_purchase_01、air_purifier_warranty_01）；每份文档满足 D1–D4
（≥3 页、1 个 >1000 字符页、near-tie zone、exact-term 全局唯一），manifest v2
带每页 anchor 与 near-tie zone 声明。

**Blocked by:** 01（目录迁移）

**Status:** claimed

- [ ] 10 份文档 + manifest v2（pages/anchors/document_type/file_type）
- [ ] 两族三件套共享实体事实（型号/购买日期/金额），职责互不重叠
- [ ] D1–D4 逐文档满足；near-tie zone 在 manifest 中声明
- [ ] v2 corpus 校验（页数/锚点/唯一性/zone 字符数）通过
- [ ] 无真实个人信息与版权文本；`not_in_kb` 词（健身等）不出现

## Comments
