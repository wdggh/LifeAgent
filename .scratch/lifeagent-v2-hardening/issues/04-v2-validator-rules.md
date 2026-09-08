# 04: V2 校验器：schema v2 + N/D 规则

**What to build:** v2 dataset validator：schema v2 结构（gold 数组、version、
decoy/difficulty 字段）、类别分布、slug/页界；N1–N5 机器可断言的子集
（decoy 存在且不与 gold 交集、hard candidate 的 decoy 数量、位置门、编号唯一）
与 D1–D5（页数、near-tie zone 字符数、页码覆盖、exact-term 唯一）。v1 数据
不被该校验器读取。

**Blocked by:** 02、03（语料与 queries 就位）

**Status:** open

- [ ] schema v2 结构校验（gold 数组/mandatory/version/字段白名单）
- [ ] N1/N3/N4/N5 可执行断言；N2 由 difficulty_note 人工声明
- [ ] D1–D5 断言（含 zone 页 >1000 字符）
- [ ] fast 模式全绿；v1 文件零读取

## Comments
