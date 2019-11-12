import logging
import chalice
import os
import sys
import json

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chalicelib'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import monitor


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

stage = os.getenv('DSS_INFRA_TAG_STAGE')
app = chalice.Chalice(app_name=f"dss-monitor-{stage}")
app.log.setLevel(logging.DEBUG)


@app.route('/', methods=['GET'])
def index():
    logger.info(dict(status='ok'))
    return chalice.Response(body='ok',
                            headers={"Content-Type": "text/plain"},
                            status_code=200)


@app.route('/notifications', methods=['POST'])
def notification():
    notification_event = app.current_request.json_body  # todo verify HMAC key
    logger.info(json.dumps(dict(stage=stage, event=notification_event)))
    return chalice.Response(body='ok',
                            headers={"Content-Type": "text/plain"},
                            status_code=200)


@app.schedule("cron(0 17 ? * MON-FRI *)")
def daemon_run(event):
    monitor.run(webhook=True)
