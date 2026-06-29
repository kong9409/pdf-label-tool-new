# PDF 标签处理工具 v20

## 本版修复点

v20 主要修复目的地 FBA 公司名清理逻辑：

- 优先使用 PDF content stream 文本流替换：`FBA: 任意公司名` / `FBA：任意公司名` -> `FBA`
- 支持 `(FBA: xxx) Tj`
- 支持 `[(F)-0.000(B)-0.000(A)-0.000(:)...] TJ`
- 支持 `[<004600420041003a...>] TJ` 这类 UTF-16BE hex 文本
- 不再使用横向白框擦除 fallback，避免挡住右侧发货地姓名、仓库代码和地址
- 保留 `目的地：`、`FBA`、仓库代码、仓库地址、发货地姓名和地址

## 本地运行

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

## Zeabur 部署

上传本仓库到 GitHub 后，在 Zeabur 选择该 GitHub 仓库部署即可。

启动命令可填：

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

如果 Zeabur 识别为 Node 项目，也可以使用 `package.json` 里的：

```bash
npm start
```

## 输出

- 支持 PDF / ZIP 输入
- 支持 10x8、10x10、10x15 cm
- 可选添加 Made In China
- 可选按 SellerSKU 合并
- 可选上传 SellerSKU -> 仓库 SKU 映射表，并按仓库 SKU 命名
