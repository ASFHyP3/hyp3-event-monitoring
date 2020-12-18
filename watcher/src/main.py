from os import environ

import boto3
import hyp3_sdk
from hyp3_sdk import HyP3
from hyp3_sdk.exceptions import HyP3Error

DB = boto3.resource('dynamodb')
SUBSCRIPTION_TABLE = DB.Table(environ['SUBSCRIPTION_TABLE'])
PRODUCT_TABLE = DB.Table(environ['PRODUCT_TABLE'])
HYP3 = HyP3(environ['HYP3_URL'])

def get_actionable_subscriptions():
    return []


def get_rtc_granules():
    return []


def get_subscription_products(subscription):
    return []


def add_product_for_subscription(subscription, granule):
    pass


def submit_product_to_hyp3(subscription, product):
    return 0


def collect_product_files(product):
    pass


def update_products(subscription):
    products = get_subscription_products(subscription)
    for product in products:
        if not product['finished']:
            if not product.get('hyp3_id'):
                product['hyp3_id'] = submit_product_to_hyp3()
                continue
            hyp3_job = HYP3._get_job_by_id(product['hyp3_id'])
            product['status_code'] = hyp3_job['status_code']
            if product['status_code'] == 'SUCCEEDED':
                collect_product_files(product)
        PRODUCT_TABLE.put_item(product)


def get_insar_pairs(subscription):
    return []


def lambda_handler(event, context):
    subscriptions = get_actionable_subscriptions()
    for subscription in subscriptions:
        products = get_subscription_products(subscription)
        if subscription['processing_type'] == 'RTC':
            granules = get_rtc_granules(subscription)
            for granule in granules:
                if granule not in [product['granules'] for product in products]:
                    add_product_for_subscription(subscription, granule)
        if subscription['processing_type'] == 'INSAR':
            pairs = get_insar_pairs(subscription)
            for pair in pairs:
                if pair not in [product['granules'] for product in products]:
                    add_product_for_subscription(subscription, pair)
        update_products(subscription)

