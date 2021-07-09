import pytest
import os
from unittest.mock import patch
import json
from main import app
from freezegun import freeze_time

import alphabot.helpers as h
import test.helpers as th


waiting_for_base_call_count = 0


@pytest.fixture
def mock_main_py3c():
    with patch('main.Py3CW') as mock_main_py3c:
        mock_main_py3c().request.side_effect = mock_py3c_request_side_effect
        yield mock_main_py3c


def mock_py3c_request_side_effect(entity, action, payload=None, action_id=None):
    global waiting_for_base_call_count
    with open("test/test_files/BTC_L4_open_long_base_trade_response.json") as _f:
        mock_base_trade_data = json.load(_f)
    with open("test/test_files/BTC_L4_open_long_waiting_for_base.json") as _f:
        mock_waiting_for_base_data = json.load(_f)

    if entity == "smart_trades_v2" and action == "new":
        return {}, mock_base_trade_data
    if entity == "smart_trades_v2" and action == "get_by_id" and action_id == '7873502':
        if waiting_for_base_call_count == 0:
            # initial call, still waiting for base open
            waiting_for_base_call_count += 1
            return {}, mock_waiting_for_base_data


@pytest.fixture
def mock_trade_checkup_py3c():
    with patch('alphabot.trade_checkup.Py3CW') as mock_trade_checkup_py3c:
        yield mock_trade_checkup_py3c


@pytest.fixture
def mock_print():
    with patch('builtins.print') as mock_print:
        yield mock_print


@pytest.fixture
def client():
    # use test db
    os.environ["MONGO_DB"] = "TEST"

    # keep times consistent
    freezer = freeze_time("2021-07-08 14:45")
    freezer.start()
    with app.test_client() as client:
        yield client
    freezer.stop()


def test_get(client, mock_print):
    rv = client.get('/')
    assert b'Crypto Bros reporting for duty! None yet died of natural causes!' in rv.data


def test_report(client, mock_print):
    th.reset_test_coll()

    rv = client.post('/', json=dict(
        route="report"
    ))
    for _call in th.get_expected_calls(th.EXPECTED_REPORT_CALL_STRS):
        assert _call in mock_print.mock_calls


def test_config_update_of_description(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = "BTC_L4"
    new_description = '20m Split TPs'  # was 15m Split TPs
    rv = client.post('/', json=dict(
        route='config_update',
        user='latham',
        strat=strat,
        config={
            'description': new_description,
            'tp_pct': '10',
            'tp_trail': None,
            'sl_pct': '10',
            'leverage': '1',
            'units': '2',
            'reset_tsl': False,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    # check that config was properly updated
    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_description_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_tp_pct(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_tp_pct = '8'  # was 10

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': "15m Split TPs",
            'tp_pct': new_tp_pct,
            'tp_trail': None,
            'sl_pct': '10',
            'leverage': '1',
            'units': '2',
            'reset_tsl': False,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_tp_pct_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_tp_pct_2(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_tp_pct_2 = '2'  # was None

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': '15m Split TPs',
            'tp_pct': 10,
            'tp_pct_2': new_tp_pct_2,
            'tp_trail': None,
            'sl_pct': 10,
            'leverage': 1,
            'units': 2,
            'reset_tsl': False,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_tp_pct_2_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_sl_pct(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_sl_pct = '5'  # was 10

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': '15m Split TPs',
            'tp_pct': 10,
            'tp_trail': None,
            'sl_pct': new_sl_pct,
            'leverage': 1,
            'units': 2,
            'reset_tsl': False,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_sl_pct_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_reset_tsl(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_reset_tsl = True  # was False

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': '15m Split TPs',
            'tp_pct': 10,
            'tp_trail': None,
            'sl_pct': 10,
            'leverage': 1,
            'units': 2,
            'reset_tsl': new_reset_tsl,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_reset_tsl_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_tsl_reset_points(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_tsl_reset_points = [["0.5", "0.0"], ["1", "-0.25"]]

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': '15m Split TPs',
            'tp_pct': 10,
            'tp_trail': None,
            'sl_pct': 10,
            'leverage': 1,
            'units': 2,
            'reset_tsl': False,
            'tsl_reset_points': new_tsl_reset_points
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_tsl_reset_points_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_leverage(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_leverage = 10

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': '15m Split TPs',
            'tp_pct': 10,
            'tp_trail': None,
            'sl_pct': 10,
            'leverage': new_leverage,
            'units': 2,
            'reset_tsl': False,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_leverage_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_config_update_of_units(client):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'
    new_units = 19

    rv = client.post('/', json=dict(
        route='config_update',
        user=user,
        strat=strat,
        config={
            'description': '15m Split TPs',
            'tp_pct': 10,
            'tp_trail': None,
            'sl_pct': 10,
            'leverage': 1,
            'units': new_units,
            'reset_tsl': False,
            'tsl_reset_points': [
                ["0.15", "-0.1"], ["0.2", "-0.15"], ["0.3", "-0.19"], ["0.4", "-0.28"], ["0.5", "-0.37"],
                ["0.6", "-0.46"], ["0.7", "-0.55"], ["0.8", "-0.63"], ["0.9", "-0.72"], ["1", "-0.8"], ["2", "-1.7"],
                ["3", "-2.6"], ["4", "-3.5"], ["5", "-4.4"], ["6", "-5.3"], ["7", "-6.2"], ["8", "-7.1"],
                ["9", "-8"]
            ]
        }
    ))

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_units_update.json") as _f:
        expected = json.load(_f)[strat]

    assert actual == expected


def test_open_long(client, mock_main_py3c):
    coll = th.reset_test_coll()

    user = 'latham'
    strat = 'BTC_L4'

    with open("test/test_files/BTC_L4_pre_open_long.json") as _f:
        pre_open_state = json.load(_f)[strat]

    coll.update_one(
        {"_id": user},
        {
            "$set": {f"{strat}": pre_open_state}
        }
    )

    rv = client.post('/', json=dict(
        user=user,
        strat=strat,
        long=True,
        price=35001
    ))

    post_state = coll.find_one({"_id": user})[strat]
    with open("test/test_files/BTC_L4_post_open_long.json") as _f:
        expected_post_open_state = json.load(_f)[strat]

    assert post_state == expected_post_open_state
