from os import environ
from pathlib import Path

import boto3
import pytest
import yaml
from botocore.stub import Stubber
from moto import mock_dynamodb2

import api
import find_new
import harvest_products


def get_table_properties_from_template(resource_name):
    yaml.SafeLoader.add_multi_constructor('!', lambda loader, suffix, node: None)
    template_file = Path(__file__).parent.parent / 'cloudformation.yml'
    with open(template_file, 'r') as f:
        template = yaml.safe_load(f)
    table_properties = template['Resources'][resource_name]['Properties']
    return table_properties


@pytest.fixture
def tables():
    with mock_dynamodb2():
        find_new.DB = boto3.resource('dynamodb')

        class Tables:
            event_table = find_new.DB.create_table(
                TableName=environ['EVENT_TABLE'],
                **get_table_properties_from_template('EventTable'),
            )
            product_table = find_new.DB.create_table(
                TableName=environ['PRODUCT_TABLE'],
                **get_table_properties_from_template('ProductTable')
            )

        tables = Tables()
        yield tables


@pytest.fixture
def api_tables():
    with mock_dynamodb2():
        api.dynamodb = boto3.resource('dynamodb')

        class Tables:
            event_table = api.dynamodb.create_table(
                TableName=environ['EVENT_TABLE'],
                **get_table_properties_from_template('EventTable'),
            )
            product_table = api.dynamodb.create_table(
                TableName=environ['PRODUCT_TABLE'],
                **get_table_properties_from_template('ProductTable')
            )

        tables = Tables()
        yield tables


@pytest.fixture
def harvester_tables():
    with mock_dynamodb2():
        harvest_products.DB = boto3.resource('dynamodb')

        class Tables:
            event_table = harvest_products.DB.create_table(
                TableName=environ['EVENT_TABLE'],
                **get_table_properties_from_template('EventTable'),
            )
            product_table = harvest_products.DB.create_table(
                TableName=environ['PRODUCT_TABLE'],
                **get_table_properties_from_template('ProductTable')
            )

        tables = Tables()
        yield tables


@pytest.fixture
def s3_stubber():
    with Stubber(harvest_products.S3.meta.client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def api_client():
    with api.app.test_client() as client:
        yield client
