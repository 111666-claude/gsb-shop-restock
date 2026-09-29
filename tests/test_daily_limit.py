import random
import time
import unittest
from datetime import date, datetime, timedelta

from shoprestock.shop import Shop, ShopError, buy, server_day


class DailyResetTest(unittest.TestCase):
    def test_limit_resets_next_day(self):
        shop = Shop({"potion": (10, 3)})
        money = 1000
        for _ in range(3):
            money, bought = buy(shop, "potion", 20260929, money)
        self.assertEqual(money, 970)
        self.assertEqual(bought, 3)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 20260929, money)
        # 新的服务器日计数清零，可以再买满 3 次。
        for expected in (1, 2, 3):
            money, bought = buy(shop, "potion", 20260930, money)
            self.assertEqual(bought, expected)
        self.assertEqual(money, 940)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 20260930, money)

    def test_refresh_at_five_am(self):
        shop = Shop({"potion": (10, 1)})
        buy(shop, "potion", datetime(2026, 9, 29, 4, 59), 100)
        with self.assertRaises(ShopError):
            buy(shop, "potion", datetime(2026, 9, 29, 4, 59, 59), 100)
        # 到 05:00 进入新的服务器日，计数清零。
        _, bought = buy(shop, "potion", datetime(2026, 9, 29, 5, 0), 100)
        self.assertEqual(bought, 1)
        with self.assertRaises(ShopError):
            buy(shop, "potion", datetime(2026, 9, 29, 23, 59), 100)
        # 次日 00:00 仍属 9 月 29 日这个限购日。
        with self.assertRaises(ShopError):
            buy(shop, "potion", datetime(2026, 9, 30, 0, 0), 100)
        _, bought = buy(shop, "potion", datetime(2026, 9, 30, 5, 0), 100)
        self.assertEqual(bought, 1)

    def test_server_day_helper(self):
        self.assertEqual(server_day(datetime(2026, 9, 29, 0, 0), 5), date(2026, 9, 28))
        self.assertEqual(server_day(datetime(2026, 9, 29, 4, 59), 5), date(2026, 9, 28))
        self.assertEqual(server_day(datetime(2026, 9, 29, 5, 0), 5), date(2026, 9, 29))
        self.assertEqual(server_day(datetime(2026, 9, 29, 23, 59), 5), date(2026, 9, 29))

    def test_refresh_hour_zero(self):
        shop = Shop({"potion": (1, 1)}, refresh_hour=0)
        buy(shop, "potion", datetime(2026, 9, 29, 23, 0), 10)
        _, bought = buy(shop, "potion", datetime(2026, 9, 30, 0, 0), 10)
        self.assertEqual(bought, 1)

    def test_each_item_has_own_counter(self):
        shop = Shop({"a": (1, 1), "b": (1, 2)})
        buy(shop, "a", 1, 10)
        buy(shop, "b", 1, 10)
        _, bought = buy(shop, "b", 1, 10)
        self.assertEqual(bought, 2)
        with self.assertRaises(ShopError):
            buy(shop, "a", 1, 10)


class MoneyTest(unittest.TestCase):
    def test_insufficient_money_rejected(self):
        shop = Shop({"potion": (10, 3)})
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 5)
        self.assertNotIn("potion", shop.purchases)

    def test_exact_money_ok(self):
        shop = Shop({"potion": (10, 3)})
        money, bought = buy(shop, "potion", 1, 10)
        self.assertEqual((money, bought), (0, 1))
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 0)
        self.assertEqual(shop.purchases["potion"], 1)
        self.assertGreaterEqual(money, 0)

    def test_failure_does_not_mutate(self):
        shop = Shop({"potion": (10, 3)})
        money, _ = buy(shop, "potion", 1, 50)
        self.assertEqual(money, 40)
        with self.assertRaises(ShopError):
            buy(shop, "ghost", 1, money)
        with self.assertRaises(ShopError):
            buy(shop, "potion", 1, 5)
        self.assertEqual(shop.purchases, {"potion": 1})
        self.assertEqual(shop.last_day, 1)


class InvariantTest(unittest.TestCase):
    def test_replayed_batch_gives_same_result(self):
        stock = {"potion": (10, 3), "sword": (50, 1)}
        sequence = [
            ("potion", 1), ("potion", 1), ("sword", 1),
            ("potion", 1), ("potion", 1),
            ("potion", 2), ("potion", 2),
            ("ghost", 2),
        ]

        def run_batch(start):
            shop = Shop(stock)
            money = start
            results = []
            for item, day in sequence:
                try:
                    money, bought = buy(shop, item, day, money)
                    results.append((True, money, bought))
                except ShopError:
                    results.append((False, money, None))
            return money, results, shop.purchases

        money_a, results_a, purchases_a = run_batch(120)
        money_b, results_b, purchases_b = run_batch(120)
        self.assertEqual(money_a, money_b)
        self.assertEqual(results_a, results_b)
        self.assertEqual(purchases_a, purchases_b)
        self.assertGreaterEqual(money_a, 0)

    def test_random_invariants(self):
        rng = random.Random(424242)
        stock = {("item%d" % i): (rng.randint(1, 20), rng.randint(0, 5))
                 for i in range(30)}
        shop = Shop(stock)
        money = 500
        for _ in range(5000):
            item = "item%d" % rng.randrange(len(stock))
            day = rng.randrange(0, 4)
            before = shop.purchases.get(item, 0)
            try:
                money, bought = buy(shop, item, day, money)
                self.assertGreaterEqual(money, 0)
                self.assertLessEqual(bought, shop.stock[item][1])
            except ShopError:
                self.assertEqual(shop.purchases.get(item, 0), before)
                self.assertGreaterEqual(money, 0)

    def test_zero_limit(self):
        shop = Shop({"locked": (1, 0)})
        with self.assertRaises(ShopError):
            buy(shop, "locked", 1, 100)
        self.assertNotIn("locked", shop.purchases)


class ReferenceModelTest(unittest.TestCase):
    """随机 200 组序列，与「按天计数 + 余额校验」参考实现逐步比对。"""

    @staticmethod
    def _execute(stock, refresh_hour, start_money, sequence):
        """被测实现：执行一批购买，记录逐步结果。"""
        shop = Shop(dict(stock), refresh_hour=refresh_hour)
        money = start_money
        outcomes = []
        for item, time_arg in sequence:
            try:
                money, bought = buy(shop, item, time_arg, money)
                outcomes.append((True, money, bought))
            except ShopError:
                outcomes.append((False, money, None))
        return money, outcomes, shop

    @staticmethod
    def _reference(stock, refresh_hour, start_money, sequence):
        """参考实现：按 (服务器日, 商品) 计数，先限购后余额校验。"""
        counts = {}
        money = start_money
        outcomes = []
        for item, time_arg in sequence:
            day_key = (server_day(time_arg, refresh_hour)
                       if isinstance(time_arg, datetime) else time_arg)
            price, limit = stock[item]
            bought = counts.get((day_key, item), 0)
            if bought < limit and money >= price:
                money -= price
                bought += 1
                counts[(day_key, item)] = bought
                outcomes.append((True, money, bought))
            else:
                outcomes.append((False, money, None))
        return money, outcomes, counts

    def test_against_reference(self):
        rng = random.Random(20260930)
        for _ in range(200):
            self._run_one_trial(rng)

    def _run_one_trial(self, rng):
        items = ["item%d" % i for i in range(rng.randint(1, 8))]
        stock = {name: (rng.randint(1, 15), rng.randint(1, 4))
                 for name in items}
        refresh_hour = rng.choice((0, 5))
        use_datetime = rng.choice((True, False))
        steps = rng.randint(20, 120)

        start_money = rng.randint(0, 80)
        int_day = rng.randrange(1, 100)
        moment = datetime(2026, 1, 1, refresh_hour, 0)
        sequence = []

        for _ in range(steps):
            item = items[rng.randrange(len(items))]
            if use_datetime:
                # 时间单调递增，并刻意踩到刷新时刻边界两侧。
                if rng.random() < 0.1:
                    moment = (moment + timedelta(days=1)).replace(
                        hour=refresh_hour, minute=rng.choice((0, 59)))
                else:
                    moment += timedelta(
                        hours=rng.randrange(0, 18),
                        minutes=rng.choice((0, 30, 59)))
                time_arg = moment
            else:
                int_day += rng.choice((0, 0, 0, 1, 1, 2))
                time_arg = int_day
            sequence.append((item, time_arg))

        ref_money, ref_outcomes, ref_counts = self._reference(
            stock, refresh_hour, start_money, sequence)
        real_money, real_outcomes, real_shop = self._execute(
            stock, refresh_hour, start_money, sequence)

        # 逐步比对：成功/拒绝、剩余余额、当天购买次数完全一致（差异为 0）。
        self.assertEqual(real_outcomes, ref_outcomes)
        self.assertEqual(real_money, ref_money)

        # last_day 必须是最后一次成功购买的服务器日；若序列末步在新的
        # 一天被拒绝，last_day 停留在之前的日子（失败无副作用）。
        success_days = [
            arg for (ok, _, _), (_, arg) in zip(real_outcomes, sequence) if ok
        ]
        if success_days:
            expected_last = success_days[-1]
            if isinstance(expected_last, datetime):
                expected_last = server_day(expected_last, refresh_hour)
            self.assertEqual(real_shop.last_day, expected_last)
        else:
            self.assertIsNone(real_shop.last_day)
        for name in items:
            self.assertEqual(
                real_shop.purchases.get(name, 0),
                ref_counts.get((real_shop.last_day, name), 0))
            self.assertLessEqual(real_shop.purchases.get(name, 0),
                                 stock[name][1])
        self.assertGreaterEqual(real_money, 0)

        # 同一批购买在新商店上重复执行，结果必须完全相同。
        replay_money, replay_outcomes, replay_shop = self._execute(
            stock, refresh_hour, start_money, sequence)
        self.assertEqual(replay_outcomes, real_outcomes)
        self.assertEqual(replay_money, real_money)
        self.assertEqual(replay_shop.purchases, real_shop.purchases)


class ScaleTest(unittest.TestCase):
    def test_throughput_and_memory(self):
        stock = {("i%04d" % i): (i % 5, 200) for i in range(1000)}
        shop = Shop(stock)
        money = 10**12
        total = 100000
        start = time.perf_counter()
        for n in range(total):
            money, _ = buy(shop, "i%04d" % (n % 1000), 1, money)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0)
        # purchases 只存当前服务器日，大小为 O(商品数)。
        self.assertEqual(len(shop.purchases), 1000)
        self.assertGreaterEqual(money, 0)


if __name__ == "__main__":
    unittest.main()
