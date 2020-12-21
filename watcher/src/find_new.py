from os import environ
from uuid import uuid4

from hyp3_sdk import HyP3
from hyp3_sdk.util import get_authenticated_session

from src.util import get_existing_products, DB, PRODUCT_TABLE
from src.nearest_neighbor import make_pairs

SUBSCRIPTION_TABLE = DB.Table(environ['SUBSCRIPTION_TABLE'])
HYP3 = HyP3(environ['HYP3_URL'])


def get_actionable_subscriptions():
    return []


def get_rtc_granules(subscription):
    session = get_authenticated_session(environ['EDLUSERNAME'], environ['EDLPASSWORD'])
    response = session.get('https://api.daac.asf.alaska.edu/services/search/param',
                           params={
                               'intersectsWith': subscription['geometry'],
                               'start': subscription['start'],
                               'end': subscription['end'],
                               'platform': 'SENTINEL-1',
                               'processingLevel': subscription['product_types'],
                               'output': 'jsonlite',
                           })
    return [granule['granuleName'] for granule in response.json()['results']]


def submit_product_to_hyp3(subscription, granules):
    if subscription['processing_type'] == 'RTC_GAMMA':
        return HYP3.submit_rtc_job(granules[0],
                                   name=subscription['subscription_name'],
                                   dem_matching=subscription['processing_parameters']['dem_matching'],
                                   include_dem=subscription['processing_parameters']['include_dem'],
                                   include_inc_map=subscription['processing_parameters']['include_inc_map'],
                                   include_sattering_area=subscription['processing_parameters'][
                                       'include_sattering_area'],
                                   radiometry=subscription['processing_parameters']['radiometry'],
                                   resolution=subscription['processing_parameters']['resolution'],
                                   scale=subscription['processing_parameters']['scale'],
                                   speckle_filter=subscription['processing_parameters']['speckle_filter']
                                   )
    elif subscription['processing_type'] == 'INSAR_GAMMA':
        return HYP3.submit_insar_job(granules[0],
                                     granules[1],
                                     subscription['subscription_name'],
                                     include_look_vectors=subscription['processing_parameters']['include_look_vectors'],
                                     include_los_displacement=subscription['processing_parameters'][
                                         'include_los_displacement'],
                                     looks=subscription['processing_parameters']['looks']
                                     )


def add_product_for_subscription(subscription, granules):
    product = submit_product_to_hyp3(subscription, granules)
    product_item = {
        'product_id': uuid4(),
        'subscription_id': subscription['subscription_id'],
        'hyp3_id': product.job_id,
        'status_code': 'PROCESSING',
    }
    PRODUCT_TABLE.put_item(Item=product_item)


def get_insar_pairs(subscription):
    return make_pairs(get_rtc_granules(subscription))


def lambda_handler(event, context):
    subscriptions = get_actionable_subscriptions()
    for subscription in subscriptions:
        products = get_existing_products(subscription)
        if subscription['processing_type'] == 'RTC_GAMMA':
            granules = get_rtc_granules(subscription)
            for granule in granules:
                if granule not in [product['granules'] for product in products]:
                    add_product_for_subscription(subscription, granule)
        if subscription['processing_type'] == 'INSAR_GAMMA':
            pairs = get_insar_pairs(subscription)
            for pair in pairs:
                if sorted(pair) not in [sorted(product['granules']) for product in products]:
                    add_product_for_subscription(subscription, pair)
