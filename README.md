# PDF 标签处理工具 - Zeabur 部署版

## 功能

- 上传 PDF 或 ZIP。
- 按页面识别 `Single SKU` 下方的 SKU。
- 只有 SKU 完全一致才合并。
- 输出为多个 PDF：`SKU-数量只.pdf`。
- 支持尺寸：10cm x 8cm、10cm x 10cm、10cm x 15cm。
- 可选在每页底部居中添加 `Made In China`，距离底部约 0.5cm。
- 后端使用 Python + PyMuPDF 解析 PDF 文本层，比纯 HTML / pdf.js 更快、更稳定。

## Zeabur 部署

1. 把本文件夹全部上传到一个 GitHub 仓库。
2. 打开 Zeabur 项目：https://zeabur.com/projects
3. 点击 Add Service / New Service。
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
