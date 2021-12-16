import pytest
import os
from unittest.mock import patch, call
import json
from main import app
from freezegun import freeze_time

import alphabot.helpers as h
import test.helpers as th
from test.helpers import MOCK_USER_ATTR

waiting_for_base_open_long_call_count = 0
waiting_for_base_open_short_call_count = 0
waiting_for_close_long_call_count = 0
waiting_for_close_short_call_count = 0
waiting_for_trade_checkup_call_count = 0


@pytest.fixture
def mock_main_py3c_open_long():
    with patch("main.Py3CW") as mock_main_py3c_open_long:
        mock_main_py3c_open_long().request.side_effect = (
            mock_py3c_request_side_effect_open_long
        )
        yield mock_main_py3c_open_long


@pytest.fixture
def mock_open_long_with_leverage():
    with patch("main.Py3CW") as mock_main_py3c_open_long_with_leverage:
        mock_main_py3c_open_long_with_leverage().request.side_effect = (
            mock_py3c_request_side_effect_open_long_with_leverage
        )
        yield mock_main_py3c_open_long_with_leverage


@pytest.fixture
def mock_main_py3c_open_short():
    with patch("main.Py3CW") as mock_main_py3c_open_short:
        mock_main_py3c_open_short().request.side_effect = (
            mock_py3c_request_side_effect_open_short
        )
        yield mock_main_py3c_open_short


@pytest.fixture
def mock_main_py3c_close_long():
    with patch("main.Py3CW") as mock_main_py3c_close_long:
        mock_main_py3c_close_long().request.side_effect = (
            mock_py3c_request_side_effect_close_long
        )
        yield mock_main_py3c_close_long


@pytest.fixture
def mock_main_py3c_close_short():
    with patch("main.Py3CW") as mock_main_py3c_close_short:
        mock_main_py3c_close_short().request.side_effect = (
            mock_py3c_request_side_effect_close_short
        )
        yield mock_main_py3c_close_short


@pytest.fixture
def mock_tc_py3c():
    with patch("alphabot.trade_checkup.Py3CW") as mock_trade_checkup_py3c:
        mock_trade_checkup_py3c().request.side_effect = (
            mock_py3c_request_side_effect_trade_checkup
        )
        yield mock_trade_checkup_py3c


@pytest.fixture
def mock_main_py3c_partial_close_long():
    with patch("main.Py3CW") as mock_main_py3c:
        mock_main_py3c().request.side_effect = (
            mock_py3c_request_side_effect_partial_close_long
        )
        yield mock_main_py3c


def mock_py3c_request_side_effect_open_long(
    entity, action, payload=None, action_id=None
):
    global waiting_for_base_open_long_call_count
    expected_base_payload = {
        "account_id": 30491505,
        "note": "latham BTC_L4 <15m Split TPs> HTF long",
        "pair": "BTC_BTCUSD_PERP",
        "leverage": {"enabled": True, "type": "isolated", "value": 1},
        "position": {"type": "buy", "units": {"value": 2}, "order_type": "market"},
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }
    expected_update_payload = {
        "id": "7873502",
        "position": {"type": "buy", "units": {"value": 2}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": 36076.26, "type": "last"},
                    "volume": 100,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": 29516.94, "type": "last"},
                "trailing": {"enabled": False, "percent": 10},
            },
        },
    }

    if (
        entity == "smart_trades_v2"
        and action == "new"
        and payload == expected_base_payload
    ):
        with open(
            "test/test_files/BTC_L4_open_long_base_trade_initial_response.json"
        ) as _f:
            mock_base_trade_initial_response = json.load(_f)
        return {}, mock_base_trade_initial_response
    if entity == "smart_trades_v2" and action == "get_by_id" and action_id == "7873502":
        if waiting_for_base_open_long_call_count == 0:
            # initial call, still waiting for base open
            waiting_for_base_open_long_call_count += 1
            with open(
                "test/test_files/BTC_L4_open_long_first_base_waiting_response.json"
            ) as _f:
                mock_first_base_waiting_response = json.load(_f)
            return {}, mock_first_base_waiting_response
        if waiting_for_base_open_long_call_count == 1:
            # second call, send status indicating base open is complete
            with open(
                "test/test_files/BTC_L4_open_long_base_complete_response.json"
            ) as _f:
                mock_base_complete_response = json.load(_f)
            return {}, mock_base_complete_response
    if (
        entity == "smart_trades_v2"
        and action == "update"
        and action_id == "7873502"
        and payload == expected_update_payload
    ):
        with open("test/test_files/BTC_L4_open_long_update_trade_response.json") as _f:
            mock_update_complete_response = json.load(_f)
        return {}, mock_update_complete_response

    raise Exception("side effect called but no conditions were fulfilled")


def mock_py3c_request_side_effect_open_long_with_leverage(
    entity, action, payload=None, action_id=None
):
    global waiting_for_base_open_long_call_count
    expected_base_payload = {
        "account_id": 30391847,
        "note": "latham BTC_L2 <1m Split TP> HTF long",
        "pair": "BTC_BTCUSD_PERP",
        "leverage": {"enabled": True, "type": "isolated", "value": 5},
        "position": {"type": "buy", "units": {"value": 2}, "order_type": "market"},
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }
    expected_update_payload = {
        "id": "6762491",
        "position": {"type": "buy", "units": {"value": 2}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": 32845.7949, "type": "last"},
                    "volume": 50,
                },
                {
                    "order_type": "market",
                    "price": {"value": 32878.591499999995, "type": "last"},
                    "volume": 50,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": 29516.94, "type": "last"},
                "trailing": {"enabled": True, "percent": 10},
            },
        },
    }

    if (
        entity == "smart_trades_v2"
        and action == "new"
        and payload == expected_base_payload
    ):
        with open(
            "test/test_files/BTC_L2_open_long_base_trade_initial_response.json"
        ) as _f:
            mock_base_trade_initial_response = json.load(_f)
        return {}, mock_base_trade_initial_response
    if entity == "smart_trades_v2" and action == "get_by_id" and action_id == "6762491":
        if waiting_for_base_open_long_call_count == 0:
            # initial call, still waiting for base open
            waiting_for_base_open_long_call_count += 1
            with open(
                "test/test_files/BTC_L2_open_long_first_base_waiting_response.json"
            ) as _f:
                mock_first_base_waiting_response = json.load(_f)
            return {}, mock_first_base_waiting_response
        if waiting_for_base_open_long_call_count == 1:
            # second call, send status indicating base open is complete
            with open(
                "test/test_files/BTC_L2_open_long_base_complete_response.json"
            ) as _f:
                mock_base_complete_response = json.load(_f)
            return {}, mock_base_complete_response
    if (
        entity == "smart_trades_v2"
        and action == "update"
        and action_id == "6762491"
        and payload == expected_update_payload
    ):
        with open("test/test_files/BTC_L2_open_long_update_trade_response.json") as _f:
            mock_update_complete_response = json.load(_f)
        return {}, mock_update_complete_response

    raise Exception("side effect called but no conditions were fulfilled")


def mock_py3c_request_side_effect_open_short(
    entity, action, payload=None, action_id=None
):
    global waiting_for_base_open_short_call_count
    expected_base_payload = {
        "account_id": 30491505,
        "note": "latham BTC_L4 <15m Split TPs> HTF short",
        "pair": "BTC_BTCUSD_PERP",
        "leverage": {"enabled": True, "type": "isolated", "value": 1},
        "position": {"type": "sell", "units": {"value": 2}, "order_type": "market"},
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }
    expected_update_payload = {
        "id": "7876280",
        "position": {"type": "sell", "units": {"value": 2}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": 29706.120000000003, "type": "last"},
                    "volume": 100,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": 36307.48, "type": "last"},
                "trailing": {"enabled": False, "percent": 10},
            },
        },
    }

    if (
        entity == "smart_trades_v2"
        and action == "new"
        and payload == expected_base_payload
    ):
        with open(
            "test/test_files/BTC_L4_open_short_base_trade_initial_response.json"
        ) as _f:
            mock_base_trade_initial_response = json.load(_f)
        return {}, mock_base_trade_initial_response
    if entity == "smart_trades_v2" and action == "get_by_id" and action_id == "7876280":
        if waiting_for_base_open_short_call_count == 0:
            # initial call, still waiting for base open
            waiting_for_base_open_short_call_count += 1
            with open(
                "test/test_files/BTC_L4_open_short_first_base_waiting_response.json"
            ) as _f:
                mock_first_base_waiting_response = json.load(_f)
            return {}, mock_first_base_waiting_response
        if waiting_for_base_open_short_call_count == 1:
            # second call, send status indicating base open is complete
            with open(
                "test/test_files/BTC_L4_open_short_base_complete_response.json"
            ) as _f:
                mock_base_complete_response = json.load(_f)
            return {}, mock_base_complete_response
    if (
        entity == "smart_trades_v2"
        and action == "update"
        and action_id == "7876280"
        and payload == expected_update_payload
    ):
        with open("test/test_files/BTC_L4_open_short_update_trade_response.json") as _f:
            mock_update_complete_response = json.load(_f)
        return {}, mock_update_complete_response

    raise Exception("side effect called but no conditions were fulfilled")


def mock_py3c_request_side_effect_close_long(entity, action, action_id=None):
    global waiting_for_close_long_call_count
    if entity == "smart_trades_v2" and action == "get_by_id" and action_id == "7886336":
        if waiting_for_close_long_call_count == 0:
            with open("test/test_files/BTC_L4_close_long_first_status.json") as _f:
                mock_first_status_response = json.load(_f)
            waiting_for_close_long_call_count += 1
            return {}, mock_first_status_response
        if waiting_for_close_long_call_count == 1:
            with open("test/test_files/BTC_L4_close_long_waiting_response.json") as _f:
                mock_waiting_response = json.load(_f)
            waiting_for_close_long_call_count += 1
            return {}, mock_waiting_response
        if waiting_for_close_long_call_count == 2:
            with open("test/test_files/BTC_L4_close_long_successful_close.json") as _f:
                mock_successful_close_response = json.load(_f)
            return {}, mock_successful_close_response

    if (
        entity == "smart_trades_v2"
        and action == "close_by_market"
        and action_id == "7886336"
    ):
        with open("test/test_files/BTC_L4_close_long_direct_response.json") as _f:
            mock_direct_response = json.load(_f)
        return {}, mock_direct_response

    raise Exception("side effect called but no conditions were fulfilled")


def mock_py3c_request_side_effect_close_short(entity, action, action_id=None):
    global waiting_for_close_short_call_count
    if entity == "smart_trades_v2" and action == "get_by_id" and action_id == "7886809":
        if waiting_for_close_short_call_count == 0:
            with open("test/test_files/BTC_L4_close_short_first_status.json") as _f:
                mock_first_status_response = json.load(_f)
            waiting_for_close_short_call_count += 1
            return {}, mock_first_status_response
        if waiting_for_close_short_call_count == 1:
            with open("test/test_files/BTC_L4_close_short_waiting_response.json") as _f:
                mock_waiting_response = json.load(_f)
            waiting_for_close_short_call_count += 1
            return {}, mock_waiting_response
        if waiting_for_close_short_call_count == 2:
            with open("test/test_files/BTC_L4_close_short_successful_close.json") as _f:
                mock_successful_close_response = json.load(_f)
            return {}, mock_successful_close_response

    if (
        entity == "smart_trades_v2"
        and action == "close_by_market"
        and action_id == "7886809"
    ):
        with open("test/test_files/BTC_L4_close_short_direct_response.json") as _f:
            mock_direct_response = json.load(_f)
        return {}, mock_direct_response

    raise Exception("side effect called but no conditions were fulfilled")


def mock_py3c_request_side_effect_trade_checkup(entity, action, action_id=None):
    if entity == "smart_trades_v2" and action == "get_by_id":
        if action_id == "7881028":
            with open("test/test_files/trade_checkup_status_028.json") as _f:
                mock_028_response = json.load(_f)
            return {}, mock_028_response
        if action_id == "7881029":
            with open("test/test_files/trade_checkup_status_029.json") as _f:
                mock_029_response = json.load(_f)
            return {}, mock_029_response
        if action_id == "7876616":
            with open("test/test_files/trade_checkup_status_616.json") as _f:
                mock_616_response = json.load(_f)
            return {}, mock_616_response

    raise Exception("side effect called but no conditions were fulfilled")


def mock_py3c_request_side_effect_partial_close_long(entity, action, action_id):
    return


@pytest.fixture
def mock_trade_checkup_py3c():
    with patch("alphabot.trade_checkup.Py3CW") as mock_trade_checkup_py3c:
        yield mock_trade_checkup_py3c


@pytest.fixture
def mock_print():
    with patch("builtins.print") as mock_print:
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
    rv = client.get("/")
    assert (
        b"Crypto Bros reporting for duty! None yet died of natural causes!" in rv.data
    )


@patch("alphabot.report.USER_ATTR", MOCK_USER_ATTR)
def test_report(client, mock_print):
    th.reset_test_coll("baseline_test_coll_1.json")

    client.post("/", json=dict(route="report"))
    for _call in th.get_expected_calls(th.EXPECTED_REPORT_CALL_STRS):
        assert _call in mock_print.mock_calls


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_from_pre_tri_a_and_with_empty_sl_reset_points(client):
    coll = th.reset_test_coll("baseline_test_coll_3.json")  # pre triA config

    user = "latham"
    strat = "BTC_L1"
    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "Test",
                "tp_pct": [1, 0.5, 0.3],
                "tp_pct_2": [None, None, None],
                "sl_pct": [10, 5, 1],
                "dca_pct": [[2], [1], [0.5]],
                "dca_weights": [[50, 50], [33, 67], [90, 10]],
                "sl_trail": [False, True, True],
                "leverage": [5, 2, 1],
                "units": [100, 50, 20],
                "reset_sl": [True, False, False],
                "sl_reset_points": [[[]]],
            },
        ),
    )

    # check that config was properly updated
    actual = coll.find_one({"_id": user})[strat]
    with open(
        "test/test_files/expected_strat_config_after_update_from_pre_tri_a_and_with_empty_sl_reset_points.json"
    ) as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_description(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_description = "20m Split TPs"  # was 15m Split TPs
    client.post(
        "/",
        json=dict(
            route="config_update",
            user="latham",
            strat=strat,
            config={
                "description": new_description,
                "tp_pct": ["10"],
                "sl_pct": ["10"],
                "sl_trail": [False],
                "leverage": ["1"],
                "units": ["2"],
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    # check that config was properly updated
    actual = coll.find_one({"_id": user})[strat]
    with open(
        "test/test_files/expected_strat_config_after_description_update.json"
    ) as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_tp_pct_and_tp_pct_after_dca(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_tp_pct = [8, 4, 1]  # was [10]
    new_tp_pct_after_dca = [8, None, 0.5]

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": new_tp_pct,
                "tp_pct_after_dca": new_tp_pct_after_dca,
                "sl_pct": ["10"],
                "sl_trail": [False],
                "leverage": ["1"],
                "units": ["2"],
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_tp_pct_and_tp_pct_after_dca_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_tp_pct_2(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_tp_pct_2 = ["2"]  # was None

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "tp_pct_2": new_tp_pct_2,
                "sl_pct": [10],
                "sl_trail": [False],
                "leverage": [1],
                "units": [2],
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_tp_pct_2_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_sl_pct(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_sl_pct = ["5"]  # was 10

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "sl_pct": new_sl_pct,
                "sl_trail": [False],
                "leverage": [1],
                "units": [2],
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_sl_pct_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_sl_trail(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_sl_trail = [True]  # was False

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "sl_pct": [10],
                "sl_trail": new_sl_trail,
                "leverage": [1],
                "units": [2],
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]]
            }
        )
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_sl_trail_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_trail_delay(client):
    coll = th.reset_test_coll("baseline_test_coll_2.json")

    user = "malcolm"
    strat = "BTC_M1"
    new_trail_delay = [True]  # was False

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "A2A 15m",
                "tp_pct": [5],
                "sl_pct": [.5],
                "sl_trail": [True],
                "trail_delay": new_trail_delay,
                "leverage": [1],
                "units": [2],
                "reset_sl": [False],
                "sl_reset_points": [[
                    [
                      0.8,
                      0
                    ],
                    [
                      1.2,
                      -0.1
                    ],
                    [
                      2,
                      -1.1
                    ]
                ]],
            }
        )
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_trail_delay_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_reset_sl(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_reset_sl = [True]  # was False

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "sl_pct": [10],
                "sl_trail": [False],
                "leverage": [1],
                "units": [2],
                "reset_sl": new_reset_sl,
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open(
        "test/test_files/expected_strat_config_after_reset_sl_update.json"
    ) as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_sl_reset_points(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_sl_reset_points = [[["0.5", "0.0"], ["1", "-0.25"]]]

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "sl_pct": [10],
                "sl_trail": [False],
                "leverage": [1],
                "units": [2],
                "reset_sl": [False],
                "sl_reset_points": new_sl_reset_points,
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open(
        "test/test_files/expected_strat_config_after_sl_reset_points_update.json"
    ) as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_leverage(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_leverage = [10]

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "sl_pct": [10],
                "sl_trail": [False],
                "leverage": new_leverage,
                "units": [2],
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_leverage_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_units(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"
    new_units = [19]

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m Split TPs",
                "tp_pct": [10],
                "sl_pct": [10],
                "sl_trail": [False],
                "leverage": [1],
                "units": new_units,
                "reset_sl": [False],
                "sl_reset_points": [[
                    ["0.15", "-0.1"],
                    ["0.2", "-0.15"],
                    ["0.3", "-0.19"],
                    ["0.4", "-0.28"],
                    ["0.5", "-0.37"],
                    ["0.6", "-0.46"],
                    ["0.7", "-0.55"],
                    ["0.8", "-0.63"],
                    ["0.9", "-0.72"],
                    ["1", "-0.8"],
                    ["2", "-1.7"],
                    ["3", "-2.6"],
                    ["4", "-3.5"],
                    ["5", "-4.4"],
                    ["6", "-5.3"],
                    ["7", "-6.2"],
                    ["8", "-7.1"],
                    ["9", "-8"],
                ]],
            },
        ),
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_after_units_update.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("alphabot.updaters.USER_ATTR", MOCK_USER_ATTR)
def test_config_update_of_dca(client):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L6"
    new_dca = [[2, 5], [1], [0.2, 0.5]]

    client.post(
        "/",
        json=dict(
            route="config_update",
            user=user,
            strat=strat,
            config={
                "description": "15m SL",
                "tp_pct": [10],
                "sl_pct": [10],
                "dca_pct": new_dca,
                "sl_trail": [False],
                "leverage": [1],
                "units": [1],
                "reset_sl": [True],
                "sl_reset_points": [[
                    [
                      0.25,
                      -0.1
                    ],
                    [
                      0.35,
                      -0.19
                    ],
                    [
                      0.45,
                      -0.28
                    ],
                    [
                      0.55,
                      -0.37
                    ],
                    [
                      0.65,
                      -0.46
                    ],
                    [
                      0.75,
                      -0.55
                    ],
                    [
                      0.85,
                      -0.64
                    ],
                    [
                      0.95,
                      0.73
                    ],
                    [
                      1,
                      -0.75
                    ],
                    [
                      2,
                      -1.7
                    ],
                    [
                      3,
                      -2.6
                    ],
                    [
                      4,
                      -3.5
                    ],
                    [
                      5,
                      -4.4
                    ],
                    [
                      6,
                      -5.3
                    ],
                    [
                      7,
                      -6.2
                    ],
                    [
                      8,
                      -7.1
                    ],
                    [
                      9,
                      -8
                    ]
                  ]]
            }
        )
    )

    actual = coll.find_one({"_id": user})[strat]
    with open("test/test_files/expected_strat_config_update_of_dca.json") as _f:
        expected = json.load(_f)[strat]
    assert actual == expected


@patch("main.USER_ATTR", MOCK_USER_ATTR)
def test_open_long(client, mock_main_py3c_open_long):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"

    with open("test/test_files/BTC_L4_pre_open_long.json") as _f:
        pre_open_state = json.load(_f)[strat]

    coll.update_one({"_id": user}, {"$set": {f"{strat}": pre_open_state}})

    client.post("/", json=dict(user=user, strat=strat, open_long_htf=True, price=35001))

    post_state = coll.find_one({"_id": user})[strat]
    with open("test/test_files/BTC_L4_post_open_long.json") as _f:
        expected_post_open_state = json.load(_f)[strat]

    assert post_state == expected_post_open_state


@patch("main.USER_ATTR", MOCK_USER_ATTR)
def test_open_long_with_leverage(client, mock_open_long_with_leverage):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L2"

    with open("test/test_files/BTC_L2_pre_open_long.json") as _f:
        pre_open_state = json.load(_f)[strat]

    coll.update_one({"_id": user}, {"$set": {f"{strat}": pre_open_state}})

    client.post("/", json=dict(user=user, strat=strat, open_long_htf=True, price=53001))

    post_state = coll.find_one({"_id": user})[strat]
    with open("test/test_files/BTC_L2_post_open_long.json") as _f:
        expected_post_open_state = json.load(_f)[strat]

    assert post_state == expected_post_open_state


@patch("main.USER_ATTR", MOCK_USER_ATTR)
def test_open_short(client, mock_main_py3c_open_short):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"

    with open("test/test_files/BTC_L4_pre_open_short.json") as _f:
        pre_open_state = json.load(_f)[strat]

    coll.update_one({"_id": user}, {"$set": {f"{strat}": pre_open_state}})

    client.post("/", json=dict(user=user, strat=strat, open_short_htf=True, price=34002))

    post_state = coll.find_one({"_id": user})[strat]
    with open("test/test_files/BTC_L4_post_open_short.json") as _f:
        expected_post_open_state = json.load(_f)[strat]

    assert post_state == expected_post_open_state


# alpha logic doesn't use any standalone close alerts; it only closes on HTF switch
"""  
@patch("main.USER_ATTR", MOCK_USER_ATTR)
def test_close_long(client, mock_main_py3c_close_long):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"

    with open("test/test_files/BTC_L4_pre_close_long.json") as _f:
        pre_close_state = json.load(_f)[strat]

    coll.update_one({"_id": user}, {"$set": {f"{strat}": pre_close_state}})

    client.post("/", json=dict(user=user, strat=strat, close_long=True, price=36003))

    post_state = coll.find_one({"_id": user})[strat]
    with open("test/test_files/BTC_L4_post_close_long.json") as _f:
        expected_post_close_state = json.load(_f)[strat]
    assert post_state == expected_post_close_state


@patch("main.USER_ATTR", MOCK_USER_ATTR)
def test_close_short(client, mock_main_py3c_close_short):
    coll = th.reset_test_coll("baseline_test_coll_1.json")

    user = "latham"
    strat = "BTC_L4"

    with open("test/test_files/BTC_L4_pre_close_short.json") as _f:
        pre_close_state = json.load(_f)[strat]

    coll.update_one({"_id": user}, {"$set": {f"{strat}": pre_close_state}})

    client.post("/", json=dict(user=user, strat=strat, close_short=True, price=32005))

    post_state = coll.find_one({"_id": user})[strat]
    with open("test/test_files/BTC_L4_post_close_short.json") as _f:
        expected_post_close_state = json.load(_f)[strat]
    assert post_state == expected_post_close_state
"""


@patch("alphabot.trade_checkup.USER_ATTR", MOCK_USER_ATTR)
def test_trade_checkup(client, mock_tc_py3c):
    coll = th.reset_test_coll("baseline_test_coll_2.json")

    client.post("/", json=dict(route="trade_checkup"))

    # identify updates it ought to have made to the 3 open trades,
    #   update their expected json accordingly
    with open("test/test_files/expected_post_trade_checkup.json") as _f:
        expected_post_close_state = json.load(_f)
        assert coll.find_one({"_id": "latham"}) == expected_post_close_state[0]
        assert coll.find_one({"_id": "malcolm"}) == expected_post_close_state[1]


def test_limit_take_profit():
    pass


def test_limit_stop_loss():
    pass


def test_limit_entry():
    pass


def test_logic_alpha():
    pass


def test_that_actually_covers_all_of_trade_checkup_module():
    pass  # perhaps just extend the current trade checkup module test


def test_double_arrow_logic():
    pass


def try_and_test_when_omega_receives_ltf_and_htf_on_same_candle():
    pass


def test_close_long_but_no_trade_is_open(client):
    pass


def test_close_long_but_current_open_trade_is_short(client):
    pass


def test_close_long_while_another_worker_is_waiting_for_long_open(client):
    # the close long would be ignored because the trade id is not put into the strat status
    #   until the trade is confirmed open
    # so this test is essentially a dupe of test_close_long_but_no_trade_is_open
    pass


def test_partial_profit_signal_received(client, mock_main_py3c_partial_close_long):
    coll = th.reset_test_coll("baseline_test_coll_2.json")
    user = "latham"
    strat = "BTC_M3"
    client.post(
        "/",
        json=dict(user=user, strat=strat, close_long=True, partial=True, price=33333),
    )

    #assert False
