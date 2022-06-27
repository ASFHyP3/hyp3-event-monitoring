from os import environ
from unittest.mock import MagicMock, call, patch

import responses
from botocore.stub import ANY
from dateutil import parser
from hyp3_sdk.jobs import Job

import harvest_products


@responses.activate
def test_harvest_file(s3_stubber):
    responses.add(responses.GET, 'https://foo.com/file.png', body='image_content')
    params = {
        'Bucket': environ['BUCKET_NAME'],
        'Key': 'prefix/file.png',
        'ContentType': 'image/png',
        'Body': ANY
    }
    s3_stubber.add_response(method='put_object', expected_params=params, service_response={})
    response = harvest_products.harvest_file('https://foo.com/file.png', 'prefix')

    assert response == f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/prefix/file.png'


@patch('harvest_products.harvest_file')
def test_harvest(mock_harvest_file: MagicMock):
    product = {
        'event_id': 'event_id',
        'product_id': 'product_id',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }

    class MockJob:
        files = [
            {
                'filename': 'product.zip',
                'size': 123,
                'url': 'PRODUCT_URL',
            },
        ]
        browse_images = [
            'BROWSE_IMAGE_URL',
        ]
        thumbnail_images = [
            'THUMBNAIL_IMAGE_URL',
        ]

    mock_harvest_file.return_value = 'https://foo.com/file.png'
    files = harvest_products.harvest(product, MockJob())

    assert files == {
        'browse_url': 'https://foo.com/file.png',
        'thumbnail_url': 'https://foo.com/file.png',
        'product_name': 'product.zip',
        'product_size': 123,
        'product_url': 'https://foo.com/file.png'
    }

    assert mock_harvest_file.mock_calls == [
        call('BROWSE_IMAGE_URL', 'event_id/product_id'),
        call('THUMBNAIL_IMAGE_URL', 'event_id/product_id'),
        call('PRODUCT_URL', 'event_id/product_id'),
    ]


def test_update_product_succeeded(tables):
    product = {
        'event_id': '1',
        'product_id': 'foo',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }

    job = Job(
        job_type='RTC_GAMMA',
        job_id='foo',
        request_time=parser.parse('2020-01-01T00:00:00+00:00'),
        status_code='SUCCEEDED',
        user_id='some_user',
        browse_images=['BROWSE_IMAGE_URL'],
        thumbnail_images=['THUMBNAIL_IMAGE_URL'],
        files=[
            {
                's3': {
                    'bucket': 'BUCKET',
                    'key': 'foo/product.zip',
                },
            },
        ],
    )

    mock_harvest = {
        'browse_url': 'BROWSE_IMAGE_URL',
        'thumbnail_url': 'THUMBNAIL_IMAGE_URL',
        'product_name': 'product.zip',
        'product_size': 123,
        'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/foo/product.zip'
    }

    with patch('harvest_products.harvest', lambda x, y: mock_harvest):
        harvest_products.update_product(product, job)

    updated_product = tables.product_table.scan()['Items'][0]

    assert updated_product['status_code'] == 'SUCCEEDED'
    assert updated_product['files'] == mock_harvest


def test_update_product_failed(tables):
    product = {
        'event_id': '1',
        'product_id': 'foo',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }

    job = Job(
        job_type='RTC_GAMMA',
        job_id='foo',
        request_time=parser.parse('2020-01-01T00:00:00+00:00'),
        status_code='FAILED',
        user_id='some_user',
    )

    harvest_products.update_product(product, job)

    updated_product = tables.product_table.scan()['Items'][0]

    assert updated_product['status_code'] == 'FAILED'
    assert 'files' not in updated_product
