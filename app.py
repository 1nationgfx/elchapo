import logging

import requests
from flask import Flask, redirect, jsonify
from flask import request

from constants import WEBHOOK, NOT_FOUND_URL
from models import ShortURL
from zappa.asynchronous import task

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

MAIN = False

app = Flask(__name__, static_url_path='/no_static')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/c', methods=['POST'])
def create_url():
    path = request.json['path']
    redirect_url = request.json['redirect_url']
    webhook = request.json.get('webhook', None)
    ShortURL(url=path, redirection_url=redirect_url, webhook=webhook).save()
    return jsonify(success=True), 200


@task
def call_url(url):
    if url:
        retry = 3
        while retry > 0:
            x = requests.get(url)
            if x.status_code >= 400:
                retry = retry - 1
            else:
                return x.text


def get_hook(webhook, path):
    if webhook:
        if webhook.__contains__('?'):
            webhook + '&path=%s' % path
        else:
            webhook + '?path=%s' % path
    return webhook


@app.route('/<path:path>', methods=['GET'])
def redirect_url(path):
    try:
        sort = ShortURL.get(path)
        sort.is_clicked = True
        webhook = WEBHOOK
        if sort.webhook:
            webhook = sort.webhook
        webhook = get_hook(webhook, path)
        if webhook:
            call_url(webhook)
        return redirect(sort.redirection_url, code=302)
    except ShortURL.DoesNotExist:
        return redirect(NOT_FOUND_URL, code=302)


# We only need this for local development.
if __name__ == '__main__':
    MAIN = True
    app.run(host='0.0.0.0', port=5601)
