from uuid import uuid4

import harvest_products

def test_get_products(tables):
    mock_products = [
        {
            'event_id': '1',
            'product_id': str(uuid4()),
            'granules': [],
            'status_code': 'SUCCEEDED',
            'processing_date': '2020-01-01T00:00:00+00:00'
        },
        {
            'event_id': '2',
            'product_id': str(uuid4()),
            'granules': [],
            'status_code': 'PENDING',
            'processing_date': '2020-01-01T00:00:00+00:00'
        },
        {
            'event_id': '3',
            'product_id': str(uuid4()),
            'granules': [],
            'status_code': 'RUNNING',
            'processing_date': '2020-01-01T00:00:00+00:00'
        },
    ]
    for product in mock_products:
        tables.product_table.put_item(Item=product)

    products = harvest_products.get_products()

    assert products == mock_products
