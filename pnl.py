import os
import ifm_pyutil as imu
import datetime as dt
import enum

class DIRECTIONS(enum.Enum):
    SHORT = -1
    FLAT = 0
    LONG = 1


class Fill:
    def __init__(self, _fill):
        self.OrderID = _fill.OrderID
        self.PriceLevel = _fill.PriceLevel
        self.OrderFilled = _fill.OrderFilled
        self.TransactionTime = _fill.TransactionTime
        #
        self.Booked = False
        self.BookedPartial = False
        self.OpenQuantity = self.OrderFilled
        self.Offsets = []
        self.Pnl = 0

    @property
    def direction(self):
        if not self.OrderFilled:
            raise ValueError(f'Received {__class__.__name__} with 0 quantity')
        return DIRECTIONS.LONG if self.OrderFilled > 0 else DIRECTIONS.SHORT

    def __repr__(self):
        return f"{__class__.__name__} #{self.OrderID} {self.direction.name} {self.PriceLevel} {self.OrderFilled}/{self.OpenQuantity} {self.TransactionTime} {'Booked' if self.Booked else 'Open'}"

    def book_partial(self, pnl, offset):
        self.Offsets.append(offset)
        self.BookedPartial = True
        if abs(offset.OrderFilled) > abs(self.OpenQuantity):
            self.OpenQuantity = 0
        elif offset.BookedPartial:
            self.OpenQuantity += offset.OpenQuantity
        else:
            self.OpenQuantity += offset.OrderFilled
        self.Pnl += pnl
        print(f'BOOKING_PARTIAL {self} pnl:{round(pnl, 2)}')

    def book(self, pnl, offset):
        self.Offsets.append(offset)
        self.Booked = True
        self.BookedPartial = True
        self.OpenQuantity = 0
        self.Pnl += pnl
        print(f'BOOKING {self} pnl:{round(pnl, 2)}')


class Blotter:
    def __init__(self, ticker, trade, contract_multiplier=1, tick_value=12.5, tick_size=0.0025):
        self.ticker = ticker
        self.net_position = 0
        self.avg_open_price = 0
        self.realized_pnl = 0
        self.unrealized_pnl = 0
        self.total_pnl = 0
        #
        self.trades = []
        self.positions = []
        self.add_fill(trade)
        #
        self.contract_multiplier = contract_multiplier
        self.tick_value = tick_value
        self.tick_size = tick_size

    def __repr__(self):
        return f'{__class__.__name__} {self.net_direction.name} qty:{abs(self.net_position)} symbol:{self.ticker} {round(self.avg_open_price, 6)} real:{round(self.realized_pnl, 2)} unreal:{round(self.unrealized_pnl, 2)} total:{round(self.total_pnl, 2)}'

    @property
    def net_direction(self):
        if not self.net_position:
            return DIRECTIONS.FLAT
        return DIRECTIONS.LONG if self.net_position > 0 else DIRECTIONS.SHORT

    def add_fill(self, fill):
        self.trades.append(fill)

    def get_open_positions(self):
        return [t for t in self.trades if not t.Booked]

    def get_fifo_trade_by_direction(self, direction):
        for t in self.trades:
            if t.direction.value == direction and not t.Booked:
                return t

    def calc_pnl(self, trade, closing_trade):
        qty = min(abs(trade.OpenQuantity), abs(closing_trade.OpenQuantity))
        if trade.direction == DIRECTIONS.LONG:
            diff = (closing_trade.PriceLevel - trade.PriceLevel)
        else:
            diff = (trade.PriceLevel - closing_trade.PriceLevel)
        pnl = diff * qty * self.contract_multiplier / self.tick_size * self.tick_value
        return pnl

    def book_trade_partial(self, trade, closing_trade):
        '''
        when fill quantity is less than closing fill quantity
        partially book the closing fill then
        book the fill
        '''
        pnl = self.calc_pnl(trade, closing_trade)
        closing_trade.book_partial(pnl, trade)
        trade.book(pnl, closing_trade)
        return pnl

    def book_trade(self, trade, closing_trade):
        '''
        when fill quantity is equal to or greater than closing fill quantity
        completely book the closing fill
        partially book the fill
        '''
        pnl = self.calc_pnl(trade, closing_trade)
        closing_trade_open_qty = closing_trade.OpenQuantity
        if not trade.OpenQuantity + closing_trade_open_qty:
            trade.book(pnl, closing_trade)
        else:
            trade.book_partial(pnl, closing_trade)
        closing_trade.book(pnl, trade)
        return pnl

    def set_avg_open_price(self, trade):
        _avg_open_price = ((self.avg_open_price * self.net_position) + (trade.PriceLevel * trade.OpenQuantity)) / \
                           (self.net_position + trade.OpenQuantity)
        return _avg_open_price

    def close_position(self, trade):
        closing_trade = self.get_fifo_trade_by_direction(-1*trade.direction.value)

        if abs(trade.OpenQuantity) < abs(closing_trade.OpenQuantity):
            remaining = trade.OpenQuantity + closing_trade.OpenQuantity
            pnl = self.book_trade_partial(trade, closing_trade)
            self.realized_pnl += pnl
        else: 
            remaining = trade.OpenQuantity + closing_trade.OpenQuantity
            pnl = self.book_trade(trade, closing_trade)
            self.realized_pnl += pnl
            while abs(remaining) > 0:
                closing_trade = self.get_fifo_trade_by_direction(-1*trade.direction.value)
                if not closing_trade: # net direction change
                    break
                remaining = trade.OpenQuantity + closing_trade.OpenQuantity

                if abs(trade.OpenQuantity) < abs(closing_trade.OpenQuantity):
                    pnl = self.book_trade_partial(closing_trade, trade)
                    self.realized_pnl += pnl
                else:
                    pnl = self.book_trade(trade, closing_trade)
                    self.realized_pnl += pnl


    def update(self, trade):
        is_closing_trade = self.net_position and self.net_direction != trade.direction
        change_direction = is_closing_trade and abs(self.net_position) < abs(trade.OpenQuantity)

        if is_closing_trade:
            self.close_position(trade)
                                
        else:
            self.avg_open_price = self.set_avg_open_price(trade)
            print(f'\t\tAdding to position {trade} px:{round(self.avg_open_price, 6)}')

        if change_direction:
            self.avg_open_price = trade.PriceLevel

        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        self.net_position += trade.OrderFilled

    def update_by_marketdata(self, last_price):
        self.unrealized_pnl = (last_price - self.avg_open_price) * self.net_position
        self.total_pnl = self.realized_pnl + self.unrealized_pnl


if __name__ == '__main__':
    im_creds = ['SUSIAALFOBSQ02.FCSTONE.COM', 'IMatch', 'FOUser', 'FOtest$$$$']

    SYMBOL = 'ZCN19'
    ACCOUNT = '03001'
    #with imu.DatabaseConnection(*im_creds) as db:
    #    results = db.getDFfromQuery(
    #       f"""select OrderID, ExchangeTicker, OrderFilled, PriceLevel, TransactionTime 
    #        from Fills 
    #        where SubmittedAccountNumber='{ACCOUNT}' 
    #          and OrderStatus in ('FILLED', 'PARTIALLY_FILLED') 
    #          and ExchangeTicker='{SYMBOL}' 
    #          and OrderFilled <> 0
    #        order by transactiontime asc"""
    #    )
    #    marketdata = db.getDFfromQuery(
    #        f"""select cast(Bid as float)/100000 Bid,cast(Offer as float)/100000 Offer 
    #            from CqgTobQuotes q
    #            where Symbol like 'IZCEN9'
    #        """
    #    )
    #trades = list(map(lambda x: x[1], results.iterrows()))
    #_fill = trades[0]

    class FakeFill:
        def __init__(self, orderid, ticker, pricelevel, orderfilled):
            self.OrderID = orderid
            self.ExchangeTicker = ticker
            self.PriceLevel = float(pricelevel)
            self.OrderFilled = int(orderfilled)
            self.TransactionTime = dt.datetime.now()

    fills = open('fills.txt').read().strip('\n').split('\n')

    _fill = FakeFill(*fills[0].split(','))
    trade = Fill(_fill)

    manager = Blotter(_fill.ExchangeTicker, trade)
    print(manager)
    manager.update(trade)
    print(manager)
    print()

    for f in fills[1:]:
        _fill = Fill(FakeFill(*f.split(',')))
        manager.add_fill(_fill)
        print(f'\t{_fill}')
        manager.update(_fill)
        print(manager)
        print()

    #marketdata = list(map(lambda x: x[1], marketdata.iterrows()))
    #if manager.net_position > 0:
    #    quote = marketdata[0].Bid
    #else:
    #    quote = marketdata[0].Offer
    #manager.update_by_marketdata(quote)

