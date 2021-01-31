from os import environ

import boto3
from boto3.dynamodb.conditions import Key
from hyp3_sdk import HyP3

DB = boto3.resource('dynamodb')
S3 = boto3.resource('s3')


def harvest(product, job):
    destination_bucket = S3.Bucket(environ['BUCKET_NAME'])
    copy_source = {
        'Bucket': job.files[0]['s3']['bucket'],
        'Key': job.files[0]['s3']['key'],
    }
    product_name = job.files[0]['filename']
    destination_key = f'{product["event_id"]}/{product["product_id"]}/{product_name}'
    destination_bucket.copy(copy_source, destination_key)

    return {
        'browse_url': job.browse_images[0],
        'thumbnail_url': job.thumbnail_images[0],
        'product_name': product_name,
        'product_size': job.files[0]['size'],
        'product_url': f'https://{destination_bucket.name}.s3.amazonaws.com/{destination_key}',
    }


def update_product(product):
    table = DB.Table(environ['PRODUCT_TABLE'])
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    job = hyp3._get_job_by_id(product['product_id'])
    if job.complete():
        if job.succeeded():
            product['files'] = harvest(product, job)
        product['status_code'] = job.status_code
        table.put_item(Item=product)


def get_incomplete_products():
    table = DB.Table(environ['PRODUCT_TABLE'])
    key_expression = Key('status_code').eq('PENDING')
    response = table.query(IndexName='status_code', KeyConditionExpression=key_expression)
    products = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.query(
            IndexName='status_code',
            KeyConditionExpression=key_expression,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        products.extend(response['Items'])
    return products


def lambda_handler(event, context):
    products = get_incomplete_products()
    for product in products:
        update_product(product)
