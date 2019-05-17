import unittest
from pnl import *

class FakeFill:
    def __init__(self, orderid, ticker, pricelevel, orderfilled):
        self.OrderID = orderid
        self.ExchangeTicker = ticker
        self.PriceLevel = float(pricelevel)
        self.OrderFilled = int(orderfilled)
        self.TransactionTime = dt.datetime.now()


def execute(fill_str):
    fills = fill_str.strip('\n').split('\n')
    _init_fill = FakeFill(*fills[0].split(','))
    trade = Fill(_init_fill)

    manager = Blotter(_init_fill.ExchangeTicker, trade)
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
    return manager


class TestBlotter(unittest.TestCase):
    def test_single(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,-1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    def test_single2(self):
        f = '1,ZCN19,3.705,1 \n\
2,ZCN19,3.7025,-1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == -12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    def test_single_sell(self):
        f = '1,ZCN19,3.705,-1 \n\
2,ZCN19,3.7025,1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    def test_single_sell2(self):
        f = '1,ZCN19,3.7025,-1 \n\
2,ZCN19,3.705,1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == -12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    def test_double(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,-1 \n\
3,ZCN19,3.7025,-1 \n\
4,ZCN19,3.705,1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 0)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    def test_flat_zero_pnl(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,-1 \n\
4,ZCN19,3.7025,1 \n\
5,ZCN19,3.705,-1 \n\
6,ZCN19,3.7025,-1 \n\
7,ZCN19,3.705,1 \n\
8,ZCN19,3.7025,-1 \n\
9,ZCN19,3.705,1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 0)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    def test_direction_change(self):
        f = '1,ZCN19,3.7025,1 \n\
4,ZCN19,3.705,-2'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == -1)
        assert(manager.net_direction == DIRECTIONS.SHORT)

    def test_direction_change2(self):
        f = '1,ZCN19,3.705,-1 \n\
4,ZCN19,3.7025,2'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 1)
        assert(manager.net_direction == DIRECTIONS.LONG)

    def test_direction_change3(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.7025,-2 \n\
3,ZCN19,3.7125,3 \n\
4,ZCN19,3.7025,-4 \n\
5,ZCN19,3.7075,5'
        manager = execute(f)
        pnl = 0 - 50 - 50*2 - 25*2
        assert(round(manager.total_pnl, 2) == pnl)
        assert(manager.net_position == 3)
        assert(manager.net_direction == DIRECTIONS.LONG)

    def test_fifo_open_positions(self):
        f = '1,ZCN19,3.7025,5 \n\
2,ZCN19,3.705,-1 \n\
4,ZCN19,3.7025,1 \n\
5,ZCN19,3.705,-2 \n\
6,ZCN19,3.7025,1 \n\
7,ZCN19,3.705,3 \n\
8,ZCN19,3.7025,-2 \n\
9,ZCN19,3.705,1'
        manager = execute(f)
        pnl = 12.5 + 25 + 0
        opens = manager.get_open_positions()
        assert(round(manager.total_pnl, 2) == pnl)
        assert([4, 6, 7, 9] == list(map(lambda x: int(x.OrderID), opens)))
        assert(manager.net_position == 6)
        assert(manager.net_direction == DIRECTIONS.LONG)

    def test_fifo_open_positions2(self):
        f = '1,ZCN19,3.7025,-5 \n\
2,ZCN19,3.705,1 \n\
4,ZCN19,3.7025,-1 \n\
5,ZCN19,3.705,2 \n\
6,ZCN19,3.7025,-1 \n\
7,ZCN19,3.705,-3 \n\
8,ZCN19,3.7025,2 \n\
9,ZCN19,3.705,-1'
        manager = execute(f)
        pnl = -12.5 - 25 + 0
        opens = manager.get_open_positions()
        assert(round(manager.total_pnl, 2) == pnl)
        assert([4, 6, 7, 9] == list(map(lambda x: int(x.OrderID), opens)))
        assert(manager.net_position == -6)
        assert(manager.net_direction == DIRECTIONS.SHORT)

    def test_no_errors(self):
        f = '1,ZCN19,3.70,1 \n\
2,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,1 \n\
3,ZCN19,3.7075,1 \n\
4,ZCN19,3.71,1 \n\
5,ZCN19,3.7125,1 \n\
6,ZCN19,3.7075,-10 \n\
7,ZCN19,3.705,1 \n\
8,ZCN19,3.7025,1 \n\
9,ZCN19,3.705,3 \n\
10,ZCN19,3.7025,1 \n\
11,ZCN19,3.70,1 \n\
12,ZCN19,3.70,1 \n\
13,ZCN19,3.705,1 \n\
14,ZCN19,3.7075,1 \n\
15,ZCN19,3.7025,10 \n\
16,ZCN19,3.705,-25'
        manager = execute(f)

if __name__ == '__main__':
    unittest.main()
