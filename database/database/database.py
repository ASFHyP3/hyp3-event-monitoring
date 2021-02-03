from datetime import datetime
from os import environ
from typing import List

import boto3
from boto3.dynamodb.conditions import Attr, Key

DB = boto3.resource('dynamodb')
EVENT_TABLE = environ.get('EVENT_TABLE', None)
PRODUCT_TABLE = environ.get('PRODUCT_TABLE', None)


def query_table(table_name, key_expression, filter_expression=None, index_name=None):
    table = DB.Table(table_name)
    query_params = {
        'KeyConditionExpression': key_expression,
    }
    if filter_expression:
        query_params['FilterExpression'] = filter_expression
    if index_name:
        query_params['IndexName'] = index_name

    response = table.query(**query_params)
    items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.query(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            **query_params
        )
        items.extend(response['Items'])
    return items


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
        return query_table(PRODUCT_TABLE, key_expression, filter_expression=filter_expression)
    else:
        return query_table(PRODUCT_TABLE, key_expression)


def get_products_by_status(status_code: str, processed_since: datetime = None) -> List[dict]:
    key_expression = Key('status_code').eq(status_code)
    if processed_since:
        key_expression &= Key('processing_date').gte(processed_since.isoformat(timespec='seconds'))

    return query_table(PRODUCT_TABLE, key_expression, index_name='status_code')


def put_product(product: dict):
    table = DB.Table(PRODUCT_TABLE)
    table.put_item(Item=product)
