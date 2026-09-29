import unittest

from shoprestock.shop import Shop, ShopError, buy


class BuyTest(unittest.TestCase):
    def test_first_buy(self):
        shop = Shop({"potion": (10, 3)})
        money, bought = buy(shop, "potion", 1, 100)
        self.assertEqual((money, bought), (90, 1))

    def test_unknown_item(self):
        with self.assertRaises(ShopError):
            buy(Shop({}), "ghost", 1, 10)

    def test_limit_is_three(self):
        shop = Shop({"potion": (10, 3)})
        for _ in range(3):
            buy(shop, "potion", 1, 100)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 100)

    def test_stock_and_refresh_hour(self):
        shop = Shop({"potion": (10, 3)}, refresh_hour=5)
        self.assertEqual(shop.stock["potion"], (10, 3))
        self.assertEqual(shop.refresh_hour, 5)


if __name__ == "__main__":
    unittest.main()


class DailyResetTest(unittest.TestCase):
    def test_next_day_resets_count(self):
        shop = Shop({"potion": (10, 3)})
        money = 1000
        for _ in range(3):
            money, _ = buy(shop, "potion", 20260929, money)
        money, bought = buy(shop, "potion", 20260930, money)
        self.assertEqual(bought, 1)
        self.assertEqual(money, 960)

    def test_same_day_limit_still_enforced(self):
        shop = Shop({"potion": (10, 3)})
        for _ in range(3):
            buy(shop, "potion", 20260929, 1000)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 20260929, 1000)

    def test_counts_are_independent_per_item(self):
        shop = Shop({"potion": (10, 1), "ether": (20, 1)})
        buy(shop, "potion", 1, 1000)
        money, bought = buy(shop, "ether", 1, 1000)
        self.assertEqual(bought, 1)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 1000)

    def test_refresh_hour_boundary(self):
        from datetime import datetime

        from shoprestock.shop import server_day
        self.assertEqual(server_day(datetime(2026, 9, 30, 4, 59)).isoformat(), "2026-09-29")
        self.assertEqual(server_day(datetime(2026, 9, 30, 5, 0)).isoformat(), "2026-09-30")
        self.assertEqual(server_day(datetime(2026, 9, 30, 23, 59)).isoformat(), "2026-09-30")


class BalanceTest(unittest.TestCase):
    def test_insufficient_balance_rejected(self):
        shop = Shop({"potion": (10, 3)})
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 5)

    def test_rejection_keeps_state(self):
        shop = Shop({"potion": (10, 3)})
        try:
            buy(shop, "potion", 1, 5)
        except ShopError:
            pass
        self.assertEqual(shop.purchases.get("potion", 0), 0)
        money, bought = buy(shop, "potion", 1, 10)
        self.assertEqual((money, bought), (0, 1))

    def test_exact_balance_ok(self):
        shop = Shop({"potion": (10, 3)})
        money, _ = buy(shop, "potion", 1, 10)
        self.assertEqual(money, 0)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 0)

    def test_failed_limit_buy_does_not_charge(self):
        shop = Shop({"potion": (10, 1)})
        money, _ = buy(shop, "potion", 1, 100)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, money)
        self.assertEqual(money, 90)


class ReferenceModel:
    """参考实现：按天计数 + 余额校验，用于逐步对照。"""

    def __init__(self, stock):
        self.stock = dict(stock)
        self.counts = {}
        self.day = None

    def buy(self, item, day, money):
        price, limit = self.stock[item]
        if day != self.day:
            self.counts = {}
            self.day = day
        if self.counts.get(item, 0) >= limit:
            return money, self.counts[item], "limit"
        if money < price:
            return money, self.counts.get(item, 0), "money"
        self.counts[item] = self.counts.get(item, 0) + 1
        return money - price, self.counts[item], "ok"


class DifferentialTest(unittest.TestCase):
    def test_random_sequences_match_reference(self):
        import random

        rng = random.Random(20260930)
        stock = {"item%d" % i: (rng.randint(1, 50), rng.randint(1, 4)) for i in range(8)}
        for _ in range(200):
            shop = Shop(stock)
            ref = ReferenceModel(stock)
            day = rng.randint(20260901, 20260905)
            money = rng.randint(0, 200)
            for _ in range(rng.randint(1, 40)):
                item = rng.choice(list(stock))
                if rng.random() < 0.4:
                    day += rng.randint(0, 2)  # 跨天（也可能不跨）
                before = money
                try:
                    money, bought = buy(shop, item, day, before)
                    outcome = "ok"
                except ShopError:
                    bought = shop.purchases.get(item, 0)
                    outcome = None
                ref_money, ref_bought, ref_status = ref.buy(item, day, before)
                self.assertEqual(money, ref_money)
                self.assertEqual(bought, ref_bought)
                if outcome is None:
                    self.assertIn(ref_status, ("limit", "money"))
                else:
                    self.assertEqual(ref_status, "ok")
                # 不变量：bought_today <= daily_limit，余额永不为负
                self.assertLessEqual(shop.purchases.get(item, 0), stock[item][1])
                self.assertGreaterEqual(money, 0)

    def test_same_batch_is_deterministic(self):
        import random

        rng = random.Random(7)
        stock = {"a": (10, 2), "b": (25, 1)}
        ops = [(rng.choice(list(stock)), rng.randint(1, 4)) for _ in range(50)]
        results = []
        for _ in range(2):
            shop = Shop(stock)
            money = 100
            trace = []
            for item, day in ops:
                try:
                    money, bought = buy(shop, item, day, money)
                    trace.append((money, bought))
                except ShopError:
                    trace.append(("error", money))
            results.append(trace)
        self.assertEqual(results[0], results[1])


class ScaleTest(unittest.TestCase):
    def test_100k_buys_under_one_second(self):
        import time

        stock = {"item%d" % i: (1, 1000) for i in range(1000)}
        shop = Shop(stock)
        money = 10 ** 9
        start = time.monotonic()
        for i in range(100000):
            money, _ = buy(shop, "item%d" % (i % 1000), 1, money)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)
        self.assertEqual(len(shop.purchases), 1000)  # 内存 O(商品数)


if __name__ == "__main__":
    unittest.main()
