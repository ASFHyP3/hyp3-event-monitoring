import json
from os import environ
from uuid import uuid4

import responses
from hyp3_sdk.util import AUTH_URL

import harvest_products


def test_get_products(harvester_tables):
    mock_products = [
        {
            'event_id': '1',
            'product_id': str(uuid4()),
            'granules': [],
            'status_code': 'SUCCEEDED',
            'processing_date': '2020-01-01T00:00:00+00:00'
        },
        {
            'event_id': '2',
            'product_id': str(uuid4()),
            'granules': [],
            'status_code': 'PENDING',
            'processing_date': '2020-01-01T00:00:00+00:00'
        },
        {
            'event_id': '3',
            'product_id': str(uuid4()),
            'granules': [],
            'status_code': 'PENDING',
            'processing_date': '2020-01-01T00:00:00+00:00'
        },
    ]
    for product in mock_products:
        harvester_tables.product_table.put_item(Item=product)

    products = harvest_products.get_incomplete_products()

    assert products == mock_products[1:]


@responses.activate
def test_harvest(harvester_tables, s3_stubber):
    product = {
        'event_id': '1',
        'product_id': 'foo',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }

    class MockJob():
        files = [
            {'filename': 'product.zip',
             's3': {
                 'bucket': 'BUCKET',
                 'key': 'foo/product.zip',
             },
             },
        ]
        browse_images = [
            'BROWSE_IMAGE_URL',
        ]
        thumbnail_images = [
            'THUMBNAIL_IMAGE_URL',
        ]

    params = {
        'Bucket': 'BUCKET',
        'Key': 'foo/product.zip',
    }
    s3_response = {
        'ContentLength': 123
    }
    s3_stubber.add_response(method='head_object', expected_params=params, service_response=s3_response)
    params = {
        'Bucket': environ['BUCKET_NAME'],
        'Key': '1/foo/product.zip',
        'CopySource': {
            'Bucket': 'BUCKET',
            'Key': 'foo/product.zip'
        },
    }
    s3_response = {
    }
    s3_stubber.add_response(method='copy_object', expected_params=params, service_response=s3_response)
    params = {
        'Bucket': environ['BUCKET_NAME'],
        'Key': '1/foo/product.zip',
    }
    s3_response = {
        'ContentLength': 123
    }
    s3_stubber.add_response(method='head_object', expected_params=params, service_response=s3_response)

    files = harvest_products.harvest(product, MockJob())

    assert files == {
        'browse_url': 'BROWSE_IMAGE_URL',
        'thumbnail_url': 'THUMBNAIL_IMAGE_URL',
        'product_name': 'product.zip',
        'product_size': 123,
        'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/foo/product.zip'
    }


def test_update_product(harvester_tables):
    product = {
        'event_id': '1',
        'product_id': 'foo',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }
    responses.add(responses.GET, AUTH_URL)
    hyp3_repsonse = {
        'job_id': 'foo',
        'job_type': 'RTC_GAMMA',
        'name': 'event_id1',
        'request_time': '2020-06-04T18:00:03+00:00',
        'user_id': 'some_user',
        'status_code': 'SUCCEEDED',
        'browse_images': ['BROWSE_IMAGE_URL'],
        'thumbnail_images': ['THUMBNAIL_IMAGE_URL'],
        'files': [
            {
                's3': {
                    'bucket': 'BUCKET',
                    'key': 'foo/product.zip',
                },
            },
        ],
    }
    responses.add(responses.GET, environ['HYP3_URL'] + '/jobs/foo', json.dumps(hyp3_repsonse))

    def mock_harvest(foo, bar):
        return {
            'browse_url': 'BROWSE_IMAGE_URL',
            'thumbnail_url': 'THUMBNAIL_IMAGE_URL',
            'product_name': 'product.zip',
            'product_size': 123,
            'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/foo/product.zip'
        }

    harvest_products.harvest = mock_harvest

    harvest_products.update_product(product)

    updated_product = harvester_tables.product_table.scan()['Items'][0]

    assert updated_product['status_code'] == 'SUCCEEDED'
    assert updated_product['files'] == mock_harvest(None, None)


def test_is_succeeded():
    product = {
        'event_id': '1',
        'product_id': str(uuid4()),
        'granules': [],
        'status_code': 'SUCCEEDED',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }
    assert harvest_products.is_succeeded(product) is True

    product = {
        'event_id': '1',
        'product_id': str(uuid4()),
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }
    assert harvest_products.is_succeeded(product) is False