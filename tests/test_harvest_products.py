import json
from os import environ
from unittest import mock

import responses
from botocore.stub import ANY
from hyp3_sdk.util import AUTH_URL

import harvest_products


@responses.activate
def test_harvest_image(s3_stubber):
    responses.add(responses.GET, 'https://foo.com/file.png', body='image_content')
    params = {
        'Bucket': environ['BUCKET_NAME'],
        'Key': 'prefix/file.png',
        'ContentType': 'image/png',
        'Body': ANY
    }
    s3_stubber.add_response(method='put_object', expected_params=params, service_response={})
    bucket = harvest_products.S3.Bucket(environ['BUCKET_NAME'])
    response = harvest_products.harvest_image('https://foo.com/file.png', bucket, 'prefix')

    assert response == f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/prefix/file.png'


@responses.activate
def test_harvest(s3_stubber):
    product = {
        'event_id': '1',
        'product_id': 'source_prefix',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }

    class MockJob:
        files = [
            {
                'filename': 'product.zip',
                'size': 123,
                's3': {
                    'bucket': 'sourceBucket',
                    'key': 'source_prefix/product.zip',
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
        'Bucket': 'sourceBucket',
        'Key': 'source_prefix/product.zip',
    }
    s3_response = {
        'ContentLength': 123
    }
    s3_stubber.add_response(method='head_object', expected_params=params, service_response=s3_response)

    params = {
        'Bucket': environ['BUCKET_NAME'],
        'Key': '1/source_prefix/product.zip',
        'CopySource': {
            'Bucket': 'sourceBucket',
            'Key': 'source_prefix/product.zip'
        },
    }
    s3_stubber.add_response(method='copy_object', expected_params=params, service_response={})

    with mock.patch('harvest_products.harvest_image', lambda x, y, z: 'https://foo.com/file.png'):
        files = harvest_products.harvest(product, MockJob())

    assert files == {
        'browse_url': 'https://foo.com/file.png',
        'thumbnail_url': 'https://foo.com/file.png',
        'product_name': 'product.zip',
        'product_size': 123,
        'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/source_prefix/product.zip'
    }


@responses.activate
def test_update_product(tables):
    product = {
        'event_id': '1',
        'product_id': 'foo',
        'granules': [],
        'status_code': 'PENDING',
        'processing_date': '2020-01-01T00:00:00+00:00'
    }

    hyp3_response = {
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
    responses.add(responses.GET, AUTH_URL)
    responses.add(responses.GET, environ['HYP3_URL'] + '/jobs/foo', json.dumps(hyp3_response))

    mock_harvest = {
        'browse_url': 'BROWSE_IMAGE_URL',
        'thumbnail_url': 'THUMBNAIL_IMAGE_URL',
        'product_name': 'product.zip',
        'product_size': 123,
        'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/foo/product.zip'
    }

    with mock.patch('harvest_products.harvest', lambda x, y: mock_harvest):
        harvest_products.update_product(product)

    updated_product = tables.product_table.scan()['Items'][0]

    assert updated_product['status_code'] == 'SUCCEEDED'
    assert updated_product['files'] == mock_harvest
