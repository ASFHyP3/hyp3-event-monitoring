from datetime import timezone
from os import environ
from typing import List

import requests
from dateutil import parser
from hyp3_sdk import HyP3

from database import database

SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'
BASELINE_URL = 'https://api.daac.asf.alaska.edu/services/search/baseline'


def get_nearest_neighbors(granule: str, max_neighbors: int = 2,) -> List[dict]:
    """Get a granules nearest neighbors from a temporal stack (backwards in time)
    Args:
        granule: reference granule
        max_neighbors: maximum number of neighbors to return
    Returns:
        neighbors: a list of neighbors sorted by time
    """
    params = {
        'output': 'jsonlite',
        'master': granule,
    }
    response = requests.get(BASELINE_URL, params=params)
    response.raise_for_status()
    all_neighbors = response.json()['results']
    selected_neighbors = [n for n in all_neighbors if n['temporalBaseline'] < 0]
    selected_neighbors.sort(key=lambda k: k['temporalBaseline'], reverse=True)

    return selected_neighbors[:max_neighbors]


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
        {
            'job_type': 'INSAR_GAMMA',
            'parameters': {
                'include_look_vectors': True,
                'include_los_displacement': False,
                'looks': '20x4',
            },
        },
    ]


def format_granule(granule):
    acquisition_date = parser.parse(granule['startTime']).replace(tzinfo=timezone.utc).isoformat(timespec='seconds')
    return {
        'granule_name': granule['granuleName'],
        'acquisition_date': acquisition_date,
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
        'processing_date': job.request_time.isoformat(timespec='seconds'),
        'status_code': job.status_code,
    }


def add_product_for_processing(granule, event, process):
    print(f'submitting {process["job_type"]} for {granule}')
    hyp3 = HyP3(environ['HYP3_URL'], username=environ['EDL_USERNAME'], password=environ['EDL_PASSWORD'])
    products = []
    if process['job_type'] == 'RTC_GAMMA':
        job = hyp3.submit_rtc_job(granule=granule['granuleName'], **process['parameters'])
        products.append(format_product(job, event, [granule]))
    elif process['job_type'] == 'INSAR_GAMMA':
        neighbors = get_nearest_neighbors(granule['granuleName'])
        for neighbor in neighbors:
            job = hyp3.submit_insar_job(granule['granuleName'], neighbor['granuleName'], **process['parameters'])
            products.append(format_product(job, event, [granule, neighbor]))
    else:
        raise NotImplementedError('Unknown or unimplemented process job type')
    for product in products:
        print(f'adding product for processing: {product}')
        database.put_product(product)


def handle_event(event, processes):
    print(f'processing event: {event["event_id"]}')
    granules = get_unprocessed_granules(event)
    for granule in granules:
        for process in processes:
            add_product_for_processing(granule, event, process)


def lambda_handler(event, context):
    events = database.get_events()
    processes = get_processes()
    for event in events:
        handle_event(event, processes)
