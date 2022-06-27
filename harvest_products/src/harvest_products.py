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


def harvest_file(file_url, destination_prefix):
    destination_bucket = S3.Bucket(environ['BUCKET_NAME'])
    filename = basename(urlparse(file_url).path)
    destination_key = f'{destination_prefix}/{filename}'
    response = requests.get(file_url)
    response.raise_for_status()
    content_type = guess_type(filename)[0] if guess_type(filename)[0] else 'application/octet-stream'
    destination_bucket.put_object(Body=io.BytesIO(response.content), Key=destination_key, ContentType=content_type)
    return f'https://{destination_bucket.name}.s3.amazonaws.com/{destination_key}'


def harvest(product, job):
    destination_prefix = f'{product["event_id"]}/{product["product_id"]}'
    product_file = job.files[0]

    return {
        'browse_url': harvest_file(job.browse_images[0], destination_prefix),
        'thumbnail_url': harvest_file(job.thumbnail_images[0], destination_prefix),
        'product_name': product_file['filename'],
        'product_size': product_file['size'],
        'product_url': harvest_file(product_file['url'], destination_prefix),
    }


def update_product(product, job):
    print(f'job status is {job.status_code}')
    if job.succeeded():
        product['files'] = harvest(product, job)
    product['status_code'] = job.status_code
    print(f'updating product table for: {product}')
    database.put_product(product)


def lambda_handler(event, context):
    products = database.get_products_by_status('PENDING')
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    for product in products:
        print(f'Checking on product: {product["product_id"]}')
        job = hyp3.get_job_by_id(product['product_id'])
        if job.complete():
            update_product(product, job)
