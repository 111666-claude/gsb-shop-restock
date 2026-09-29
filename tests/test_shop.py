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
