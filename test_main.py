import pytest
import os
from unittest.mock import patch, call
import json
from main import app

import alphabot.helpers as h
import test.helpers as th


@pytest.fixture
def mock_print():
    with patch('builtins.print') as mock_print:
        yield mock_print


@pytest.fixture
def client():
    # use test db
    os.environ["MONGO_DB"] = "TEST"

    with app.test_client() as client:
        yield client


def test_get(client, mock_print):
    rv = client.get('/')
    assert b'Crypto Bros reporting for duty! None yet died of natural causes!' in rv.data


def test_report(client, mock_print):
    # clear out test db and populate with test data
    coll = h.get_mongo_coll()
    coll.drop()
    with open('test/test_files/report_test_coll.json') as _f:
        file_data = json.load(_f)
    coll.insert_many(file_data)

    rv = client.post('/', json=dict(
        route="report"
    ))
    for _call in th.get_expected_report_calls():
        assert _call in mock_print.mock_calls






