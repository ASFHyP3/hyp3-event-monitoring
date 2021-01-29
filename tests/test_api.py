from flask_api import status


def test_api(client):
    assert client.get('events').status_code == status.HTTP_200_OK