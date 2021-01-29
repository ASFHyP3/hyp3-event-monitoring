from flask_api import status

from api import lambda_handler


def test_events(client):
    response = client.get('/events')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json() == []

    # TODO test with data


def test_event_by_id(client):
    response = client.get('/events/foo')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # TODO event with no products
    # TODO event with products
    # TODO event with products where status_code != 'SUCCEEDED'


def test_recent_products(client):
    response = client.get('/recent_products')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json() == []

    # TODO product newer than 7 days
    # TODO product newer than 7 days where status_code != 'SUCCEEDED'
    # TODO product older than 7 days

    # TODO test DecimalEncoder?


def test_cors(client):
    response = client.get('/')
    assert response.headers['Access-Control-Allow-Origin'] == '*'

    response = client.get('/', headers={'Origin': 'https://sarviews-hazards.alaska.edu'})
    assert response.headers['Access-Control-Allow-Origin'] == 'https://sarviews-hazards.alaska.edu'


def test_lambda_handler():
    event = {
        'version': '2.0',
        'rawPath': '/',
        'requestContext': {
            'http': {
                'method': 'GET',
            },
        },
        'headers': {},
    }
    response = lambda_handler(event, None)
    assert response['statusCode'] == status.HTTP_404_NOT_FOUND
    assert response['headers']['Content-Type'] == 'text/html; charset=utf-8'
    assert response['isBase64Encoded'] is False
