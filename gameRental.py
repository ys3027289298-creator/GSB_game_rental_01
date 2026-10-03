import datetime

class GameStore:
    DAILY_RATE = 1      # 租金：每天 $1
    DEPOSIT = 10        # 每笔订单押金 $10
    RENTAL_PERIOD = 7   # 正常租期 7 天
    OVERDUE_RATE = 5    # 逾期每天加收 $5

    def __init__(self, stock={}):
        self.stock = dict(stock)   # 复制入参，门店之间不共享账本
        self.orders = {}           # (gameName, rentalTime) -> 订单记录
    
    def displayStock(self):
        print("Here is the stock {}".format(self.stock))
        return self.stock
    
    def rentGame(self, n):
        if n not in self.stock:
            print("We do not have {}.".format(n))
            return None
        
        elif self.stock[n] <= 0:
            print("We are currently sold out of {}.".format(n))
            return None

        else:
            now = datetime.datetime.now()
            print("Rental Sucess. Charge is $1 per day starting {}".format(now))
            self.stock[n] -= 1
            self.orders[(n, now)] = {
                "rentalTime": now,
                "deposit": self.DEPOSIT,
                "returned": False,
                "bill": None,
                "refund": None,
            }
            return now
    
    def returnedGame(self, request):
        rentalTime, gameName = request # tuple for time it was checked out, game name

        # 先校验，后改账：任何一步不通过都不留半份状态
        if not (rentalTime and gameName):
            print("return not valid")
            return None
        if gameName not in self.stock:
            print("return not valid")
            return None
        order = self.orders.get((gameName, rentalTime))
        if order is None or order["returned"]:
            print("return not valid")
            return None

        now = datetime.datetime.now()
        days = max(0, (now - order["rentalTime"]).days)
        overdueDays = max(0, days - self.RENTAL_PERIOD)
        bill = days * self.DAILY_RATE + overdueDays * self.OVERDUE_RATE
        refund = max(0, order["deposit"] - bill)

        order["returned"] = True
        order["bill"] = bill
        order["refund"] = refund
        self.stock[gameName] += 1
        return bill

    def deleteOrder(self, request):
        rentalTime, gameName = request
        key = (gameName, rentalTime)
        order = self.orders.get(key)
        if order is None:
            print("order not found")
            return None
        if not order["returned"]:
            self.stock[gameName] += 1 # 回滚未归还订单占用的库存
        del self.orders[key]
        return True

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
            return 0,0




