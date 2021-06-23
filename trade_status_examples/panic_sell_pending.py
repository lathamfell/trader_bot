data = {
    'id': 7621901,
    'version': 2,
    'account': {
        'id': 29896590,
        'type': 'binance_futures_coin',
        'name': 'Binance Futures COIN-M',
        'market': 'Binance Futures COIN-M',
        'link': '/accounts/29896590'
    },
    'pair': 'ETH_ETHUSD_PERP',
    'instant': False,
    'status': {
        'type': 'panic_sell_pending',
        'title': 'Closing at Market Price'
    },
    'leverage': {
        'enabled': True,
        'type': 'isolated',
        'value': '10.0'
    },
    'position': {
        'type': 'sell',
        'editable': False,
        'units': {
            'value': '1.0',
            'editable': False
        },
        'price': {
            'value': '1987.23',
            'value_without_commission': '1988.03',
            'editable': False
        },
        'total': {
            'value': '0.00503211'
        },
        'order_type': 'market',
        'status': {
            'type': 'finished',
            'title': 'Finished'
        }
    },
    'take_profit': {
        'enabled': True,
        'steps': [{
            'id': 26697758,
            'order_type': 'market',
            'editable': True,
            'units': {
                'value': '1.0'
            },
            'price': {
                'value': '1789.0',
                'type': 'last',
                'percent': None
            },
            'volume': '100.0',
            'total': '0.00558971',
            'trailing': {
                'enabled': False,
                'percent': None
            },
            'status': {
                'type': 'to_process',
                'title': 'Pending'
            },
            'data': {
                'cancelable': True,
                'panic_sell_available': True
            },
            'position': 1
        }]
    },
    'stop_loss': {
        'enabled': True,
        'order_type': 'market',
        'editable': True,
        'price': {
            'value': None
        },
        'conditional': {
            'price': {
                'value': '2184.62',
                'type': 'last',
                'percent': None
            },
            'trailing': {
                'enabled': True,
                'percent': None
            }
        },
        'timeout': {
            'enabled': False,
            'value': None
        },
        'status': {
            'type': 'trailing_activated',
            'title': 'Trailing Activated'
        }
    },
    'note': 'eth short',
    'skip_enter_step': False,
    'data': {
        'editable': False,
        'current_price': {
            'bid': '2002.36',
            'ask': '2002.37',
            'last': '2002.66',
            'day_change_percent': '9.5',
            'quote_volume': '2485955.51293016'
        },
        'target_price_type': 'price',
        'base_order_finished': True,
        'missing_funds_to_close': 0,
        'liquidation_price': '2198.67871675',
        'average_enter_price': '1987.23',
        'average_close_price': None,
        'average_enter_price_without_commission': '1988.03',
        'average_close_price_without_commission': None,
        'panic_sell_available': False,
        'add_funds_available': False,
        'force_start_available': False,
        'force_process_available': True,
        'cancel_available': False,
        'finished': False,
        'base_position_step_finished': True,
        'created_at': '2021-06-23T11:20:20.045Z',
        'updated_at': '2021-06-23T11:20:20.045Z',
        'type': 'smart_cover'
    },
    'profit': {
        'volume': '-0.000036034408',
        'usd': '-0.072164667525280000000000611508959675717664',
        'percent': '-0.72',
        'roe': '-7.2'
    },
    'margin': {
        'amount': '1.0097314353',
        'total': '0.00050811'
    },
    'is_position_not_filled': False
}
