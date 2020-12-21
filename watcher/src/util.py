from os import environ

import boto3

DB = boto3.resource('dynamodb')

PRODUCT_TABLE = DB.Table(environ['PRODUCT_TABLE'])


def get_existing_products(subscription):
    return []
