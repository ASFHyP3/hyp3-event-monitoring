from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import Flask, abort, jsonify
from flask.json import JSONEncoder
from flask_api.status import HTTP_404_NOT_FOUND
from flask_cors import CORS
from serverless_wsgi import handle_request

import database


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
    events = database.get_events()
    return jsonify(events)


@app.route('/events/<event_id>')
def get_event_by_id(event_id):
    try:
        event = database.get_event(event_id)
    except ValueError:
        abort(HTTP_404_NOT_FOUND)
    event['products'] = database.get_products_for_event(event_id, status_code='SUCCEEDED')
    return jsonify(event)


@app.route('/recent_products')
def get_recent_products():
    processed_since = (datetime.now(tz=timezone.utc) - timedelta(days=7))
    recent_products = database.get_products_by_status('SUCCEEDED', processed_since=processed_since)
    return jsonify(recent_products)


def lambda_handler(event, context):
    return handle_request(app, event, context)
