import unittest
import logging
import datetime as dt
from blotter import Blotter, Fill, DIRECTIONS

logger = logging.getLogger("blotter.log")

def initialize_from_csvstr(string):
    '''
    Example:
        1,ZCN19,3.7025,1
        2,ZCN19,3.705,-1
    '''
    fills = list(map(lambda x: 
                Fill.create_from_attrs(*x.split(',')), 
                string.strip('\n').split('\n')
            ))
    for f in fills:
        print(f)
    print('=='*36)
    blotter = Blotter(fills[0].ExchangeTicker)
    blotter.initialize_from_list(fills)
    return blotter


class TestBlotter(unittest.TestCase):
    def annotate(f):
        def wrap(*args, **kwargs):
            print(f'{f.__name__.upper()}')
            print('=='*36)
            f(*args, **kwargs)
        return wrap

    @annotate
    def test_single_buy_positive_pnl(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,-1'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    @annotate
    def test_single_buy_negative_pnl(self):
        f = '1,ZCN19,3.705,1 \n\
2,ZCN19,3.7025,-1'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == -12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    @annotate
    def test_single_sell_positive_pnl(self):
        f = '1,ZCN19,3.705,-1 \n\
2,ZCN19,3.7025,1'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    @annotate
    def test_single_sell_negative_pnl(self):
        f = '1,ZCN19,3.7025,-1 \n\
2,ZCN19,3.705,1'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == -12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    @annotate
    def test_net_direction_zero_open_positions_zero_pnl(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,-1 \n\
4,ZCN19,3.7025,1 \n\
5,ZCN19,3.705,-1 \n\
6,ZCN19,3.7025,-1 \n\
7,ZCN19,3.705,1 \n\
8,ZCN19,3.7025,-1 \n\
9,ZCN19,3.705,1'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == 0)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    @annotate
    def test_direction_change_fromlong(self):
        f = '1,ZCN19,3.7025,1 \n\
4,ZCN19,3.705,-2'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == -1)
        assert(manager.net_direction == DIRECTIONS.SHORT)

    @annotate
    def test_direction_change_fromshort(self):
        f = '1,ZCN19,3.705,-1 \n\
4,ZCN19,3.7025,2'
        manager = initialize_from_csvstr(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 1)
        assert(manager.net_direction == DIRECTIONS.LONG)

    @annotate
    def test_direction_change_extended(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.7025,-2 \n\
3,ZCN19,3.7125,3 \n\
4,ZCN19,3.7025,-4 \n\
5,ZCN19,3.7075,5'
        manager = initialize_from_csvstr(f)
        pnl = 0 - 50 - 50*2 - 25*2
        assert(round(manager.total_pnl, 2) == pnl)
        assert(manager.net_position == 3)
        assert(manager.net_direction == DIRECTIONS.LONG)

    @annotate
    def test_fifo_open_position_longs(self):
        f = '1,ZCN19,3.7025,5 \n\
2,ZCN19,3.705,-1 \n\
4,ZCN19,3.7025,1 \n\
5,ZCN19,3.705,-2 \n\
6,ZCN19,3.7025,1 \n\
7,ZCN19,3.705,3 \n\
8,ZCN19,3.7025,-2 \n\
9,ZCN19,3.705,1'
        manager = initialize_from_csvstr(f)
        pnl = 12.5 + 25 + 0
        opens = manager.get_open_positions()
        print(opens)
        assert(round(manager.total_pnl, 2) == pnl)
        assert([4, 6, 7, 9] == list(map(lambda x: int(x.OrderID), opens)))
        assert(manager.net_position == 6)
        assert(manager.net_direction == DIRECTIONS.LONG)

    @annotate
    def test_fifo_open_positions_shorts(self):
        f = '1,ZCN19,3.7025,-5 \n\
2,ZCN19,3.705,1 \n\
4,ZCN19,3.7025,-1 \n\
5,ZCN19,3.705,2 \n\
6,ZCN19,3.7025,-1 \n\
7,ZCN19,3.705,-3 \n\
8,ZCN19,3.7025,2 \n\
9,ZCN19,3.705,-1'
        manager = initialize_from_csvstr(f)
        pnl = -12.5 - 25 + 0
        opens = manager.get_open_positions()
        print(opens)
        assert(round(manager.total_pnl, 2) == pnl)
        assert([4, 6, 7, 9] == list(map(lambda x: int(x.OrderID), opens)))
        assert(manager.net_position == -6)
        assert(manager.net_direction == DIRECTIONS.SHORT)

    @annotate
    def test_fifo_pnl_extended(self):
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
        manager = initialize_from_csvstr(f)
        pnl = 37.5 + 25 + 12.5 + 0 - \
              12.5 - 25 + 12.5 + 25 + 25 + \
              0 + 12.5 + 25 + 25 + 0 - 12.5 + 125
        assert(round(manager.total_pnl, 2) == pnl)
        assert(manager.net_position == -9)
        assert(manager.net_direction == DIRECTIONS.SHORT)

    @annotate
    def test_new_error(self):
        f = '1,ZCN19,4.005,1 \n\
4,ZCN19,4.0025,-2 \n\
5,ZCN19,4.005,-2 \n\
6,ZCN19,4.0075,2 \n\
8,ZCN19,4.0025,1'
        manager = initialize_from_csvstr(f)
        pnl = -12.5 - 25 - 12.5 + 12.5
        assert(round(manager.total_pnl, 2) == pnl)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)

    @annotate
    def test_new_error_inverse(self):
        f = '1,ZCN19,4.005,-1 \n\
4,ZCN19,4.0025,2 \n\
5,ZCN19,4.005,2 \n\
6,ZCN19,4.0075,-2 \n\
8,ZCN19,4.0025,-1'
        manager = initialize_from_csvstr(f)
        #assert(round(manager.total_pnl, 2) == pnl)
        #assert(manager.net_position == -9)
        #assert(manager.net_direction == DIRECTIONS.SHORT)

