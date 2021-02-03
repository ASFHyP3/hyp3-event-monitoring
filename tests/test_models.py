from datetime import datetime, timezone

import pytest

from models import models


def test_get_events(tables):
    assert models.get_events() == []

    event1 = {'event_id': '1'}
    tables.event_table.put_item(Item=event1)
    assert models.get_events() == [event1]

    event2 = {'event_id': '2'}
    tables.event_table.put_item(Item=event2)
    assert models.get_events() == [event1, event2]


def test_get_event(tables):
    event1 = {'event_id': '1'}
    event2 = {'event_id': '2'}
    tables.event_table.put_item(Item=event1)
    tables.event_table.put_item(Item=event2)

    assert models.get_event('1') == event1
    assert models.get_event('2') == event2
    with pytest.raises(ValueError):
        models.get_event('foo')


def test_get_products_for_event(tables):
    products = [
        {'event_id': '1', 'product_id': '1', 'status_code': 'SUCCEEDED'},
        {'event_id': '1', 'product_id': '2', 'status_code': 'SUCCEEDED'},
        {'event_id': '1', 'product_id': '3', 'status_code': 'PENDING'},
    ]
    for product in products:
        tables.product_table.put_item(Item=product)

    assert models.get_products_for_event('foo') == []
    assert models.get_products_for_event('1') == products
    assert models.get_products_for_event('1', 'SUCCEEDED') == products[0:2]
    assert models.get_products_for_event('1', 'PENDING') == products[2:3]


def test_get_products_by_status(tables):
    products = [
        {
            'event_id': '1',
            'product_id': '1',
            'status_code': 'SUCCEEDED',
            'processing_date': '2021-01-01T00:00:00+00:00',
        },
        {
            'event_id': '1',
            'product_id': '2',
            'status_code': 'SUCCEEDED',
            'processing_date': '2021-02-01T00:00:00+00:00',
        },
        {
            'event_id': '1',
            'product_id': '3',
            'status_code': 'PENDING',
            'processing_date': '2021-01-01T00:00:00+00:00',
        },
    ]
    for product in products:
        tables.product_table.put_item(Item=product)

    assert models.get_products_by_status('foo') == []
    assert models.get_products_by_status('SUCCEEDED') == products[0:2]
    assert models.get_products_by_status('PENDING') == products[2:3]

    processed_since = datetime(year=2021, month=1, day=1, tzinfo=timezone.utc)
    assert models.get_products_by_status('SUCCEEDED', processed_since) == products[0:2]

    processed_since = datetime(year=2021, month=1, day=1, second=1, tzinfo=timezone.utc)
    assert models.get_products_by_status('SUCCEEDED', processed_since) == products[1:2]

    processed_since = datetime(year=2022, month=1, day=1, tzinfo=timezone.utc)
    assert models.get_products_by_status('SUCCEEDED', processed_since) == []


def test_put_product(tables):
    assert tables.product_table.scan()['Items'] == []

    product1 = models.Product(event_id='event1', product_id='foo')
    models.put_product(product1)
    assert tables.product_table.scan()['Items'] == [product1]

    product2 = models.Product(event_id='event2', product_id='bar')
    models.put_product(product2)
    assert tables.product_table.scan()['Items'] == [product1, product2]
