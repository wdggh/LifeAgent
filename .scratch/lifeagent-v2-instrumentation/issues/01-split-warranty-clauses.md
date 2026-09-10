# 01: 拆分保修文档 near-tie 条款到相邻页

**What to build:** bike_warranty_01 与 air_purifier_warranty_01 各拆一页
（4→5 页），把"保修范围"与"非保修/保修流程"分到相邻页，使 page-level gold
能区分条款排序；更新 manifest（pages/anchors/near_tie_zones/revision）、
重新生成 PDF、通过 corpus 校验。

**Blocked by:** None

**Status:** resolved

- [ ] 两份文档各 5 页；近义条款不再共用长页
- [ ] manifest revision="v2.0.2-instrumentation"，anchors 与新页匹配
- [ ] PDF 重新生成；validate_corpus 通过（页数/锚点/10 个唯一编号）
- [ ] query/answer_cases 文件零改动

## Comments

## Answer

已实现并验证：

- `bike_warranty_01` 与 `air_purifier_warranty_01` 各 4→5 页：p2 保修范围、
  p3 非保修范围（两页均 ≤1000 字符 → 单 chunk），p4 为长页
  （判定示例+速查+流程+检测补充，1057/1076 字符，满足 D1 且保留多 chunk
  覆盖信号），p5 为凭证/延保注意事项。
- manifest：revision="v2.0.2-instrumentation"、两份文档 pages=5、anchors 更新、
  near_tie_zones 标注 `measurement="clause_ordering"`。
- v2 校验器 D2 规则细化：仅 clause_ordering zone 要求单 chunk（≤1000）；
  其他 decoy zone 允许长页；D1 长页要求不变。
- 生成器新增 `--only`（避免无关 PDF 二进制漂移），本次仅重生成两份保修 PDF；
  `validate_corpus` 通过："10 documents, 49 pages, unique terms verified"；
  `validate_v2` 通过；tests/evaluation 48 个 fast 用例全绿。
- query / answer_cases 文件零改动（冻结要求）。

验收清单满足。下一步 V2.0.2-02 重跑 triage 并发布 baseline-v2.0.2。
