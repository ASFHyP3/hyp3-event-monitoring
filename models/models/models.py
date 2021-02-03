from datetime import datetime
from os import environ
from typing import List

import boto3
from boto3.dynamodb.conditions import Attr, Key

DB = boto3.resource('dynamodb')
EVENT_TABLE = environ['EVENT_TABLE']
PRODUCT_TABLE = environ['PRODUCT_TABLE']


class Event:
    def __init__(self, event_id, processing_start=None, processing_end=None, wkt=None, **kwargs):
        self.event_id = event_id
        self.processing_start = processing_start
        self.processing_end = processing_end
        self.wkt = wkt
        self.extras = kwargs

    def __eq__(self, other):
        variables_to_compare = [attr for attr in dir(Event) if
                                not callable(getattr(Event, attr)) and not attr.startswith("__")]
        return all(getattr(self, a, NotImplementedError) == getattr(other, a, NotImplementedError) for a in
                   variables_to_compare)

    def to_dict(self):
        d = {
            'event_id': self.event_id,
            **self.extras,
        }
        if self.processing_start is not None:
            d['processing_timeframe']['start'] = self.processing_end
        if self.processing_end is not None:
            d['processing_timeframe']['end'] = self.processing_end
        if self.wkt is not None:
            d['wkt'] = self.wkt
        return d

    @staticmethod
    def from_dict(input_dict):
        return Event(**input_dict)


class Product:
    def __init__(self, product_id,
                 event_id,
                 granules=None,
                 status_code=None,
                 processing_date=None,
                 job_type=None,
                 files=None,
                 **kwargs):
        self.product_id = product_id
        self.event_id = event_id
        self.granules = granules
        self.status_code = status_code
        self.processing_date = processing_date
        self.job_type = job_type
        self.files = files
        self.extras = kwargs

    def __eq__(self, other):
        variables_to_compare = [attr for attr in dir(Product) if
                                not callable(getattr(Product, attr)) and not attr.startswith("__")]
        return all(getattr(self, a, NotImplementedError) == getattr(other, a, NotImplementedError) for a in
                   variables_to_compare)

    def to_dict(self):
        d = {
            'event_id': self.event_id,
            'product_id': self.product_id,
            **self.extras,
        }
        if self.granules is not None:
            d['granules'] = self.granules
        if self.status_code is not None:
            d['status_code'] = self.status_code
        if self.processing_date is not None:
            d['processing_date'] = self.processing_date
        if self.job_type is not None:
            d['job_type'] = self.job_type
        if self.files is not None:
            d['files'] = self.files
        return d

    @staticmethod
    def from_dict(input_dict):
        return Product(**input_dict)


def get_events() -> List[Event]:
    table = DB.Table(EVENT_TABLE)
    response = table.scan()
    events = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        events.extend(response['Items'])

    return [Event.from_dict(event) for event in events]


def get_event(event_id: str) -> Event:
    table = DB.Table(EVENT_TABLE)
    response = table.get_item(Key={'event_id': event_id})

    if 'Item' not in response:
        raise ValueError(f'Event {event_id} not found')

    return Event.from_dict(response['Item'])


def get_products_for_event(event_id: str, status_code: str = None) -> List[Product]:
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

    return [Product.from_dict(product) for product in products]


def get_products_by_status(status_code: str, processed_since: datetime = None) -> List[Product]:
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

    products = response['Items']
    return [Product.from_dict(product) for product in products]


def put_product(product: Product):
    table = DB.Table(PRODUCT_TABLE)
    table.put_item(Item=product.to_dict())
