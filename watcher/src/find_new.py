from os import environ
from uuid import uuid4

import requests
from hyp3_sdk import HyP3

import boto3
from boto3.dynamodb.conditions import Key

DB = boto3.resource('dynamodb')
HYP3 = HyP3(environ['HYP3_URL'], username=environ['EDLUSERNAME'], password=environ['EDLPASSWORD'])
SEARCH_URL = 'https://api.daac.asf.alaska.edu/services/search/param'


def get_actionable_subscriptions():
    table = DB.Table(environ['SUBSCRIPTION_TABLE'])
    response = table.scan()
    return response['Items']  # TODO implement filtering


def get_existing_products(subscription_name):
    table = DB.Table(environ['PRODUCT_TABLE'])

    key_expression = Key('subscription_name').eq(subscription_name)
    products = table.query(KeyConditionExpression=key_expression)
    return products['Items']


def get_rtc_granules(subscription):
    response = requests.get(SEARCH_URL,
                            params={
                                'intersectsWith': subscription.get('geometry'),
                                'start': subscription['start'],
                                'end': subscription['end'],
                                'platform': 'SENTINEL-1',
                                'processingLevel': subscription['file_types'],
                                'output': 'jsonlite',
                            })
    response.raise_for_status()
    return [granule['granuleName'] for granule in response.json()['results']]


def submit_product_to_hyp3(subscription, granules):
    if subscription['processing_type'] == 'RTC_GAMMA':
        return HYP3.submit_rtc_job(granules[0],
                                   name=subscription['subscription_name'],
                                   dem_matching=subscription['processing_parameters']['dem_matching'],
                                   include_dem=subscription['processing_parameters']['include_dem'],
                                   include_inc_map=subscription['processing_parameters']['include_inc_map'],
                                   include_sattering_area=subscription['processing_parameters'][
                                       'include_scattering_area'],
                                   radiometry=subscription['processing_parameters']['radiometry'],
                                   resolution=float(subscription['processing_parameters']['resolution']),
                                   scale=subscription['processing_parameters']['scale'],
                                   speckle_filter=subscription['processing_parameters']['speckle_filter']
                                   )


def add_product_for_subscription(subscription, granules):
    table = DB.Table(environ['PRODUCT_TABLE'])
    product = submit_product_to_hyp3(subscription, granules)
    product_item = {
        'product_id': str(uuid4()),
        'subscription_name': subscription['subscription_name'],
        'hyp3_id': product.job_id,
        'status_code': 'PENDING',
        'granules': granules,
    }
    table.put_item(Item=product_item)


def lambda_handler(event, context):
    subscriptions = get_actionable_subscriptions()
    for subscription in subscriptions:
        products = get_existing_products(subscription['subscription_name'])
        if subscription['processing_type'] == 'RTC_GAMMA':
            granules = get_rtc_granules(subscription)
            for granule in granules:
                if granule not in [product['granules'] for product in products]:
                    add_product_for_subscription(subscription, [granule])
