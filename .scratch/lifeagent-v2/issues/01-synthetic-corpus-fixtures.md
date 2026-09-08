# 01: 合成语料与确定性 PDF fixtures

**What to build:** 6 份原创中文合成语料（markdown 为唯一事实源 + 显式页边界 marker）、
`fixtures/corpus/manifest.json`（slug → 文件名/document_type/页数/每页 anchor）、
reportlab 生成器 + 仓库内提交的 OFL CJK 字体子集、提交 `fixtures/pdf/` 下生成的
PDF；fast 校验：pypdf `extract_text()` 的页数/每页 anchor/gold 页界合法，且重生成
PDF 的提取文本与提交版一致（不比较字节）。rental 第 4 条（p8）与第 5 条（p9）
做成跨页同主题、近似长度条款对，支撑 near-tie 排序复现。

**Blocked by:** None（可直接开工）

**Status:** resolved

- [ ] 6 份 corpus markdown：原创、无真实个人信息、无版权文本；文档类型符合 CONTEXT 词表
- [ ] 页边界用显式 marker，生成器消费后不渲染进 PDF 文本
- [ ] manifest.json：slug/文件名/document_type/页数/每页 anchor 完整
- [ ] `reportlab`/`fonttools` 只进 requirements-dev；OFL 字体子集与生成 PDF 提交入库
- [ ] fast 校验覆盖：页数符合预期、每页 anchor 存在、gold page 在合法范围
- [ ] 漂移校验：由 markdown 重生成的 PDF 与提交版 `extract_text()` 一致
- [ ] rental_contract_01 p8 第 4 条与 p9 第 5 条构成跨页 near-tie 条款对（同主题、长度相近、共享"违约金金额为一个月的租金"措辞、触发条件不同）
- [ ] 语料中的 exact-term 锚点（合同号/保单号/型号等）全局唯一

## Comments

## Answer

已实现并验证（本 feature 首批 commits）：

- 6 份原创合成语料落 `tests/evaluation/fixtures/corpus/`（rental 9 页 /
  insurance 6 页 / employment 5 页 / purchase 4 页 / device manual 6 页 /
  personal notes 单页 txt/md），markdown 为唯一事实源，页边界用
  `<!-- page-break -->` 显式 marker，无真实个人信息、无版权文本、无"健身"内容。
- rental 第 4 条独立成页 8、第 5 条独立成页 9，构成跨页 near-tie 条款对：同主题、
  近似长度、共享"违约金金额为一个月的租金，即人民币4500元"措辞，触发条件分别为
  提前退租/逾期腾退。修订动机：同页双条款会使 page-level gold 下的 chunk 级指标
  无法衡量两条之间的排序（假绿），拆页后 reg 门禁与 MRR 可观察语义匹配条款是否
  排在近似干扰项之前。insurance p4 理赔材料页 1023 字符，跨段可分多 chunk。
- exact-term 全局唯一已由校验器断言：RENT-2025-0310 / POL-2025-0042 /
  EMP-2024-0067 / PO-2025-0099 / INV-2025-0622 / ABC-2025-001。
- `manifest.json`：corpus_version、slug、source/file、file_type、document_type、
  pages、每页 anchor。
- 字体与 PDF：下载 OFL Noto Sans SC（google/fonts）→ 实例化 400 字重 →
  按语料字符集子集化 → 提交 `fonts/NotoSansSC-Subset.ttf`（221KB、894 字符，
  源字体不提交）；reportlab 生成 5 份 PDF 提交 `fixtures/pdf/`（personal notes
  为 txt/md 单页，不生成 PDF）。reportlab/fonttools 仅进 requirements-dev。
- 校验 `validate_corpus.py` 全绿：6 文档 31 页；pypdf `extract_text()` 页数与每页
  anchor 全部命中；无手机号/身份证号模式；rental p8 只含第四条、p9 只含第五条
  （条款不跨页）且共享违约金措辞的结构断言通过。
- 生成器页数与 markdown segment 数不符时会硬失败（防内容溢出漂移页）。

验收清单全部满足。下一步进入 V2.0-02 Evaluation Dataset。
