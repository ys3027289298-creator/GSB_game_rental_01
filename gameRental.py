import datetime


class GameStore:
    DAILY_RATE = 1
    OVERDUE_RATE = 2
    DEPOSIT_AMOUNT = 20
    FREE_DAYS = 7

    def __init__(self, stock={}):
        # Copy the input so the mutable default argument (and any caller dict)
        # can never be shared between stores.
        self.stock = dict(stock)
        # Open orders: (rental_time, game_name) -> order ledger entry.
        self.orders = {}
        # Settled orders are archived so refunds/debts stay traceable and the
        # same order can never be returned a second time.
        self.order_history = {}
        self.total_deposits_collected = 0
        self.deposits_held = 0
        self.total_revenue = 0
        self.total_refunded = 0

    def displayStock(self):
        print("Here is the stock {}".format(self.stock))
        return self.stock

    def activeOrderCount(self):
        return len(self.orders)

    def getOrder(self, key):
        return self.orders.get(key)

    def rentGame(self, n):
        # All validation happens before any state change, so a failed rental
        # never leaves a partial order, a missing deposit, or a negative stock.
        if n not in self.stock:
            print("We do not have {}.".format(n))
            return None

        if self.stock[n] <= 0:
            print("We are currently sold out of {}.".format(n))
            return None

        now = datetime.datetime.now()
        key = (now, n)
        while key in self.orders or key in self.order_history:
            now = datetime.datetime.now()
            key = (now, n)

        # Validation passed: stock, order book, and deposit move together.
        self.stock[n] -= 1
        self.orders[key] = {
            "game": n,
            "rental_time": now,
            "deposit": self.DEPOSIT_AMOUNT,
            "debt": 0,
        }
        self.total_deposits_collected += self.DEPOSIT_AMOUNT
        self.deposits_held += self.DEPOSIT_AMOUNT

        print("Rental Success. Charge is ${} per day starting {} "
              "(deposit ${} collected)".format(
                  self.DAILY_RATE, now, self.DEPOSIT_AMOUNT))
        return key

    def returnedGame(self, request):
        rentalTime, gameName = request  # tuple for time it was checked out, game name

        if not rentalTime or not gameName:  # both are valid
            print("return not valid")
            return None

        if gameName not in self.stock:
            print("return not valid")
            return None

        key = (rentalTime, gameName)
        order = self.orders.get(key)
        # Rejects returns for games that were never rented and duplicate
        # returns of an order that has already been settled.
        if order is None:
            print("no open rental for {} at {}".format(gameName, rentalTime))
            return None

        elapsed = datetime.datetime.now() - rentalTime
        if elapsed.total_seconds() < 0:
            print("return not valid")
            return None

        days = elapsed.days
        overdue_days = max(0, days - self.FREE_DAYS)
        bill = days * self.DAILY_RATE + overdue_days * self.OVERDUE_RATE
        refund = max(0, self.DEPOSIT_AMOUNT - bill)
        debt = max(0, bill - self.DEPOSIT_AMOUNT)

        # Validation passed: stock, order book, deposit, refund, revenue and
        # debt settle in one synchronous step.
        self.stock[gameName] += 1
        order["bill"] = bill
        order["refund"] = refund
        order["debt"] = debt
        order["returned_at"] = rentalTime + elapsed
        self.order_history[key] = order
        del self.orders[key]
        self.deposits_held -= self.DEPOSIT_AMOUNT
        self.total_refunded += refund
        self.total_revenue += min(bill, self.DEPOSIT_AMOUNT)

        print("Return of {} accepted. Bill is ${}, deposit refund ${}".format(
            gameName, bill, refund))
        return bill


class Customer:
    def __init__(self):
        self.rentalTime = 0
        self.gameName = ""
        self.bill = 0

    def requestRental(self):
        self.gameName = input("which game would you like to rent?")
        return self.gameName

    def returnGame(self):
        if self.gameName and self.rentalTime:
            return self.rentalTime, self.gameName
        else:
            return 0, 0
