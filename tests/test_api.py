from flask_api import status

from api import lambda_handler


def test_api(client):
    response = client.get('/events')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json() == []

    response = client.get('/events/foo')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = client.get('/recent_products')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json() == []

    # TODO test /events with data

    # TODO test /events/foo with data
        # TODO event with no products
        # TODO event with products
        # TODO event with products where status_code != 'SUCCEEDED'

    # TODO test /recent_products with data
        # TODO product newer than 7 days
        # TODO product newer than 7 days where status_code != 'SUCCEEDED'
        # TODO product older than 7 days

    # TODO test DecimalEncoder?


def test_cors(client):
    response = client.get('/')
    assert response.headers['Access-Control-Allow-Origin'] == '*'
    assert 'Access-Control-Allow-Credentials' not in response.headers

    response = client.get('/', headers={'Origin': 'https://sarviews-hazards.alaska.edu'})
    assert response.headers['Access-Control-Allow-Origin'] == 'https://sarviews-hazards.alaska.edu'
    assert 'Access-Control-Allow-Credentials' not in response.headers


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
