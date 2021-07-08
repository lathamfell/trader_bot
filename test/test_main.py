import pytest
from unittest.mock import patch

from main import app


@pytest.fixture
def client():

    with app.test_client() as client:
        yield client


@patch('main.get_logger')
def test_get(mock_logger, client):

    rv = client.get('/')
    assert b'Crypto Bros reporting for duty! None yet died of natural causes!' in rv.data
