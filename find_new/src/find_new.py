from datetime import datetime, timezone
from os import environ
from uuid import uuid4

import requests
from dateutil import parser
from hyp3_sdk import HyP3, asf_search
from hyp3_sdk.exceptions import HyP3Error

from database import database

SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'

class ProductException(Exception):
    """thrown when product submission encounters a known error
     that should be retried but not block other Products from being submitted"""

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


def add_invalid_product_record(event_id, granule, message):
    product = {
        'product_id': str(uuid4()),
        'event_id': event_id,
        'granules': [format_granule(granule)],
        'processing_date': datetime.now(tz=timezone.utc).isoformat(timespec='seconds'),
        'status_code': 'FAILED',
        'message': message,
    }
    database.put_product(product)


def submit_jobs_for_granule(hyp3, granule, event_id):
    print(f'submitting jobs for granule {granule["granuleName"]}')

    prepared_jobs = []
    granule_lists = []

    prepared_jobs.append(hyp3.prepare_rtc_job(granule=granule['granuleName']))
    granule_lists.append([granule])

    try:
        neighbors = asf_search.get_nearest_neighbors(granule['granuleName'])
    except requests.HTTPError as e:
        raise ProductException()

    for neighbor in neighbors:
        insar_job = hyp3.prepare_insar_job(granule['granuleName'], neighbor['granuleName'], include_look_vectors=True)
        prepared_jobs.append(insar_job)
        granule_lists.append([granule, neighbor])

    try:
        submitted_jobs = hyp3.submit_prepared_jobs(prepared_jobs)
    except HyP3Error as e:
        raise ProductException()

    for job, granule_list in zip(submitted_jobs, granule_lists):
        product = format_product(job, event_id, granule_list)
        database.put_product(product)


def handle_event(hyp3, event):
    print(f'processing event: {event["event_id"]}')
    granules = get_unprocessed_granules(event)
    for granule in granules:
        try:
            submit_jobs_for_granule(hyp3, granule, event['event_id'])
        except ProductException as e:
            add_invalid_product_record(event['event_id'], granule, str(e))


def lambda_handler(event, context):
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    events = database.get_events()
    for event in events:
        handle_event(hyp3, event)
