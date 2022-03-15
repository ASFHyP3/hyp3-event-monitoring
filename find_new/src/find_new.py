from datetime import datetime, timezone
from os import environ
from typing import List
from uuid import uuid4

import asf_search
import requests
from dateutil import parser
from hyp3_sdk import HyP3
from hyp3_sdk.exceptions import HyP3Error, ServerError

from database import database

SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'


class GranuleError(Exception):
    """Raised for granules for which jobs will not succeed"""


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


def get_neighbors(granule_name: str, max_neighbors: int = 2) -> List[dict]:
    results = asf_search.product_search([granule_name])
    assert len(results) == 1
    granule: asf_search.ASFProduct = results[0]

    stack = asf_search.baseline_search.stack_from_product(granule)
    stack = [item for item in stack if item.properties['temporalBaseline'] < 0]
    neighbors = [item.properties['fileID'] for item in stack[-max_neighbors:]]

    response = requests.post(
        SEARCH_URL,
        params={
            'product_list': ','.join(neighbors),
            'output': 'jsonlite'
        }
    )

    status_code = str(response.status_code)
    if status_code[0] == '4':
        raise asf_search.ASFSearch4xxError()
    elif status_code[0] == '5':
        raise asf_search.ASFSearch5xxError()

    return response.json()['results']


def submit_jobs_for_granule(hyp3, event_id, granule):
    print(f'submitting jobs for granule {granule["granuleName"]}')

    prepared_jobs = []
    granule_lists = []

    prepared_jobs.append(hyp3.prepare_rtc_job(granule=granule['granuleName']))
    granule_lists.append([granule])

    try:
        neighbors = get_neighbors(granule['granuleName'])
    except asf_search.ASFSearch4xxError:
        raise GranuleError()
    except asf_search.ASFSearchError as e:
        print(e)
        print(f'Server error finding neighbors for {granule["granuleName"]}, skipping...')
        return

    for neighbor in neighbors:
        insar_job = hyp3.prepare_insar_job(
            granule['granuleName'], neighbor['granuleName'], include_look_vectors=True, apply_water_mask=True
        )
        prepared_jobs.append(insar_job)
        granule_lists.append([granule, neighbor])

    try:
        submitted_jobs = hyp3.submit_prepared_jobs(prepared_jobs)
    except HyP3Error:
        raise GranuleError()
    except ServerError as e:
        print(e)
        print(f'Server error submitting {granule["granuleName"]} to HyP3, skipping...')
        return

    for job, granule_list in zip(submitted_jobs, granule_lists):
        product = format_product(job, event_id, granule_list)
        database.put_product(product)


def handle_event(hyp3, event):
    print(f'processing event: {event["event_id"]}')
    granules = get_unprocessed_granules(event)
    for granule in granules:
        try:
            submit_jobs_for_granule(hyp3, event['event_id'], granule)
        except GranuleError as e:
            print(e.__context__)
            print(f'Error submitting {granule["granuleName"]} to HyP3, creating FAILED product record')
            add_invalid_product_record(event['event_id'], granule, str(e.__context__))


def lambda_handler(event, context):
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    events = database.get_events()
    for event in events:
        handle_event(hyp3, event)
