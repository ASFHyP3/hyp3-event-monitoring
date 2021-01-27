import json
from os import environ
from uuid import uuid4

from hyp3_sdk.util import AUTH_URL
import responses

import find_new


def test_get_events(tables):
    mock_events = [
        {
            'event_id': 'event1',
            'processing_timeframe': {
                'start': '2020-01-01T00:00:00Z',
                'end': '2020-01-02T00:00:00Z'
            },
            'wkt': 'foo'
        },
        {
            'event_id': 'event2',
            'processing_timeframe': {
                'start': '2020-01-01T00:00:00Z',
            },
            'wkt': 'foo'
        },
        {
            'event_id': 'event3',
            'processing_timeframe': {
                'start': '2020-01-01T00:00:00Z',
                'end': '2020-01-02T00:00:00Z'
            },
            'wkt': 'foo',
            'some_extra_parameter': 'foobar',
        }
    ]
    for item in mock_events:
        tables.event_table.put_item(Item=item)

    response = find_new.get_events()

    assert response == mock_events


def test_get_existing_products(tables):
    event_id1 = 'test1'
    event_id2 = 'test2'
    products = [
        {
            'product_id': str(uuid4()),
            'event_id': event_id1,
            'status_code': 'PENDING'
        },
        {
            'product_id': str(uuid4()),
            'event_id': event_id1,
            'status_code': 'RUNNING'
        },
        {
            'product_id': str(uuid4()),
            'event_id': event_id2,
            'status_code': 'SUCCEEDED'
        },
        {
            'product_id': str(uuid4()),
            'event_id': event_id2,
            'status_code': 'FAILED'
        },
    ]
    for item in products:
        tables.product_table.put_item(Item=item)

    res = find_new.get_existing_products(event_id1)
    assert len(res) == 2
    assert products[0] in res
    assert products[1] in res

    res = find_new.get_existing_products(event_id2)

    assert len(res) == 2
    assert products[2] in res
    assert products[3] in res


@responses.activate
def test_get_granules():
    mock_response = {
        'results': [
            {
                'granuleName': 'granule1',
                'startTime': '2020-01-01T00:00:00Z',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule2',
                'startTime': '2020-01-01T00:00:00Z',
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
            'start': '2020-01-01T00:00:00Z',
            'end': '2020-01-02T00:00:00Z',
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
                'startTime': '2020-01-01T00:00:00Z',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule2',
                'startTime': '2020-01-01T00:00:00Z',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule3',
                'startTime': '2020-01-01T00:00:00Z',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule4',
                'startTime': '2020-01-01T00:00:00Z',
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
            'start': '2020-01-01T00:00:00Z',
            'end': '2020-01-02T00:00:00Z',
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
                    'aquisition_date': '2020-01-01T00:00:00Z',
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
                    'aquisition_date': '2020-01-01T00:00:00Z',
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
        'startTime': '2020-01-01T00:00:00Z',
        'path': 456,
        'frame': 789,
        'wkt': 'someWKT',
    }

    assert find_new.format_granule(search_api_granule) == {
        'granule_name': 'granule1',
        'acquisition_date': '2020-01-01T00:00:00Z',
        'path': 456,
        'frame': 789,
        'wkt': 'someWKT',
    }


def test_format_product():
    class MockJob:
        job_id = 'foo'
        job_type = 'BAR'

    job = MockJob()
    event = {
        'event_id': 'event_id1',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00Z',
            'end': '2020-01-02T00:00:00Z',
        },
        'wkt': 'someWKT',
    }
    granules = [
        {
            'granuleName': 'granule1',
            'startTime': '2020-01-01T00:00:00Z',
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
                'acquisition_date': '2020-01-01T00:00:00Z',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            }
        ],
        'job_type': 'BAR'
    }


@responses.activate
def test_add_product_for_processing(tables):
    responses.add(responses.GET, AUTH_URL)
    event = {
        'event_id': 'event_id1',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00Z',
            'end': '2020-01-02T00:00:00Z',
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
        'startTime': '2020-01-01T00:00:00Z',
        'path': 123,
        'frame': 456,
        'wkt': 'someWKT',
    }
    find_new.add_product_for_processing(granule, event, find_new.get_processes()[0])

    products = tables.product_table.scan()['Items']
    assert len(products) == 1

@responses.activate
def test_lambda_hanlder(tables):
    mock_events = [
        {
            'event_id': 'event_id1',
            'processing_timeframe': {
                'start': '2020-01-01T00:00:00Z',
                'end': '2020-01-02T00:00:00Z'
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
                'startTime': '2020-01-01T00:00:00Z',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule2',
                'startTime': '2020-01-01T00:00:00Z',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule3',
                'startTime': '2020-01-01T00:00:00Z',
                'path': 123,
                'frame': 456,
                'wkt': 'someWKT',
            },
            {
                'granuleName': 'granule4',
                'startTime': '2020-01-01T00:00:00Z',
                'path': 456,
                'frame': 789,
                'wkt': 'someWKT',
            },
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
                    'aquisition_date': '2020-01-01T00:00:00Z',
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
                    'aquisition_date': '2020-01-01T00:00:00Z',
                    'path': 456,
                    'frame': 789,
                    'wkt': 'someWKT',
                },
            ]
        },
    ]
    for item in mock_products:
        tables.product_table.put_item(Item=item)

    hyp3_repsonses = [
        {
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
        },
        {
            'jobs': [
                {
                    'job_id': 'bar',
                    'job_type': 'RTC_GAMMA',
                    'name': 'event_id1',
                    'request_time': '2020-06-04T18:00:03+00:00',
                    'user_id': 'some_user',
                    'status_code': 'PENDING',
                }
            ],
        },
    ]
    for response in hyp3_repsonses:
        responses.add(responses.GET, AUTH_URL)
        responses.add(responses.POST, environ['HYP3_URL'] + '/jobs', json.dumps(response))

    find_new.lambda_handler(None, None)

    products = tables.product_table.scan()['Items']

    assert len(products) == 4
    assert products == {}