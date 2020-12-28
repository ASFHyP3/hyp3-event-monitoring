from os import environ

from hyp3_sdk import HyP3

from src.util import get_existing_products, PRODUCT_TABLE

HYP3 = HyP3(environ['HYP3_URL'])


def collect_product_files(product):

    pass


def update_products(subscription):
    products = get_existing_products(subscription)
    for product in products:
        if not product['finished']:
            hyp3_job = HYP3._get_job_by_id(product['hyp3_id'])
            product['status_code'] = hyp3_job['status_code']
            if product['status_code'] == 'SUCCEEDED':
                collect_product_files(product)
        PRODUCT_TABLE.put_item(product)
