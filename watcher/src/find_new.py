from os import environ

import boto3
import requests
from boto3.dynamodb.conditions import Key
from hyp3_sdk import HyP3

SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'
HYP3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
DB = boto3.resource('dynamodb')


def get_events():
    table = DB.Table(environ['EVENT_TABLE'])
    response = table.scan()
    events = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.query(
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        events.extend(response['Items'])
    return events


def get_existing_products(event):
    table = DB.Table(environ['PRODUCT_TABLE'])
    key_expression = Key('event_id').eq(event['event_id'])
    response = table.query(KeyConditionExpression=key_expression)
    products = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression=key_expression,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        products.extend(response['Items'])
    return products


def get_granules(event):
    search_params = {
        'intersectsWith': event.get('wkt'),
        'start': event['start'],
        'end': event.get('end'),
        'beamMode': 'IW',
        'platform': 'SENTINEL-1',
        'processingLevel': 'SLC',
        'output': 'jsonlite',
    }
    response = requests.get(SEARCH_URL, params=search_params)
    response.raise_for_status()
    return [granule['granuleName'] for granule in response.json()['results']]


def get_unprocessed_granules(event):
    all_granules = get_granules(event)
    processed_granules = []
    for product in get_existing_products(event):
        processed_granules.extend(product['granules'])
    return [granule for granule in all_granules if granule not in processed_granules]


def get_processes():
    return [
        {
            'job_type': 'RTC_GAMMA',
            'parameters': {
                'dem_matching': False,
                'include_dem': False,
                'include_inc_map': False,
                'include_scattering_area': False,
                'radiometry': 'gamma0',
                'resolution': 30,
                'scale': 'power',
                'speckle_filter': False,
            },
        },
    ]


def get_insar_neighbor(granule, distance):
    return ""


def add_product_for_processing(granule, event, process):
    table = DB.Table(environ['PRODUCT_TABLE'])
    products = []
    if process['job_type'] == 'RTC_GAMMA':
        products.append(HYP3.submit_rtc_job(granule=granule, **process['parameters']))
    elif process['job_type'] == 'INSAR_GAMMA':
        nearest_neighbor = get_insar_neighbor(granule, 1)
        next_nearest_neighbor = get_insar_neighbor(granule, 2)
        products.append(HYP3.submit_insar_job(granule1=granule, granule2=nearest_neighbor, **process['parameters']))
        products.append(
            HYP3.submit_insar_job(granule1=granule, granule2=next_nearest_neighbor, **process['parameters']))
    else:
        pass
        # TODO handle unknown job type
    for product in products:
        table.put_item(
            {
                'product_id': product.job_id,
                'event_id': event['event_id'],
                'granules': product.job_parameters['granules'],
                'job_type': product.job_type,
            }
        )


def lambda_handler(event, context):
    events = get_events()
    processes = get_processes()
    for event in events:
        granules = get_unprocessed_granules(event['event_id'])
        for granule in granules:
            for process in processes:
                add_product_for_processing(granule, event, process)
