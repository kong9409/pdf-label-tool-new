# v15 文本流替换版说明

本版本针对“擦除容易误伤目的地 / FBA / 仓库代码”的问题做了核心调整：

1. 优先使用 PDF 内容流文本替换，而不是视觉遮挡。
   - 将 `FBA: 任意公司名或地址` 直接替换为 `FBA`。
   - 保留原始字体、字号、坐标和排版。
   - 不保留冒号。

2. 如果同一页中存在 `FBA: Changshapengxinkejiyouxiangongsi`、`FBA: Chaozhou Zero to One Cultural Media Co., Ltd` 或其他中文/英文/拼音形式，公司名都按同一行文本替换逻辑处理。

3. SellerSKU 识别逻辑保留：
   - 优先读取 `Single SKU` 下一行。
   - 数量按每页 `数量` 字段累加。
   - 单个 SKU 也命名为 `SellerSKU-数量只.pdf`。

4. 如果勾选“先识别分组”，同 SellerSKU 合并，不同 SellerSKU 分开输出。
   不勾选则按原 PDF 文件输出。

更新 Zeabur 时，重点覆盖：

```
main.py
static/index.html
```
