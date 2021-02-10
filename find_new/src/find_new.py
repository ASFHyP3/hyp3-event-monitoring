from datetime import timezone
from os import environ

import requests
from dateutil import parser
from hyp3_sdk import HyP3, asf_search

from database import database

SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'


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
    existing_products = database.get_products_for_event(event['event_id'])
    processed_granule_names = [product['granules'][0]['granule_name'] for product in existing_products]
    return [granule for granule in all_granules if granule['granuleName'] not in processed_granule_names]


def format_granule(granule):
    acquisition_date = parser.parse(granule['startTime']).replace(tzinfo=timezone.utc).isoformat(timespec='seconds')
    return {
        'granule_name': granule['granuleName'],
        'acquisition_date': acquisition_date,
        'path': granule['path'],
        'frame': granule['frame'],
        'wkt': granule['wkt'],
    }


def format_product(job, event_id, granules):
    return {
        'product_id': job.job_id,
        'event_id': event_id,
        'granules': [format_granule(granule) for granule in granules],
        'job_type': job.job_type,
        'processing_date': job.request_time.isoformat(timespec='seconds'),
        'status_code': job.status_code,
    }


def submit_jobs_for_granule(hyp3, granule, event_id):
    print(f'submitting jobs for granule {granule["granuleName"]}')

    rtc_job = hyp3.submit_rtc_job(granule=granule['granuleName'])
    rtc_product = format_product(rtc_job, event_id, [granule])
    database.put_product(rtc_product)

    neighbors = asf_search.get_nearest_neighbors(granule['granuleName'])
    for neighbor in neighbors:
        insar_job = hyp3.submit_insar_job(granule['granuleName'], neighbor['granuleName'], include_look_vectors=True)
        insar_product = format_product(insar_job, event_id, [granule, neighbor])
        database.put_product(insar_product)


def handle_event(hyp3, event):
    print(f'processing event: {event["event_id"]}')
    granules = get_unprocessed_granules(event)
    for granule in granules:
        submit_jobs_for_granule(hyp3, granule, event['event_id'])


def lambda_handler(event, context):
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    events = database.get_events()
    for event in events:
        handle_event(hyp3, event)
