# 04: V2 校验器：schema v2 + N/D 规则

**What to build:** v2 dataset validator：schema v2 结构（gold 数组、version、
decoy/difficulty 字段）、类别分布、slug/页界；N1–N5 机器可断言的子集
（decoy 存在且不与 gold 交集、hard candidate 的 decoy 数量、位置门、编号唯一）
与 D1–D5（页数、near-tie zone 字符数、页码覆盖、exact-term 唯一）。v1 数据
不被该校验器读取。

**Blocked by:** 02、03（语料与 queries 就位）

**Status:** resolved

- [ ] schema v2 结构校验（gold 数组/mandatory/version/字段白名单）
- [ ] N1/N3/N4/N5 可执行断言；N2 由 difficulty_note 人工声明
- [ ] D1–D5 断言（含 zone 页 >1000 字符）
- [ ] fast 模式全绿；v1 文件零读取

## Comments

## Answer

已实现并验证：

- `tests/evaluation/dataset/validate_v2.py`（只读 synthetic-personal-kb-v2，
  不触碰 v1 冻结文件）：
  - schema v2：字段白名单、schema_version=2、gold 数组（全 mandatory）、
    类别受控词表、id 唯一、页界检查；
  - 分布权威计数：50 条（simple 8 / semantic 10 / exact 6 / numeric 6 /
    clause 6 / cross_paragraph 4 / clause_specific 4 / cross_document 6）；
  - N 规则可执行子集：clause_specific 必须 reg-* 且不泄露条款号；
    hard_candidate 必须有 difficulty_note（含 N1–N5 标记）与 decoy；
    非 reg hard 的 decoys ≥2 且不与 gold 相交；reg 同文档 decoy 要求
    note 声明"同文档/近义"；
  - N4/D3：单文档 hard 不允许只有首页 gold；cross_document 至少一条腿
    非首页；
  - D1/D2：产品族 6 份文档 ≥3 页、至少一页 >1000 字符、manifest 声明
    near-tie zone 且 zone 覆盖 >1000 字符页；
  - D4/D5：manifest unique_terms 全语料恰出现一次；源页数与每页 anchor
    与 manifest 一致。
- 为满足 D3 修订 cd-001/cd-005 的 gold（增加非首页腿：bike_warranty p3、
  insurance p5），跨文档 6 条全部通过位置门。
- `tests/evaluation/dataset/test_validate_v2.py`：canary 用例全绿；输出
  "v2 ok: 10 documents / 50 queries, hard_candidates=16"。

验收清单满足。下一步 V2.0.1-05 Multi-doc gold 的 mapping/metrics/runner
泛化。
