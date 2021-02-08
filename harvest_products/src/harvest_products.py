import io
from mimetypes import guess_type
from os import environ
from os.path import basename
from urllib.parse import urlparse

import boto3
import requests
from hyp3_sdk import HyP3

from database import database

S3 = boto3.resource('s3')


def harvest_image(image_url, destination_bucket, destination_prefix):
    filename = basename(urlparse(image_url).path)
    destination_key = f'{destination_prefix}/{filename}'
    response = requests.get(image_url)
    response.raise_for_status()
    content_type = guess_type(filename)[0] if guess_type(filename)[0] else 'application/octet-stream'
    destination_bucket.put_object(Body=io.BytesIO(response.content), Key=destination_key, ContentType=content_type)
    return f'https://{destination_bucket.name}.s3.amazonaws.com/{destination_key}'


def harvest(product, job):
    destination_bucket = S3.Bucket(environ['BUCKET_NAME'])
    copy_source = {
        'Bucket': job.files[0]['s3']['bucket'],
        'Key': job.files[0]['s3']['key'],
    }
    product_name = job.files[0]['filename']
    destination_prefix = f'{product["event_id"]}/{product["product_id"]}'
    destination_key = f'{destination_prefix}/{product_name}'
    print(f'copying {product_name} to s3://{destination_bucket.name}/{destination_key}')
    destination_bucket.copy(copy_source, destination_key)

    return {
        'browse_url': harvest_image(job.browse_images[0], destination_bucket, destination_prefix),
        'thumbnail_url': harvest_image(job.thumbnail_images[0], destination_bucket, destination_prefix),
        'product_name': product_name,
        'product_size': job.files[0]['size'],
        'product_url': f'https://{destination_bucket.name}.s3.amazonaws.com/{destination_key}',
    }


def update_product(product):
    print(f'Checking on product: {product}')
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    job = hyp3._get_job_by_id(product['product_id'])
    if job.complete():
        print(f'product status is {job.status_code}')
        if job.succeeded():
            product['files'] = harvest(product, job)
        product['status_code'] = job.status_code
        print(f'updating product table for: {product}')
        database.put_product(product)


def lambda_handler(event, context):
    products = database.get_products_by_status('PENDING')
    for product in products:
        update_product(product)
