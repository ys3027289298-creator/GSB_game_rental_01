import datetime

class GameStore:
    def __init__(self, stock={}):
        self.stock = stock
    
    def displayStock(self):
        print("Here is the stock {}".format(self.stock))
        return self.stock
    
    def rentGame(self, n):
        if n not in self.stock:
            print("We do not have {}.".format(n))
            return None
        
        elif self.stock[n] == 0:
            print("We are currently sold out of {}.".format(n))
            return None

        else:
            now = datetime.datetime.now()
            print("Rental Sucess. Charge is $1 per day starting {}".format(now))
            self.stock[n] -= 1
            return now
    
    def returnedGame(self, request):
        rentalTime, gameName = request # tuple for time it was checked out, game name
        bill = 0

        if rentalTime and gameName: # both are valid
            if gameName in self.stock:
                now = datetime.datetime.now()
                self.stock[gameName] += 1
                days = int((now - rentalTime) / 86400)
                if days < 0:
                    bill = 0
                else:
                    bill = days * 5
                return bill
            else:
                print("return not valid")
                return None
        else:
            print("return not valid")
            return None

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





