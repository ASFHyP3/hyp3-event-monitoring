from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import Flask, abort, jsonify
from flask.json import JSONEncoder
from flask_api.status import HTTP_404_NOT_FOUND
from flask_cors import CORS
from serverless_wsgi import handle_request

from models import models


class DecimalEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o == int(o):
                return int(o)
            return float(o)
        return super(DecimalEncoder, self).default(o)


app = Flask(__name__)
CORS(app)
app.json_encoder = DecimalEncoder


@app.route('/events')
def get_events():
    events = models.get_events()
    return jsonify([event.to_dict() for event in events])


@app.route('/events/<event_id>')
def get_event_by_id(event_id):
    try:
        event = models.get_event(event_id)
    except ValueError:
        abort(HTTP_404_NOT_FOUND)
    products = models.get_products_for_event(event_id, status_code='SUCCEEDED')
    event_dict = event.to_dict()
    event_dict['products'] = [product.to_dict() for product in products]
    return jsonify(event_dict)


@app.route('/recent_products')
def get_recent_products():
    processed_since = datetime.now(tz=timezone.utc) - timedelta(days=7)
    recent_products = models.get_products_by_status('SUCCEEDED', processed_since=processed_since)
    return jsonify([product.to_dict() for product in recent_products])


def lambda_handler(event, context):
    return handle_request(app, event, context)
