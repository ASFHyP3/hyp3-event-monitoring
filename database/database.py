from datetime import datetime
from os import environ
from typing import List

import boto3
from boto3.dynamodb.conditions import Key, Attr

DB = boto3.resource('dynamodb')
EVENT_TABLE = environ['EVENT_TABLE']
PRODUCT_TABLE = environ['PRODUCT_TABLE']


def get_events() -> List[dict]:
    table = DB.Table(EVENT_TABLE)
    response = table.scan()
    events = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        events.extend(response['Items'])

    return events


def get_event(event_id: str) -> dict:
    table = DB.Table(EVENT_TABLE)
    response = table.get_item(Key={'event_id': event_id})

    if 'Item' not in response:
        raise ValueError(f'Event {event_id} not found')

    return response['Item']


def get_products_for_event(event_id: str, status_code: str = None) -> List[dict]:

    key_expression = Key('event_id').eq(event_id)
    if status_code:
        filter_expression = Attr('status_code').eq(status_code)
    else:
        filter_expression = Attr('event_id').exists()

    table = DB.Table(PRODUCT_TABLE)
    response = table.query(KeyConditionExpression=key_expression, FilterExpression=filter_expression)
    products = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression=key_expression,
            FilterExpression=filter_expression,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        products.extend(response['Items'])

    return products


def get_products_by_status(status_code: str, processed_since: datetime = None) -> List[dict]:

    key_expression = Key('status_code').eq(status_code)
    if processed_since:
        key_expression &= Key('processing_date').gte(processed_since.isoformat(timespec='seconds'))

    table = DB.Table(PRODUCT_TABLE)
    response = table.query(IndexName='status_code', KeyConditionExpression=key_expression)
    products = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.query(
            IndexName='status_code',
            KeyConditionExpression=key_expression,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        products.extend(response['Items'])

    return response['Items']


def put_product(product: dict):
    table = DB.Table(PRODUCT_TABLE)
    table.put_item(Item=product)
