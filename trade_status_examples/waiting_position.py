data = {
    'id': 7643995,
    'version': 2,
    'account': {
        'id': 30034871,
        'type': 'binance_futures_coin',
        'name': 'COIN-M lec',
        'market': 'Binance Futures COIN-M',
        'link': '/accounts/30034871'
    },
    'pair': 'BTC_BTCUSD_PERP',
    'instant': False,
    'status': {
        'type': 'waiting_position',
        'title': 'Pending Position Opened'
    },
    'leverage': {
        'enabled': True,
        'type': 'isolated',
        'value': '1.0'
    },
    'position': {
        'type': 'sell',
        'editable': False,
        'units': {
            'value': '1.0',
            'editable': False
        },
        'price': {
            'value': '34872.6',
            'value_without_commission': '34886.6',
            'editable': False
        },
        'total': {
            'value': '0.00286758'
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
            'id': 26778648,
            'order_type': 'market',
            'editable': True,
            'units': {
                'value': None
            },
            'price': {
                'value': '31397.9',
                'type': 'last',
                'percent': None
            },
            'volume': '100.0',
            'total': None,
            'trailing': {
                'enabled': False,
                'percent': None
            },
            'status': {
                'type': 'idle',
                'title': 'Pending'
            },
            'data': {
                'cancelable': True,
                'panic_sell_available': False
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
                'value': '38375.26',
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
            'type': 'idle',
            'title': 'Pending'
        }
    },
    'note': 'btc1 short',
    'skip_enter_step': False,
    'data': {
        'editable': True,
        'current_price': {
            'bid': '34819.0',
            'ask': '34819.1',
            'last': '34819.0',
            'day_change_percent': '4.446',
            'quote_volume': '184368.57257178'
        },
        'target_price_type': 'price',
        'base_order_finished': True,
        'missing_funds_to_close': 0,
        'liquidation_price': None,
        'average_enter_price': None,
        'average_close_price': None,
        'average_enter_price_without_commission': None,
        'average_close_price_without_commission': None,
        'panic_sell_available': False,
        'add_funds_available': False,
        'force_start_available': False,
        'force_process_available': True,
        'cancel_available': True,
        'finished': False,
        'base_position_step_finished': True,
        'created_at': '2021-06-24T18:49:07.488Z',
        'updated_at': '2021-06-24T18:49:07.488Z',
        'type': 'smart_cover'
    },
    'profit': {
        'volume': None,
        'usd': None,
        'percent': 0,
        'roe': '0.0'
    },
    'margin': {
        'amount': '0.0',
        'total': '0.0'
    },
    'is_position_not_filled': False
}
