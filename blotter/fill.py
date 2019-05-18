from .directions import DIRECTIONS
import datetime as dt

class _Fill:
    def __init__(self, orderid, ticker, pricelevel, orderfilled):
        self.OrderID = orderid
        self.ExchangeTicker = ticker
        self.PriceLevel = float(pricelevel)
        self.OrderFilled = float(orderfilled)
        self.TransactionTime = dt.datetime.now()

    @property
    def headers(self):
        return '|'.join([a for a in dir(self) if a[0].isupper()])


class Fill:
    def __init__(self, fill):
        self.OrderID = fill.OrderID
        self.PriceLevel = fill.PriceLevel
        self.OrderFilled = fill.OrderFilled
        self.ExchangeTicker = fill.ExchangeTicker
        self.TransactionTime = fill.TransactionTime
        #
        self.Booked = False
        self.BookedPartial = False
        self.OpenQuantity = self.OrderFilled
        self.Offsets = []
        self.UnrealPnl = 0
        self.RealPnl = 0

    @staticmethod
    def create_from_attrs(*args):
        return Fill(_Fill(*args))

    @property
    def headers(self):
        return '|'.join([a for a in dir(self) if a[0].isupper()])

    @property
    def TotalPnl(self):
        return self.UnrealPnl + self.RealPnl

    @property
    def Direction(self):
        if not self.OrderFilled:
            raise ValueError(f'Received {__class__.__name__} with 0 quantity')
        return DIRECTIONS.LONG if self.OrderFilled > 0 else DIRECTIONS.SHORT

    def __repr__(self):
        direction = 'BUY' if self.Direction.name == DIRECTIONS.LONG.name else 'SELL'
        return f'+{__class__.__name__.upper()}|' + \
                f"#{self.OrderID}|" + \
                f"{direction}|" + \
               f'{self.OpenQuantity}/{self.OrderFilled}|' + \
               f'{self.ExchangeTicker}|' + \
               f'{self.PriceLevel}|' + \
               f'{round(self.TotalPnl, 2)}|' + \
               f'{self.TransactionTime}|'
               #f"{'Booked' if self.Booked else 'Open'}|" + \

    def book_partial(self, pnl, offset):
        self.Offsets.append(offset)
        self.BookedPartial = True
        if abs(offset.OrderFilled) > abs(self.OpenQuantity):
            self.OpenQuantity = 0
        elif offset.BookedPartial:
            self.OpenQuantity += offset.OpenQuantity
        else:
            self.OpenQuantity += offset.OrderFilled
        self.RealPnl += pnl
        print(f'\t\tBOOKING_PARTIAL {self}')
        if self.OpenQuantity == 0:
            self.Booked = True
        #assert(self.OpenQuantity != 0)

    def book(self, pnl, offset):
        self.Offsets.append(offset)
        self.Booked = True
        self.BookedPartial = True
        self.OpenQuantity = 0
        self.RealPnl += pnl
        print(f'\t\tBOOKING {self}')

