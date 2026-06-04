# v17 更新说明

- 保留“目的地：”后面的冒号，不再去掉。
- 其他功能保持 v16 不变：
  - 文本流替换清理 FBA 后面的公司/地址信息；
  - 支持 10×8 / 10×10 / 10×15cm；
  - 可选添加 Made In China，并避开“请不要遮住此标签”；
  - 可按 SellerSKU 分组输出，命名为 SellerSKU-数量只.pdf。

更新 Zeabur 时，至少覆盖：

```
main.py
static/index.html
```
