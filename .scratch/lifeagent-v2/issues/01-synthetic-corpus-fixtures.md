# 01: 合成语料与确定性 PDF fixtures

**What to build:** 6 份原创中文合成语料（markdown 为唯一事实源 + 显式页边界 marker）、
`fixtures/corpus/manifest.json`（slug → 文件名/document_type/页数/每页 anchor）、
reportlab 生成器 + 仓库内提交的 OFL CJK 字体子集、提交 `fixtures/pdf/` 下生成的
PDF；fast 校验：pypdf `extract_text()` 的页数/每页 anchor/gold 页界合法，且重生成
PDF 的提取文本与提交版一致（不比较字节）。rental page 8 的第 4/5 条做成同主题、
近似长度条款对，支撑 near-tie 复现。

**Blocked by:** None（可直接开工）

**Status:** open

- [ ] 6 份 corpus markdown：原创、无真实个人信息、无版权文本；文档类型符合 CONTEXT 词表
- [ ] 页边界用显式 marker，生成器消费后不渲染进 PDF 文本
- [ ] manifest.json：slug/文件名/document_type/页数/每页 anchor 完整
- [ ] `reportlab`/`fonttools` 只进 requirements-dev；OFL 字体子集与生成 PDF 提交入库
- [ ] fast 校验覆盖：页数符合预期、每页 anchor 存在、gold page 在合法范围
- [ ] 漂移校验：由 markdown 重生成的 PDF 与提交版 `extract_text()` 一致
- [ ] rental_contract_01 p8 第 4 条/第 5 条构成 near-tie 条款对（同主题、长度相近、金额不同）
- [ ] 语料中的 exact-term 锚点（合同号/保单号/型号等）全局唯一

## Comments
