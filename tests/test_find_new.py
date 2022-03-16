import json
from os import environ
from unittest.mock import patch
from uuid import uuid4

import asf_search
import pytest
import responses
from dateutil import parser
from hyp3_sdk import HyP3
from hyp3_sdk.exceptions import HyP3Error, ServerError
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
def test_get_unprocessed_granules(tables):
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
    event_id = 'event_id1'
    granules = [
        {
            'granuleName': 'granule1',
            'startTime': '2020-01-01T00:00:00+00:00',
            'path': 123,
            'frame': 456,
            'wkt': 'someWKT',
        }
    ]
    assert find_new.format_product(job, event_id, granules) == {
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
        'processing_date': '2020-01-01T00:00:00+00:00',
    }


def test_add_invalid_product_record(tables):
    granule = {
        'granuleName': 'granule1',
        'startTime': '2020-01-01T00:00:00+00:00',
        'path': 123,
        'frame': 456,
        'wkt': 'someWKT',
    }
    find_new.add_invalid_product_record('event_id1', granule, 'ExceptionMessage')

    response = tables.product_table.scan()['Items']

    assert len(response) == 1
    assert response[0]['status_code'] == 'FAILED'
    assert response[0]['granules'][0]['granule_name'] == 'granule1'
    assert response[0]['event_id'] == 'event_id1'


@responses.activate
def test_submit_jobs_for_granule(tables):
    responses.add(responses.GET, AUTH_URL)
    mock_hyp3_response = {
        'jobs': [
            {
                'job_id': '1',
                'job_type': 'RTC_GAMMA',
                'request_time': '2020-06-04T18:00:03+00:00',
                'user_id': 'some_user',
                'status_code': 'PENDING',
            },
            {
                'job_id': '2',
                'job_type': 'INSAR_GAMMA',
                'request_time': '2020-06-04T18:00:03+00:00',
                'user_id': 'some_user',
                'status_code': 'PENDING',
            },
            {
                'job_id': '3',
                'job_type': 'INSAR_GAMMA',
                'request_time': '2020-06-04T18:00:03+00:00',
                'user_id': 'some_user',
                'status_code': 'PENDING',
            },
        ],
    }
    responses.add(responses.POST, environ['HYP3_URL'] + '/jobs', json.dumps(mock_hyp3_response))

    mock_neighbors = [
        {
            'granuleName': 'neighbor1',
            'startTime': '2020-01-01T00:00:00+00:00',
            'path': 123,
            'frame': 456,
            'wkt': 'someWKT',
        },
        {
            'granuleName': 'neighbor2',
            'startTime': '2020-01-01T00:00:00+00:00',
            'path': 456,
            'frame': 789,
            'wkt': 'someWKT',
        },
    ]

    granule = {
        'granuleName': 'reference',
        'startTime': '2020-01-01T00:00:00+00:00',
        'path': 123,
        'frame': 456,
        'wkt': 'someWKT',
    }
    event_id = 'event_id1'

    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    with patch('find_new.get_neighbors', lambda x: mock_neighbors):
        find_new.submit_jobs_for_granule(hyp3, event_id, granule)

    products = tables.product_table.scan()['Items']

    assert len(products) == 3
    assert all([p['processing_date'] == '2020-06-04T18:00:03+00:00' for p in products])
    assert all([p['status_code'] == 'PENDING' for p in products])
    assert all([p['granules'][0]['granule_name'] == 'reference' for p in products])

    assert products[0]['job_type'] == 'RTC_GAMMA'

    assert products[1]['job_type'] == 'INSAR_GAMMA'
    assert products[1]['granules'][1]['granule_name'] == 'neighbor1'

    assert products[2]['job_type'] == 'INSAR_GAMMA'
    assert products[2]['granules'][1]['granule_name'] == 'neighbor2'


@responses.activate
def test_submit_jobs_for_granule_submit_error(tables):
    granule = {
        'granuleName': 'reference',
        'startTime': '2020-01-01T00:00:00+00:00',
        'path': 123,
        'frame': 456,
        'wkt': 'someWKT',
    }
    event_id = 'event_id1'

    responses.add(responses.GET, AUTH_URL)
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])

    with patch('find_new.get_neighbors', lambda x: []):
        with patch('hyp3_sdk.HyP3.submit_prepared_jobs', side_effect=HyP3Error):
            with pytest.raises(find_new.GranuleError):
                find_new.submit_jobs_for_granule(hyp3, event_id, granule)

    with patch('find_new.get_neighbors', lambda x: []):
        with patch('hyp3_sdk.HyP3.submit_prepared_jobs', side_effect=ServerError):
            find_new.submit_jobs_for_granule(hyp3, event_id, granule)
    assert tables.product_table.scan()['Items'] == []


@responses.activate
def test_submit_jobs_for_granule_neighbor_error(tables):
    granule = {
        'granuleName': 'reference',
        'startTime': '2020-01-01T00:00:00+00:00',
        'path': 123,
        'frame': 456,
        'wkt': 'someWKT',
    }
    event_id = 'event_id1'

    responses.add(responses.GET, AUTH_URL)
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])

    with patch('find_new.get_neighbors', side_effect=asf_search.ASFSearch4xxError):
        with pytest.raises(find_new.GranuleError):
            find_new.submit_jobs_for_granule(hyp3, event_id, granule)

    with patch('find_new.get_neighbors', side_effect=asf_search.ASFSearchError):
        find_new.submit_jobs_for_granule(hyp3, event_id, granule)
    assert tables.product_table.scan()['Items'] == []


@responses.activate
def test_lambda_handler(tables):
    mock_event = {
        'event_id': 'event_id1',
        'processing_timeframe': {
            'start': '2020-01-01T00:00:00+00:00',
            'end': '2020-01-02T00:00:00+00:00',
        },
        'wkt': 'foo',
    }
    tables.event_table.put_item(Item=mock_event)

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
                },
            ],
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
            ],
        },
    ]
    for mock_product in mock_products:
        tables.product_table.put_item(Item=mock_product)

    mock_search_response = {
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
        ]
    }
    responses.add(responses.GET, find_new.SEARCH_URL, json.dumps(mock_search_response))

    mock_neighbors = [
        {
            'granuleName': 'neighbor1',
            'startTime': '2020-01-01T00:00:00+00:00',
            'path': 123,
            'frame': 456,
            'wkt': 'someWKT',
        },
        {
            'granuleName': 'neighbor2',
            'startTime': '2020-01-01T00:00:00+00:00',
            'path': 456,
            'frame': 789,
            'wkt': 'someWKT',
        },
    ]

    responses.add(responses.GET, AUTH_URL)
    mock_hyp3_response = {
        'jobs': [
            {
                'job_id': 'rtc',
                'job_type': 'RTC_GAMMA',
                'request_time': '2020-06-04T18:00:03+00:00',
                'status_code': 'PENDING',
                'user_id': 'some_user',
            },
            {
                'job_id': 'insar1',
                'job_type': 'INSAR_GAMMA',
                'request_time': '2020-06-04T18:00:03+00:00',
                'status_code': 'PENDING',
                'user_id': 'some_user',
            },
            {
                'job_id': 'insar2',
                'job_type': 'INSAR_GAMMA',
                'request_time': '2020-06-04T18:00:03+00:00',
                'status_code': 'PENDING',
                'user_id': 'some_user',
            },
        ],
    }
    responses.add(responses.POST, environ['HYP3_URL'] + '/jobs', json.dumps(mock_hyp3_response))

    with patch('find_new.get_neighbors', lambda x: mock_neighbors):
        find_new.lambda_handler(None, None)

    products = tables.product_table.scan()['Items']

    assert len(products) == 5

    assert products[2]['job_type'] == 'RTC_GAMMA'
    assert products[2]['granules'][0]['granule_name'] == 'granule3'

    assert products[3]['job_type'] == 'INSAR_GAMMA'
    assert products[3]['granules'][0]['granule_name'] == 'granule3'
    assert products[3]['granules'][1]['granule_name'] == 'neighbor1'

    assert products[4]['job_type'] == 'INSAR_GAMMA'
    assert products[4]['granules'][0]['granule_name'] == 'granule3'
    assert products[4]['granules'][1]['granule_name'] == 'neighbor2'
