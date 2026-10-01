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


if __name__ == '__main__':
    unittest.main()