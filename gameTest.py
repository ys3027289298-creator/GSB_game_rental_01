import unittest
from unittest import mock
from datetime import datetime, timedelta

import gameRental
from gameRental import GameStore, Customer

T = datetime(2026, 1, 1, 12, 0, 0)


class FakeDateTime:
    """Replaces the gameRental datetime module; datetime.now() follows a script."""

    def __init__(self, times):
        self._times = iter(times)
        self.datetime = self

    def now(self):
        return next(self._times)


class Clock:
    def __init__(self, times):
        self._patch = mock.patch.object(gameRental, "datetime", FakeDateTime(times))

    def __enter__(self):
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        return False


class GameRentalTest(unittest.TestCase):
    stock1 = {"COD": 3, "FIFA": 1, "Smash": 2}
    stock2 = {"MHA": 3, "Fortnite": 0, "2K": 4}

    def assertLedgerBalances(self, store, initial):
        # Every deposit dollar ends up in exactly one place: held, revenue, or refunded.
        collected = store.total_revenue + store.total_refunded + store.deposits_held
        self.assertEqual(collected, store.total_deposits_collected)
        # Every held deposit belongs to exactly one open order.
        self.assertEqual(store.deposits_held,
                         store.activeOrderCount() * GameStore.DEPOSIT_AMOUNT)
        # Every game copy is either on the shelf or inside exactly one open order.
        for name, initial_count in initial.items():
            self.assertEqual(
                store.stock[name] + sum(
                    1 for order in store.orders.values() if order["game"] == name
                ),
                initial_count,
            )
        self.assertGreaterEqual(min(store.stock.values()), 0)

    def test_GameStore_diplays_correct_stock(self):
        store1 = GameStore(self.stock1)
        store2 = GameStore(self.stock2)

        self.assertDictEqual(store1.displayStock(), self.stock1)
        self.assertDictEqual(store2.displayStock(), self.stock2)

    def test_rental_not_in_stock(self):
        store1 = GameStore(dict(self.stock1))
        self.assertIsNone(store1.rentGame('NHL'))

    def test_empty_stock(self):
        store1 = GameStore(dict(self.stock2))
        self.assertIsNone(store1.rentGame("Fortnite"))

    def test_valid_rental_stock(self):
        store1 = GameStore(dict(self.stock1))
        store1.rentGame("FIFA")
        self.assertEqual(store1.stock['FIFA'], 0)

    def test_invalid_return_time(self):
        store1 = GameStore(dict(self.stock1))
        customer = Customer()

        request = customer.returnGame()  # should be (0,0)
        self.assertIsNone(store1.returnedGame(request))

        self.assertIsNone(store1.returnedGame((0, 0)))  # F F F

    def test_invalid_rental_game(self):
        store1 = GameStore(dict(self.stock1))
        customer = Customer()

        customer.rentalTime = datetime.now()
        customer.gameName = "One's Justice"

        request = customer.returnGame()
        self.assertIsNone(store1.returnedGame(request))

    def test_default_stock_does_not_alias_between_stores(self):
        store_a = GameStore()
        store_b = GameStore()
        store_a.stock["COD"] = 1
        self.assertNotIn("COD", store_b.stock)

    def test_rental_days_are_full_elapsed_days(self):
        store = GameStore({"COD": 1})
        with Clock([T, T + timedelta(days=3)]):
            key = store.rentGame("COD")
            bill = store.returnedGame(key)
        # Old code computed int(timedelta / 86400), which raised TypeError.
        self.assertEqual(bill, 3 * GameStore.DAILY_RATE)

    def test_return_within_free_window_gets_full_deposit_back_minus_rent(self):
        store = GameStore({"COD": 1})
        with Clock([T, T + timedelta(days=3)]):
            key = store.rentGame("COD")
            bill = store.returnedGame(key)
        self.assertEqual(bill, 3)
        self.assertEqual(store.total_refunded, 17)
        self.assertEqual(store.total_revenue, 3)
        self.assertEqual(store.deposits_held, 0)
        self.assertEqual(store.stock["COD"], 1)
        self.assertNotIn(key, store.orders)
        self.assertLedgerBalances(store, {"COD": 1})

    def test_same_day_return_is_free_and_fully_refunded(self):
        store = GameStore({"COD": 1})
        with Clock([T, T]):
            key = store.rentGame("COD")
            bill = store.returnedGame(key)
        self.assertEqual(bill, 0)
        self.assertEqual(store.total_refunded, 20)
        self.assertEqual(store.total_revenue, 0)
        self.assertLedgerBalances(store, {"COD": 1})

    def test_overdue_fee_charged_beyond_free_days(self):
        store = GameStore({"COD": 1})
        with Clock([T, T + timedelta(days=10)]):
            key = store.rentGame("COD")
            bill = store.returnedGame(key)
        # 10 days rent + 3 overdue days at $2
        self.assertEqual(bill, 10 + 3 * GameStore.OVERDUE_RATE)
        self.assertEqual(store.total_refunded, 4)
        self.assertEqual(store.total_revenue, 16)
        self.assertLedgerBalances(store, {"COD": 1})

    def test_overdue_beyond_deposit_is_recorded_as_debt(self):
        store = GameStore({"COD": 1})
        with Clock([T, T + timedelta(days=30)]):
            key = store.rentGame("COD")
            bill = store.returnedGame(key)
        # 30 rent + 23*2 overdue = 76, deposit covers 20, remaining 56 is debt.
        self.assertEqual(bill, 76)
        self.assertEqual(store.total_refunded, 0)
        self.assertEqual(store.total_revenue, 20)
        self.assertEqual(store.order_history[key]["debt"], 56)
        self.assertNotIn(key, store.orders)

    def test_consecutive_rent_return_cycles_keep_one_balance(self):
        store = GameStore({"COD": 3, "FIFA": 1})
        with Clock([
            T, T + timedelta(days=3),          # COD for 3 days -> 3, refund 17
            T + timedelta(days=5), T + timedelta(days=6),   # COD for 1 -> 1, refund 19
            T + timedelta(days=6), T + timedelta(days=9),   # FIFA for 3 -> 3, refund 17
        ]):
            cod_1 = store.rentGame("COD")
            self.assertEqual(store.returnedGame(cod_1), 3)
            self.assertEqual(store.stock["COD"], 3)
            cod_2 = store.rentGame("COD")
            self.assertEqual(store.returnedGame(cod_2), 1)
            fifa = store.rentGame("FIFA")
            self.assertEqual(store.returnedGame(fifa), 3)

        self.assertEqual(store.stock, {"COD": 3, "FIFA": 1})
        self.assertEqual(store.total_revenue, 7)
        self.assertEqual(store.total_refunded, 53)
        self.assertEqual(store.deposits_held, 0)
        self.assertEqual(store.activeOrderCount(), 0)
        self.assertLedgerBalances(store, {"COD": 3, "FIFA": 1})

    def test_interleaved_orders_each_get_unique_bill_and_refund(self):
        store = GameStore({"COD": 1, "FIFA": 1})
        with Clock([
            T,                                  # rent COD (A)
            T + timedelta(days=1),             # rent FIFA (B)
            T + timedelta(days=3),             # return A -> 3 days
            T + timedelta(days=4),             # re-rent COD (C)
            T + timedelta(days=10),            # return B -> 9 elapsed, 2 overdue
            T + timedelta(days=11),            # return C -> 7 elapsed, no overdue
        ]):
            order_a = store.rentGame("COD")
            order_b = store.rentGame("FIFA")
            self.assertEqual(store.stock["COD"], 0)
            self.assertEqual(store.stock["FIFA"], 0)
            self.assertEqual(store.returnedGame(order_a), 3)
            self.assertEqual(store.stock["COD"], 1)
            order_c = store.rentGame("COD")
            self.assertEqual(store.stock["COD"], 0)
            bill_b = store.returnedGame(order_b)
            bill_c = store.returnedGame(order_c)

        self.assertEqual(bill_b, 9 + 2 * GameStore.OVERDUE_RATE)   # 13
        self.assertEqual(bill_c, 7)                                 # exactly 7 free days
        self.assertNotEqual((order_a, bill_b), (order_b, bill_c))
        self.assertEqual(store.stock, {"COD": 1, "FIFA": 1})
        self.assertEqual(store.total_revenue, 3 + 13 + 7)
        self.assertEqual(store.total_refunded, 17 + 7 + 13)
        self.assertEqual(store.deposits_held, 0)
        self.assertLedgerBalances(store, {"COD": 1, "FIFA": 1})

    def test_returning_same_order_twice_does_not_double_refund(self):
        store = GameStore({"COD": 1})
        with Clock([T, T + timedelta(days=3), T + timedelta(days=40)]):
            key = store.rentGame("COD")
            self.assertEqual(store.returnedGame(key), 3)
            self.assertIsNone(store.returnedGame(key))

        self.assertEqual(store.total_refunded, 17)
        self.assertEqual(store.total_revenue, 3)
        self.assertEqual(store.stock["COD"], 1)
        self.assertEqual(store.activeOrderCount(), 0)
        self.assertLedgerBalances(store, {"COD": 1})

    def test_returning_never_rented_order_leaves_everything_untouched(self):
        store = GameStore({"COD": 3})
        fake_key = (T, "COD")
        with Clock([T - timedelta(days=1)]):
            self.assertIsNone(store.returnedGame(fake_key))
        self.assertEqual(store.stock, {"COD": 3})
        self.assertEqual(store.deposits_held, 0)
        self.assertEqual(store.total_refunded, 0)
        self.assertEqual(store.total_revenue, 0)
        self.assertEqual(store.activeOrderCount(), 0)

    def test_returning_unknown_game_is_rejected(self):
        store = GameStore({"COD": 1})
        with Clock([T]):
            key = (datetime.now(), "NHL")
        self.assertIsNone(store.returnedGame(key))
        self.assertEqual(store.stock, {"COD": 1})

    def test_sold_out_rental_never_makes_stock_negative(self):
        store = GameStore({"FIFA": 1})
        with Clock([T, T + timedelta(seconds=1)]):
            first = store.rentGame("FIFA")
            second = store.rentGame("FIFA")
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(store.stock["FIFA"], 0)
        self.assertEqual(store.activeOrderCount(), 1)
        self.assertEqual(store.deposits_held, 20)
        self.assertEqual(store.total_refunded, 0)
        self.assertLedgerBalances(store, {"FIFA": 1})

    def test_missing_game_rental_leaves_no_half_state(self):
        store = GameStore({"COD": 1})
        self.assertIsNone(store.rentGame("NHL"))
        self.assertEqual(store.stock, {"COD": 1})
        self.assertEqual(store.deposits_held, 0)
        self.assertEqual(store.activeOrderCount(), 0)

    def test_return_clock_earlier_than_rental_is_rejected(self):
        store = GameStore({"COD": 1})
        with Clock([T, T - timedelta(days=1)]):
            key = store.rentGame("COD")
            self.assertIsNone(store.returnedGame(key))
        self.assertEqual(store.stock["COD"], 0)
        self.assertEqual(store.activeOrderCount(), 1)
        self.assertEqual(store.deposits_held, 20)
        self.assertEqual(store.total_refunded, 0)
        self.assertIn(key, store.orders)
        self.assertLedgerBalances(store, {"COD": 1})


class CustomerTest(unittest.TestCase):
    def test_valid_credentials(self):
        customer = Customer()
        now = datetime.now()
        customer.rentalTime = now
        customer.gameName = "FIFA"
        self.assertEqual(customer.returnGame(), (now, "FIFA"))

    def test_invalid_credentials(self):
        customer = Customer()
        self.assertEqual(customer.returnGame(), (0, 0))


if __name__ == '__main__':
    unittest.main()
