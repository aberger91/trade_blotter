import os
import datetime as dt
import enum

from fill import Fill
from directions import DIRECTIONS


class Blotter:
    def __init__(self, 
                 ticker, 
                 contract_multiplier=1, 
                 tick_value=12.5, 
                 tick_size=0.0025
                 ):
        self.ticker = ticker
        self.net_position = 0
        self.avg_open_price = 0
        self.realized_pnl = 0
        self.unrealized_pnl = 0
        self.total_pnl = 0
        #
        self.trades = []
        self.positions = []
        #self.add_fill(trade)
        #
        self.contract_multiplier = contract_multiplier
        self.tick_value = tick_value
        self.tick_size = tick_size
        print(self.headers)
        print(self)

    @property
    def headers(self):
        return '>EVENT|SIDE|QTY|TICKER|PX|PNL|MISC|'

    def __repr__(self):
        if self.avg_open_price:
            avg_open_price = round(self.avg_open_price, 6)
        else:
            avg_open_price = 'None'
        return f'>{self.__class__.__name__.upper()}|' + \
               f'{self.net_direction.name}|'+ \
               f'{abs(self.net_position)}|' + \
               f'{self.ticker}|' + \
               f'{avg_open_price}|' + \
               f'{round(self.total_pnl, 2)}|' + \
               f'|'

    @property
    def net_direction(self):
        if not self.net_position:
            return DIRECTIONS.FLAT
        return DIRECTIONS.LONG if self.net_position > 0 else DIRECTIONS.SHORT

    def add_fill(self, fill):
        print(f'{fill}')
        self.update(fill)
        self.trades.append(fill)
        print(self)

    def get_open_positions(self):
        return [t for t in self.trades if not t.Booked]

    def get_fifo_trade_by_direction(self, direction):
        for t in self.trades:
            if t.Direction.value == direction and not t.Booked:
                return t

    def calc_pnl(self, closing_trade, trade):
        qty = min(abs(trade.OpenQuantity), abs(closing_trade.OpenQuantity))
        if trade.Direction == DIRECTIONS.LONG:
            diff = (closing_trade.PriceLevel - trade.PriceLevel)
        else:
            diff = (trade.PriceLevel - closing_trade.PriceLevel)
        pnl = diff * qty * self.contract_multiplier / self.tick_size * self.tick_value
        return pnl


    def book_trade(self, closing_trade, trade, partial=False):
        '''
        book all (or partial) closing_trade against trade
        '''
        pnl = self.calc_pnl(closing_trade, trade)
        if partial:
            closing_trade.book_partial(pnl, trade)
            trade.book(pnl, closing_trade)
        else:
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

    def close_existing_positions(self, trade):
        '''
        remove trades from the queue using fifo method
        reduce position until trade is booked or creates new position
        '''
        closing_trade = self.get_fifo_trade_by_direction(-1*trade.Direction.value)

        if not closing_trade:
            print('asdfasdf', self.net_direction, self.net_position, trade.Direction)


        if abs(trade.OpenQuantity) < abs(closing_trade.OpenQuantity):
            remaining = trade.OpenQuantity + closing_trade.OpenQuantity
            pnl = self.book_trade(closing_trade, trade, partial=True)
            self.realized_pnl += pnl
        else: 
            remaining = trade.OpenQuantity + closing_trade.OpenQuantity
            pnl = self.book_trade(closing_trade, trade)
            self.realized_pnl += pnl

            while abs(remaining) > 0:
                closing_trade = self.get_fifo_trade_by_direction(-1*trade.Direction.value)
                if not closing_trade: 
                    break

                remaining = trade.OpenQuantity + closing_trade.OpenQuantity
                if abs(trade.OpenQuantity) < abs(closing_trade.OpenQuantity):
                    pnl = self.book_trade(trade, closing_trade, partial=True)
                    self.realized_pnl += pnl
                else:
                    pnl = self.book_trade(closing_trade, trade)
                    self.realized_pnl += pnl


    def update(self, trade):
        is_closing_trade = self.net_position and self.net_direction != trade.Direction
        change_direction = is_closing_trade and abs(self.net_position) < abs(trade.OpenQuantity)

        if is_closing_trade:
            self.close_existing_positions(trade)
                                
        elif self.net_position:
            self.avg_open_price = self.set_avg_open_price(trade)
            print(f'\t\tAdding to position {trade} px:{round(self.avg_open_price, 6)}')

        else:
            self.avg_open_price = trade.PriceLevel
            print(f'\t\tInitializing position {trade} px:{round(self.avg_open_price, 6)}')

        if change_direction:
            self.avg_open_price = trade.PriceLevel

        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        self.net_position += trade.OrderFilled

        if not self.net_position:
            self.avg_open_price = None
        return self

    def update_by_marketdata(self, last_price):
        self.unrealized_pnl = (last_price - self.avg_open_price) * self.net_position
        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        return self

    def initialize_from_list(self, fills):
        for f in fills:
            self.add_fill(f)
        return self


