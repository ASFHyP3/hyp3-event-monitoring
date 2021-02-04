import json
from os import environ
from uuid import uuid4

import responses
from dateutil import parser
from hyp3_sdk.util import AUTH_URL

import find_new


@responses.activate
def test_get_granules():
    mock_response = {
        'results': [
            {
                'granuleName': 'granule1',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule2',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
        ]
    }
    responses.add(responses.GET, find_new.SEARCH_URL, json.dumps(mock_response))

    event = {
        'event_id': 'foo',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00+00:00',
            'end': '2020-01-02T00:00:00+00:00',
        },
        'wkt': 'someWKT',
    }
    response = find_new.get_granules(event)

    assert response == mock_response['results']


@responses.activate
def test_get_unproccesed_granules(tables):
    mock_response = {
        'results': [
            {
                'granuleName': 'granule1',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule2',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule3',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule4',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
        ]
    }
    responses.add(responses.GET, find_new.SEARCH_URL, json.dumps(mock_response))

    event = {
        'event_id': 'event_id1',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00+00:00',
            'end': '2020-01-02T00:00:00+00:00',
        },
        'wkt': 'someWKT',
    }

    mock_products = [
        {
            'product_id': str(uuid4()),
            'event_id': 'event_id1',
            'status_code': 'PENDING',
            'granules': [
                {
                    'granule_name': 'granule1',
                    'acquisition_date': '2020-01-01T00:00:00+00:00',
                    'path': 123,
                    'frame': 456,
                    'wkt': 'someWKT',
                }
            ]
        },
        {
            'product_id': str(uuid4()),
            'event_id': 'event_id1',
            'status_code': 'RUNNING',
            'granules': [
                {
                    'granule_name': 'granule2',
                    'acquisition_date': '2020-01-01T00:00:00+00:00',
                    'path': 456,
                    'frame': 789,
                    'wkt': 'someWKT',
                },
            ]
        },
    ]
    for item in mock_products:
        tables.product_table.put_item(Item=item)

    response = find_new.get_unprocessed_granules(event)

    assert response == mock_response['results'][2:]


def test_format_granule():
    search_api_granule = {
        'granuleName': 'granule1',
        'startTime': '2020-01-01T00:00:00.000000',
        'path': 456,
        'frame': 789,
        'wkt': 'someWKT',
    }

    assert find_new.format_granule(search_api_granule) == {
        'granule_name': 'granule1',
        'acquisition_date': '2020-01-01T00:00:00+00:00',
        'path': 456,
        'frame': 789,
        'wkt': 'someWKT',
    }


def test_format_product():
    class MockJob:
        job_id = 'foo'
        job_type = 'BAR'
        status_code = 'PENDING'
        request_time = parser.parse('2020-01-01T00:00:00+00:00')

    job = MockJob()
    event = {
        'event_id': 'event_id1',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00+00:00',
            'end': '2020-01-02T00:00:00+00:00',
        },
        'wkt': 'someWKT',
    }
    granules = [
        {
            'granuleName': 'granule1',
            'startTime': '2020-01-01T00:00:00+00:00',
            'path': 123,
            'frame': 456,
            'wkt': 'someWKT',
        }
    ]
    assert find_new.format_product(job, event, granules) == {
        'product_id': 'foo',
        'event_id': 'event_id1',
        'granules': [
            {
                'granule_name': 'granule1',
                'acquisition_date': '2020-01-01T00:00:00+00:00',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            }
        ],
        'job_type': 'BAR',
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }


@responses.activate
def test_add_product_for_processing(tables):
    responses.add(responses.GET, AUTH_URL)
    event = {
        'event_id': 'event_id1',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00+00:00',
            'end': '2020-01-02T00:00:00+00:00',
        },
        'wkt': 'someWKT',
    }
    hyp3_response = {
        'jobs': [
            {
                'job_id': 'foo',
                'job_type': 'RTC_GAMMA',
                'name': event['event_id'],
                'request_time': '2020-06-04T18:00:03+00:00',
                'user_id': 'some_user',
                'status_code': 'PENDING',
            }
        ],
    }
    responses.add(responses.POST, environ['HYP3_URL'] + '/jobs', json.dumps(hyp3_response))
    granule = {
        'granuleName': 'granule1',
        'startTime': '2020-01-01T00:00:00+00:00',
        'path': 123,
        'frame': 456,
        'wkt': 'someWKT',
    }
    find_new.add_product_for_processing(granule, event, find_new.get_processes()[0])

    products = tables.product_table.scan()['Items']
    assert len(products) == 1
    assert products[0]['processing_date'] == '2020-06-04T18:00:03+00:00'
    assert products[0]['status_code'] == 'PENDING'


@responses.activate
def test_lambda_handler(tables):
    mock_events = [
        {
            'event_id': 'event_id1',
            'processing_timeframe': {
                'start': '2020-01-01T00:00:00+00:00',
                'end': '2020-01-02T00:00:00+00:00'
            },
            'wkt': 'foo'
        },
    ]
    for item in mock_events:
        tables.event_table.put_item(Item=item)

    mock_response = {
        'results': [
            {
                'granuleName': 'granule1',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule2',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule3',
                'startTime': '2020-01-01T00:00:00+00:00',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            }
        ]
    }
    responses.add(responses.GET, find_new.SEARCH_URL, json.dumps(mock_response))

    mock_products = [
        {
            'product_id': str(uuid4()),
            'event_id': 'event_id1',
            'status_code': 'PENDING',
            'granules': [
                {
                    'granule_name': 'granule1',
                    'acquisition_date': '2020-01-01T00:00:00+00:00',
                    'path': 123,
                    'frame': 456,
                    'wkt': 'someWKT',
                }
            ]
        },
        {
            'product_id': str(uuid4()),
            'event_id': 'event_id1',
            'status_code': 'RUNNING',
            'granules': [
                {
                    'granule_name': 'granule2',
                    'acquisition_date': '2020-01-01T00:00:00+00:00',
                    'path': 456,
                    'frame': 789,
                    'wkt': 'someWKT',
                },
            ]
        },
    ]
    for item in mock_products:
        tables.product_table.put_item(Item=item)
    responses.add(responses.GET, AUTH_URL)

    hyp3_response = {
        'jobs': [
            {
                'job_id': 'foo',
                'job_type': 'RTC_GAMMA',
                'name': 'event_id1',
                'request_time': '2020-06-04T18:00:03+00:00',
                'user_id': 'some_user',
                'status_code': 'PENDING',
            }
        ],
    }
    responses.add(responses.POST, environ['HYP3_URL'] + '/jobs', json.dumps(hyp3_response))

    find_new.lambda_handler(None, None)

    products = tables.product_table.scan()['Items']

    assert len(products) == 3
    assert [product['granules'][0]['granule_name'] for product in products] == ['granule1', 'granule2', 'granule3']
