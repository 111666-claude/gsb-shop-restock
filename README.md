# shop-restock

商店限购与每天刷新，只用 Python 标准库。

```
python3 -m shoprestock.cli --sample daily
python3 -m shoprestock.cli --sample money
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **限购按天独立**：每天的购买次数单独计数，服务器日期（05:00 刷新）变化时清零。
  `--sample daily`（限购 3，第一天买满 3 次、第二天再买 1 次）按口径是 `next_day_ok=True`，
  现在累计到 4 就拒绝，给 `next_day_ok=False`。
- **余额不足要拒绝**：余额小于售价时返回 `ShopError`，余额不变。
  `--sample money`（余额 5、售价 10）按口径是 `money=rejected`，现在扣成 `money=-5`。
- 刷新时刻：每天 05:00（服务器时区）重置购买计数，跨天以服务器日期为准。
- 不变量：`bought_today <= daily_limit`；余额永不为负；同一批购买重复执行结果相同。
- 规模：1000 种商品、每秒 10 万次购买 1 秒内完成，内存 O(商品数)。

## 现在的行为

- `buy` 用 `shop.purchases[item]` 累计计数，从不按天清零。
- 扣钱前不校验余额，余额可以变负。
- `refresh_hour`/`last_day` 存了但没人用。

## 输出

```
next_day_ok=True money=970
money=rejected
```

## 目录

```
shoprestock/shop.py   限购与扣款
shoprestock/cli.py    命令行入口
tests/                unittest 用例
```
