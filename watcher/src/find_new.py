from os import environ

import boto3
import requests
from boto3.dynamodb.conditions import Key
from hyp3_sdk import HyP3

SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'
DB = boto3.resource('dynamodb')


def get_events():
    table = DB.Table(environ['EVENT_TABLE'])
    response = table.scan()
    events = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        events.extend(response['Items'])
    return events


def get_existing_products(event_id):
    table = DB.Table(environ['PRODUCT_TABLE'])
    key_expression = Key('event_id').eq(event_id)
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
        'start': event['processing_timeframe']['start'],
        'end': event['processing_timeframe'].get('end'),
        'beamMode': 'IW',
        'platform': 'SENTINEL-1',
        'processingLevel': 'SLC',
        'output': 'jsonlite',
    }
    response = requests.get(SEARCH_URL, params=search_params)
    response.raise_for_status()
    return response.json()['results']


def get_unprocessed_granules(event):
    all_granules = get_granules(event)
    processed_granule_names = [product['granules'][0]['granule_name'] for product in get_existing_products(event['event_id'])]
    return [granule for granule in all_granules if granule['granuleName'] not in processed_granule_names]


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


def get_insar_neighbor(granule_name, distance):
    return {}


def format_granule(granule):
    return {
        'granule_name': granule['granuleName'],
        'acquisition_date': granule['startTime'],
        'path': granule['path'],
        'frame': granule['frame'],
        'wkt': granule['wkt'],
    }


def format_product(job, event, granules):
    return {
        'product_id': job.job_id,
        'event_id': event['event_id'],
        'granules': [format_granule(granule) for granule in granules],
        'job_type': job.job_type,
    }


def add_product_for_processing(granule, event, process):
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    table = DB.Table(environ['PRODUCT_TABLE'])
    products = []
    if process['job_type'] == 'RTC_GAMMA':
        job = hyp3.submit_rtc_job(granule=granule['granuleName'], **process['parameters'])
        products.append(format_product(job, event, [granule]))
    # elif process['job_type'] == 'INSAR_GAMMA':
    #     for depth in (1, 2):
    #         neighbor = get_insar_neighbor(granule, depth)
    #         job = hyp3.submit_insar_job(granule['granuleName'], neighbor['granuleName'], **process['parameters'])
    #         products.append(format_product(job, event, [granule, neighbor]))
    else:
        pass
        # TODO handle unknown job type
    print(products)
    for product in products:
        table.put_item(Item=product)


def lambda_handler(event, context):
    events = get_events()
    processes = get_processes()
    for event in events:
        granules = get_unprocessed_granules(event)
        print(granules)
        for granule in granules:
            for process in processes:
                add_product_for_processing(granule, event, process)
