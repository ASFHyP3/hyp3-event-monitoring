import json
from os import environ

import responses
from hyp3_sdk.util import AUTH_URL

import harvest_products


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

    files = harvest_products.harvest(product, MockJob())

    assert files == {
        'browse_url': 'BROWSE_IMAGE_URL',
        'thumbnail_url': 'THUMBNAIL_IMAGE_URL',
        'product_name': 'product.zip',
        'product_size': 123,
        'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/source_prefix/product.zip'
    }


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

    def mock_harvest(input_product, job):
        return {
            'browse_url': 'BROWSE_IMAGE_URL',
            'thumbnail_url': 'THUMBNAIL_IMAGE_URL',
            'product_name': 'product.zip',
            'product_size': 123,
            'product_url': f'https://{environ["BUCKET_NAME"]}.s3.amazonaws.com/1/foo/product.zip'
        }

    harvest_products.harvest = mock_harvest

    harvest_products.update_product(product)

    updated_product = tables.product_table.scan()['Items'][0]

    assert updated_product['status_code'] == 'SUCCEEDED'
    assert updated_product['files'] == mock_harvest(None, None)
