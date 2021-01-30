from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask_api import status

from api import lambda_handler


def seed_data(tables):
    events = [
        {
            'event_id': 'event1',
            'decimal_value': Decimal(1.0)
        },
        {
            'event_id': 'event2',
        },
    ]
    for event in events:
        tables.event_table.put_item(Item=event)

    now = datetime.now(tz=timezone.utc)
    products = [
        {
            'event_id': 'event2',
            'product_id': 'product1',
            'status_code': 'SUCCEEDED',
            'processing_date': now.isoformat(timespec='seconds'),
        },
        {
            'event_id': 'event2',
            'product_id': 'product2',
            'status_code': 'PENDING',
            'processing_date': now.isoformat(timespec='seconds'),
        },
        {
            'event_id': 'event2',
            'product_id': 'product3',
            'status_code': 'SUCCEEDED',
            'processing_date': (now - timedelta(days=7, seconds=-1)).isoformat(timespec='seconds'),
        },
        {
            'event_id': 'event2',
            'product_id': 'product4',
            'status_code': 'SUCCEEDED',
            'processing_date': (now - timedelta(days=7, seconds=1)).isoformat(timespec='seconds'),
        },
    ]
    for product in products:
        tables.product_table.put_item(Item=product)


def test_events(api_client, api_tables):
    response = api_client.get('/events')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json() == []

    seed_data(api_tables)

    response = api_client.get('/events')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.get_json()) == 2


def test_event_by_id(api_client, api_tables):
    response = api_client.get('/events/event1')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    seed_data(api_tables)

    response = api_client.get('/events/event1')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json()['event_id'] == 'event1'
    assert response.get_json()['products'] == []

    response = api_client.get('/events/event2')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json()['event_id'] == 'event2'
    product_ids = [p['product_id'] for p in response.get_json()['products']]
    assert sorted(product_ids) == ['product1', 'product3', 'product4']


def test_recent_products(api_client, api_tables):
    response = api_client.get('/recent_products')
    assert response.status_code == status.HTTP_200_OK
    assert response.get_json() == []

    seed_data(api_tables)

    response = api_client.get('/recent_products')
    assert response.status_code == status.HTTP_200_OK
    product_ids = [p['product_id'] for p in response.get_json()]
    assert sorted(product_ids) == ['product1', 'product3']


def test_cors(api_client):
    response = api_client.get('/')
    assert response.headers['Access-Control-Allow-Origin'] == '*'

    response = api_client.get('/', headers={'Origin': 'https://sarviews-hazards.alaska.edu'})
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
