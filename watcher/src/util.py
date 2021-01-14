from os import environ

import boto3
from boto3.dynamodb.conditions import Key

DB = boto3.resource('dynamodb')

PRODUCT_TABLE = DB.Table(environ['PRODUCT_TABLE'])


def get_existing_products(subscription):
    key_expression = Key('subscription_name').eq(subscription)
    products = PRODUCT_TABLE.query(KeyConditionExpression=key_expression)
    return products['Items']
