# 02: Live A/B + 13 条 answer 重跑 + 归因分析

**What to build:** A=dense-only（应等于 baseline-v2.0.2）；B=reserved_slot
（dense top(L−1) + 1 个 sparse-only 槽位，expansion/rewrite 关闭），产出
`experiment-v2.3c-reserved-slot.json`。按预注册标准判定 (i)–(iv)，并输出
诊断：reserved slot 使用次数/命中 gold 次数、answer-013 的 purchase p3 从
sparse rank → fused rank → Agent top-4 的完整链路。重跑 13 条 answer
（answer-013 为达标项，answer-010 仅跟踪），如评分变化需用户确认。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A 与 baseline 逐项一致；B 产出受控报告（raw gitignore）
- [ ] 标准 (i)–(iv) 逐条判定；easy-40 回退 >0.01 必须判失败
- [ ] answer-013 诊断链完整记录（p3 是否进入 top-4、最终 source 是否购买记录）
- [ ] 13 条 answer 重跑（如评分变化提交用户确认；未变则沿用 v2.2 review）
- [ ] 结论与未达标项写入 README/分析报告；失败时先归因而非改参数

## Comments
