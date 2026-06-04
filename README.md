# PDF 标签处理工具 - Zeabur 部署版 v11

## 功能说明

1. 去掉 FBA 后面的公司名字，保留 FBA 和周围版式。
2. 裁剪尺寸可选择：10cm × 8cm、10cm × 10cm、10cm × 15cm。
3. 可自行选择是否添加 Made In China；添加位置为页面底部居中，距离底部约 0.5cm。
4. 可选择“先识别分组，并按 SellerSKU 合并输出”：同 SellerSKU 多个货件会合并生成同一个 PDF，不同 SellerSKU 会分开输出不同 PDF。
5. 按 SellerSKU 合并时，文件命名格式为：`SellerSKU-数量只.pdf`。

## 输出模式

### 勾选“先识别分组，并按 SellerSKU 合并输出”

- 每一页读取 `Single SKU` 下方的 SellerSKU。
- 只有 SellerSKU 完全一致才合并。
- 不同 SellerSKU 分别输出不同 PDF。
- 文件名格式：`SellerSKU-数量只.pdf`。

### 不勾选“先识别分组，并按 SellerSKU 合并输出”

- 按原 PDF 文件输出。
- 不会跨文件、跨 SellerSKU 合并。
- 只做清理 FBA 后缀、裁剪尺寸、可选添加 Made In China。

## Zeabur 部署

1. 把本文件夹全部上传到 GitHub 仓库根目录。
2. 打开 Zeabur 项目：https://zeabur.com/projects
3. 进入对应 Project，点击 Add Service / New Service。
4. 选择 GitHub。
5. 选择刚才上传的仓库。
6. Zeabur 会读取 Dockerfile 并部署。
7. 部署完成后打开 Zeabur 提供的域名，即可使用。

## 本地测试（可选）

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

然后打开 http://127.0.0.1:8080
