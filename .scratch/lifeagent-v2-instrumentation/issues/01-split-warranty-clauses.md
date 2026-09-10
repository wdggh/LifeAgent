# 01: 拆分保修文档 near-tie 条款到相邻页

**What to build:** bike_warranty_01 与 air_purifier_warranty_01 各拆一页
（4→5 页），把"保修范围"与"非保修/保修流程"分到相邻页，使 page-level gold
能区分条款排序；更新 manifest（pages/anchors/near_tie_zones/revision）、
重新生成 PDF、通过 corpus 校验。

**Blocked by:** None

**Status:** claimed

- [ ] 两份文档各 5 页；近义条款不再共用长页
- [ ] manifest revision="v2.0.2-instrumentation"，anchors 与新页匹配
- [ ] PDF 重新生成；validate_corpus 通过（页数/锚点/10 个唯一编号）
- [ ] query/answer_cases 文件零改动

## Comments
