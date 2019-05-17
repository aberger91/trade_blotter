## Python Trade Blotter

- Calculate profit & loss and open positions using FIFO method
- Example:

```python
class TestBlotter(unittest.TestCase):
    def test_single(self):
        f = '1,ZCN19,3.7025,1 \n\
2,ZCN19,3.705,-1'
        manager = execute(f)
        assert(round(manager.total_pnl, 2) == 12.5)
        assert(manager.net_position == 0)
        assert(manager.net_direction == DIRECTIONS.FLAT)
```

