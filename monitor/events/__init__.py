import os
import datetime
from dcplib.aws.clients import cloudwatch  # noqa

event_types = ['CREATE', 'TOMBSTONE', 'DELETE']


def putMetrics(namespace: str, metric_name: str, dimensions: dict, value, timestamp=datetime.datetime.utcnow()):
    """ Adds metric to aws cloudwatch metrics using namespace"""
    assert dimensions is not None
    payload = {
        "Namespace": namespace,
        "MetricData": [{
            "MetricName": metric_name,
            "Dimensions": [dimensions],
            "Timestamp": timestamp,
            "Value": value,
            "Unit": "Count"
        }]
    }
    cloudwatch.put_metric_data(**payload)

class aws_cloudwatch_metric:
    def __init__(self, dss_notification):
        self.event_type = dss_notification.get("event_type")
        self.stage = dss_notification.get('dss_api').split('.')[1]
        self.namespace = f'dss-{self.stage}'.upper() # this was already established in DCP-Monitor
        self.metric_name = 'bundles'
        self.dimensions =  {"Name": "operation",
                            "Value": dss_notification["event_type"]}
        self.value = float(1)
        self.timestamp = datetime.datetime.strptime(dss_notification.get('event_timestamp'),"%Y-%m-%dT%H%M%S.%fZ")

    def upload_to_cloudwatch(self):
        return putMetrics(namespace=self.namespace,
                          metric_name=self.metric_name,
                          timestamp=self.timestamp,
                          dimensions=self.dimensions,
                          value=self.value)

