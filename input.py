from fill import Fill, _Fill
from blotter import Blotter
import re


def validate_float(string, default=None):
    if not string or not float(string):
        return default
    return float(string)

def consume():
    buys = ['B', 'b', 'buy', 'Buy', 'BUY']
    sells = ['S', 's', 'sell', 'Sell', 'SELL']
    actions = buys + sells
    blotters = {}
    order_id = 0
    print(f'> Side OrderFilled ExchangeTicker PriceLevel ')
    while True:
        string = input('> ') 
        tokens = re.split('\s+', string.strip('\n'))

        if not tokens:
            continue
        
        if tokens[0] in actions:
            side, quantity, ticker, price = tokens
            quantity = int(quantity)
            price = float(price)

            if side in sells:
                quantity *= -1
            f = Fill.create_from_attrs(order_id, ticker, price, quantity)

            if not blotters.get(f.ExchangeTicker):
                print(f'> New {f.ExchangeTicker} Blotter ') 
                contract_multiplier = validate_float(input('> Enter ContractMultiplier (1): '), default=1)
                tick_value = validate_float(input('> Enter TickValue (12.5): '), default=12.5)
                tick_size = validate_float(input('> Enter TickSize (0.0025): '), default=0.0025)
                blotters[f.ExchangeTicker] = Blotter(f.ExchangeTicker,
                                                     contract_multiplier=contract_multiplier,
                                                     tick_value=tick_value,
                                                     tick_size=tick_size)
            blotter = blotters.get(f.ExchangeTicker)
            blotter.add_fill(f)

        elif tokens[0] in blotters.keys():
            ticker = tokens[0]
            blotter = blotters.get(ticker)
            print(blotter)

        else:
            print('Unrecognized input.')

    

if __name__ == '__main__':
    consume()

