# PDF 标签处理工具 v12

## 本版修复

1. SellerSKU 识别增强：支持 `FD-US-...`、`FDM888A-FX-US` 等多种 SKU 格式。
2. 目的地 FBA 行清理增强：不再只匹配固定公司名，而是删除 `FBA:` / `FBA：` 后面的同一行英文、中文或拼音地址/公司名。
3. 单 SKU 文件命名：即使只有一个 SellerSKU，也默认输出 `SellerSKU-数量只.pdf`。
4. 保留 Made In China 可选项。
5. 支持 10x8、10x10、10x15cm。

## 更新到 GitHub / Zeabur

把本文件夹里的内容放到 GitHub 仓库根目录，确保根目录直接包含：

```
main.py
Dockerfile
requirements.txt
static/index.html
```

提交后 Zeabur 会自动重新部署，或在 Zeabur 后台点击 Redeploy。
