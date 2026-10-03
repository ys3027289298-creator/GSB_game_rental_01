import unittest
from datetime import datetime, timedelta
from gameRental import GameStore, Customer
class GameRentalTest(unittest.TestCase):
    stock1 = {"COD": 3, "FIFA": 1, "Smash": 2}
    stock2 = {"MHA": 3, "Fortnite": 0, "2K": 4}

    def test_GameStore_diplays_correct_stock(self):
        store1 = GameStore(self.stock1)
        store2 = GameStore(self.stock2)

        self.assertDictEqual(store1.displayStock(), self.stock1)
        self.assertDictEqual(store2.displayStock(), self.stock2)
    
    def test_rental_not_in_stock(self):
        store1 = GameStore(self.stock1)
        self.assertIsNone(store1.rentGame('NHL'))
    
    def test_empty_stock(self):
        store1 = GameStore(self.stock2)
        self.assertIsNone(store1.rentGame("Fortnite"))

    def test_valid_rental_stock(self):
        store1 = GameStore(self.stock1)
        store1.rentGame("FIFA")
        self.assertEqual(store1.stock['FIFA'], 0)
    
    def test_invalid_return_time(self):
        store1 = GameStore(self.stock1)
        customer = Customer()
        
        request = customer.returnGame() # should be (0,0)
        self.assertIsNone(store1.returnedGame(request))
        
        self.assertIsNone(store1.returnedGame((0,0))) # F F F
    
    def test_invalid_rental_game(self):
        store1 = GameStore(self.stock1)
        customer = Customer()

        customer.rentalTime = datetime.now()
        customer.gameName = "One's Justice"

        request = customer.returnGame()
        self.assertIsNone(store1.returnedGame(request))

class CustomerTest(unittest.TestCase):
    def test_valid_credentials(self):
        customer = Customer()
        now = datetime.now()
        customer.rentalTime = now
        customer.gameName = "FIFA"
        self.assertEqual(customer.returnGame(),(now,"FIFA"))
    
    def test_invalid_credentials(self):
        customer = Customer()
        self.assertEqual(customer.returnGame(), (0,0))


class AccountingTest(unittest.TestCase):
    """库存、订单、押金、逾期、退款五条账务边界必须同步。"""

    def setUp(self):
        self.store = GameStore({"COD": 2, "FIFA": 1})

    def rent(self, game):
        rentalTime = self.store.rentGame(game)
        self.assertIsNotNone(rentalTime)
        return rentalTime

    def ageOrder(self, game, rentalTime, days):
        """把订单的租出时间拨到过去，用于测试天数/逾期。"""
        order = self.store.orders.pop((game, rentalTime))
        aged = rentalTime - timedelta(days=days)
        order["rentalTime"] = aged
        self.store.orders[(game, aged)] = order
        return aged

    # 连续租退：每个循环后库存必须回到原值，不留半份状态
    def test_consecutive_rent_return_cycles(self):
        for _ in range(3):
            t = self.rent("FIFA")
            self.assertEqual(self.store.stock["FIFA"], 0)
            self.assertEqual(self.store.returnedGame((t, "FIFA")), 0)
            self.assertEqual(self.store.stock["FIFA"], 1)
        self.assertEqual(self.store.stock, {"COD": 2, "FIFA": 1})

    # 订单交错：三笔订单交叉归还，每笔账独立且唯一
    def test_interleaved_orders_settle_independently(self):
        t1 = self.rent("COD")
        t2 = self.rent("COD")
        t3 = self.rent("FIFA")
        self.assertEqual(self.store.stock, {"COD": 0, "FIFA": 0})

        a1 = self.ageOrder("COD", t1, 2)
        a3 = self.ageOrder("FIFA", t3, 4)

        self.assertEqual(self.store.returnedGame((a1, "COD")), 2)
        self.assertEqual(self.store.stock["COD"], 1)
        self.assertEqual(self.store.returnedGame((a3, "FIFA")), 4)
        self.assertEqual(self.store.returnedGame((t2, "COD")), 0)
        self.assertEqual(self.store.stock, {"COD": 2, "FIFA": 1})

    # 租赁天数与押金退还：租 3 天，账单 3，退款 = 押金 - 3
    def test_rental_days_and_deposit_refund(self):
        t = self.rent("FIFA")
        aged = self.ageOrder("FIFA", t, 3)
        self.assertEqual(self.store.returnedGame((aged, "FIFA")), 3)
        order = self.store.orders[("FIFA", aged)]
        self.assertEqual(order["bill"], 3)
        self.assertEqual(order["refund"], GameStore.DEPOSIT - 3)

    # 逾期费用：租 10 天，逾期 3 天，退款不为负
    def test_overdue_fee_and_refund_floor(self):
        t = self.rent("FIFA")
        aged = self.ageOrder("FIFA", t, 10)
        expected = 10 * GameStore.DAILY_RATE + 3 * GameStore.OVERDUE_RATE
        self.assertEqual(self.store.returnedGame((aged, "FIFA")), expected)
        self.assertEqual(self.store.orders[("FIFA", aged)]["refund"], 0)

    # 重复退款：同一订单第二次归还必须被拒绝且不改账
    def test_duplicate_return_does_not_refund_twice(self):
        t = self.rent("FIFA")
        aged = self.ageOrder("FIFA", t, 3)
        self.assertEqual(self.store.returnedGame((aged, "FIFA")), 3)
        order = self.store.orders[("FIFA", aged)]
        self.assertEqual(order["refund"], GameStore.DEPOSIT - 3)

        self.assertIsNone(self.store.returnedGame((aged, "FIFA")))
        self.assertEqual(self.store.stock["FIFA"], 1)
        self.assertEqual(order["refund"], GameStore.DEPOSIT - 3)

    # 同一游戏重复出租：库存耗尽后不能再租，库存不为负
    def test_stock_never_goes_negative(self):
        self.rent("FIFA")
        self.assertIsNone(self.store.rentGame("FIFA"))
        self.assertEqual(self.store.stock["FIFA"], 0)

    # 库存回滚：失败的归还（无此订单/伪造时间/空请求）不留下任何状态
    def test_failed_return_leaves_no_partial_state(self):
        t = self.rent("FIFA")
        stockBefore = dict(self.store.stock)
        ordersBefore = dict(self.store.orders)

        self.assertIsNone(self.store.returnedGame((t, "COD")))
        self.assertIsNone(self.store.returnedGame((datetime.now(), "FIFA")))
        self.assertIsNone(self.store.returnedGame((0, 0)))

        self.assertEqual(self.store.stock, stockBefore)
        self.assertEqual(self.store.orders, ordersBefore)

    # 删除订单：不存在则报错且不改账；存在则回滚库存且只回滚一次
    def test_delete_order(self):
        t = self.rent("FIFA")
        self.assertIsNone(self.store.deleteOrder((datetime.now(), "FIFA")))
        self.assertEqual(self.store.stock["FIFA"], 0)

        self.assertTrue(self.store.deleteOrder((t, "FIFA")))
        self.assertEqual(self.store.stock["FIFA"], 1)

        self.assertIsNone(self.store.deleteOrder((t, "FIFA")))
        self.assertEqual(self.store.stock["FIFA"], 1)

    # 删除已归还订单：只删记录，不再动库存
    def test_delete_returned_order_keeps_stock(self):
        t = self.rent("FIFA")
        self.store.returnedGame((t, "FIFA"))
        self.assertTrue(self.store.deleteOrder((t, "FIFA")))
        self.assertEqual(self.store.stock["FIFA"], 1)

    # 库存是各门店的独立账本，默认参数不得共享
    def test_stores_do_not_share_stock(self):
        a = GameStore()
        b = GameStore()
        a.stock["FIFA"] = 1
        self.assertNotIn("FIFA", b.stock)


if __name__ == '__main__':
    unittest.main()
