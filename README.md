# PDF 标签处理工具 v19

这是 Zeabur 部署版：网页前端 + Python / PyMuPDF 后端。

## 功能

1. 去掉目的地行里 `FBA` 后面的公司名/地址信息，保留 `FBA`、`目的地：`、仓库代码和地址行排版。
2. 裁剪尺寸可选择 `10×8cm`、`10×10cm`、`10×15cm`。
3. 可选在每页底部居中添加 `Made In China`；如果页面底部有“请不要遮住此标签”，会自动避开，避免重叠。
4. 可选择“先识别分组，并按 SellerSKU 合并输出”。
5. 文件命名依据可选择：
   - `SellerSKU`：输出 `SellerSKU-数量只.pdf`
   - `仓库 SKU`：上传映射表后输出 `仓库SKU-数量只.pdf`
6. 输出 ZIP 中，每个 PDF 会放在同名文件夹里，例如：

```text
SELLER-SKU-001-60只/
└── SELLER-SKU-001-60只.pdf
```

或选择仓库 SKU 映射后：

```text
WAREHOUSE-SKU-001-60只/
└── WAREHOUSE-SKU-001-60只.pdf
```

## SKU 映射表格式

支持 `.xlsx` 和 `.csv`。

推荐表头：

| sellersku | 映射仓库sku |
|---|---|
| SELLER-SKU-001 | WAREHOUSE-SKU-001 |

工具会用第一列匹配 PDF 识别出来的 SellerSKU，用第二列作为文件夹和文件名里的仓库 SKU。

## 更新到 Zeabur

将本目录里的文件放到 GitHub 仓库根目录：

```text
main.py
Dockerfile
requirements.txt
zbpack.json
static/index.html
README.md
```

提交后回 Zeabur 重新部署即可。
