import logging
import chalice
from requests_http_signature import HTTPSignatureAuth


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = chalice.Chalice(app_name="dss-monitor")


@app.route('/', methods=['GET'])
def index():
    return chalice.Response(body='OK',
                            headers={"Content-Type": "text/plain"},
                            status_code=200)


@app.route('/notification/{stage}', methods=['POST'])
def notification(stage):
    notification_event = app.current_request.json_body ## todo verify HMAC key
    logger.info(dict(stage=stage, event=notification_event))
    return chalice.Response(status_code=200)
