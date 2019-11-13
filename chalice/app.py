import logging
import chalice
import os
import sys
import json

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chalicelib'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import monitor
from monitor import events


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = chalice.Chalice(app_name=f"dss-monitor")
app.log.setLevel(logging.DEBUG)


@app.route('/', methods=['GET'])
def index():
    logger.info(dict(status='OK'))
    return chalice.Response(body='OK',
                            headers={"Content-Type": "text/plain"},
                            status_code=200)

@app.route('/notifications', methods=['POST'])
def notification():
    notification_event = app.current_request.json_body  # todo verify HMAC key
    stage = notification_event.get('dss_api').split('.')[1]
    logger.info(json.dumps(dict(stage=stage, event=notification_event)))
    event = events.aws_cloudwatch_metric(dss_notification=notification_event)
    event.upload_to_cloudwatch()
    return chalice.Response(body='ok',
                            headers={"Content-Type": "text/plain"},
                            status_code=200)

@app.schedule("cron(0 17 ? * MON-FRI *)")
def daemon_run(event):
    monitor.run(webhook=True)
