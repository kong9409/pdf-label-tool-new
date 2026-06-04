# Zeabur PDF 标签工具更新说明 - Made In China 修复版

本版本修复：勾选“每页底部添加 Made In China”后，处理结果中没有显示的问题。

## 修改原因
旧版使用 `insert_textbox` 写入文字，在部分 PDF 页面通过 `show_pdf_page` 缩放后，文字框过紧会被 PyMuPDF 静默跳过，导致没有显示。

## 修复方式
新版改为使用 `insert_text` 按坐标直接写入：

- 文案：`Made In China`
- 位置：页面底部正中间
- 距离底部：约 0.5cm
- 字号：网页中可设置，默认 8pt

## 更新到 Zeabur

如果你的 Zeabur 服务是从 GitHub 仓库部署：

1. 解压本 ZIP。
2. 用本 ZIP 里的文件覆盖你 GitHub 仓库中的旧文件，尤其是 `main.py`。
3. 提交并 Push 到 GitHub。
4. 回到 Zeabur 服务页面，点击 Redeploy，或等待自动部署。

如果你是直接在 Zeabur 上传压缩包部署：

1. 在 Zeabur 服务页面删除旧服务或重新部署。
2. 上传本 ZIP 解压后的项目文件。
3. 等待构建完成。

部署完成后，打开你的工具网址，勾选“每页底部添加 Made In China”，重新上传原始 PDF/ZIP 测试。
