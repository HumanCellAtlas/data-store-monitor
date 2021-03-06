#!/usr/bin/env python
import json
import os
import requests
import string
import argparse

from monitor import get_lambda_names


mon_home = os.getenv('DSS_MON_HOME')

def load_template_file(template_path: str):
    """Loads JSON template to dict."""
    with open(template_path) as file:
        data = json.load(file)
    return data

def format_panel_positioning(dashboard_src:dict, dashboard_dst: dict):
    '''Use the dashboard_src to position panels correctly on the dashboard_dest'''
    for panel in dashboard_dst['panels']:
        hit = False
        for source_panel in dashboard_src.get("panels"):
            if panel['title'] == source_panel['title']:
                panel["gridPos"] = source_panel['gridPos']
                hit = True
                break
        if not hit:
            print(f"Unable to locate source panel with title: {panel['title']}")
    return dashboard_dst

class DCPMetricsDash:
    def __init__(self):
        self.dcp_monitor_dashboard_url = 'https://raw.githubusercontent.com/HumanCellAtlas/dcp-monitoring/' \
                                         'master/terraform/modules/env-dashboards/dss-dashboard.tf'
        self.current_dashboard = self.get_current_dashboard()
        self.unused_id = self.get_unused_panel_id()

    def get_unused_panel_id(self):
        ids = [ x for x in range(100) if x not in self.get_used_panel_ids() ]
        for id in ids:
            yield id

    def get_used_panel_ids(self):
        return [panel['id'] for panel in self.current_dashboard['panels']]

    def get_current_dashboard(self):
        """returns the terraform managed dashboard for the DSS"""
        resp = requests.get(url=self.dcp_monitor_dashboard_url)
        return json.loads(resp.text.split('EOF')[1])

    def format_tf_templates(self, new_dashboard:dict ):
        dashboard = json.dumps(new_dashboard,indent=4)
        intro = 'locals {\n  dss_dashboard = <<EOF\n'
        tail = '\nEOF\n}\n'
        return f'{intro}{dashboard}{tail}'

class DSSMetrics:
    def __init__(self):
        self.refid = self.get_refid()

    def get_refid(self):
        for char in string.ascii_uppercase:
            yield char

    def build_panel(self,filepath: str, metric_name: str, gridPos:dict, panel_id:int, panel_title: str):
        panel_template = load_template_file(filepath)
        targets = self._build_targets(metric_name)
        for target in targets:
            panel_template['targets'].append(target)
        panel_template["title"] = panel_title
        panel_template["gridPos"] = gridPos
        panel_template['id'] = panel_id
        return panel_template

class LambdaMetrics(DSSMetrics):
    def __init__(self):

        self.lambda_names = self._get_stripped_lambda_names()
        self.lambda_panel_template_path = mon_home+'/templates/graphana/lambda_panel_template.json'
        self.refid = self.get_refid()

    def get_refid(self):
        for char in string.ascii_uppercase:
            yield char

    def _get_stripped_lambda_names(self):
        # we have to strip out the stage name from the lambda names, so TF can populate them
        stage='dev'
        lambda_names = get_lambda_names(stage=stage)
        return [ln.split(f'-{stage}')[0] for ln in lambda_names]

    def _get_formatted_graphana_target(self, lambda_name: str, metric_name: str):
        base_graphana_lambda_target = {"refId":  f'{next(self.refid)}',
                                       "namespace": "AWS/Lambda",
                                       "metricName": metric_name, # Duration Invocation
                                       "statistics": [
                                         "Sum"
                                       ],
                                       "dimensions": {
                                         "FunctionName": lambda_name
                                       },
                                       "period": "",
                                       "region": "default",
                                       "id": "",
                                       "expression": "",
                                       "returnData": False,
                                       "highResolution": False,
                                       "alias": lambda_name}
        return base_graphana_lambda_target

    def _build_targets(self, metric_name:str):
        targets = [self._get_formatted_graphana_target(lambda_name=f'{lambda_name}'+'-${var.env}',
                                                       metric_name=metric_name)
                   for lambda_name in self.lambda_names]
        return targets


class BundleMetrics(DSSMetrics):
    bundle_panel_template_path = mon_home+'/templates/graphana/bundle_panel_template.json'

    def _get_formatted_graphana_target(self, event_type: str, metric_name: str, namespace: str):
        target_template = {"alias": event_type,
                           "dimensions": {
                               "operation": event_type
                           },
                           "expression": "",
                           "highResolution": False,
                           "id": "",
                           "metricName": metric_name,
                           "namespace": namespace,
                           "period": "",
                           "refId": f'{next(self.refid)}',
                           "region": "us-east-1",
                           "returnData": False,
                           "statistics": ["Sum"]
                           }
        return target_template

    def _build_targets(self, metric_name):
        """ Builds out bundle targets for consumption into terraform"""
        event_types = ["CREATE", "TOMBSTONE", "DELETE"]
        targets = [self._get_formatted_graphana_target(event_type=event,
                                                       metric_name=metric_name,
                                                       namespace='DSS-${upper(var.env)}')
                   for event in event_types]
        return targets


class BucketMetrics(DSSMetrics):
    bucket_panel_template_path = mon_home+"/templates/graphana/bucket_panel_template.json"

    def _get_formatted_graphana_target(self,bucket_name, bucket_type,metric_name):
        target_template = {
            "refId": f'{next(self.refid)}',
            "namespace": "AWS/S3",
            "metricName": metric_name,
            "statistics": ["Sum"],
            "dimensions": {
                "StorageType": "StandardStorage",
                "BucketName": bucket_name
            },
            "period": "86400",
            "region": "default",
            "id": "",
            "expression": "",
            "returnData": False,
            "highResolution": False,
            "alias": bucket_type
        }
        return target_template

    def _build_targets(self, metric_name):
        buckets = [("${local.dss_primary_bucket[local.env]}","Primary Bucket"),
                   ("${local.dss_checkout_bucket[local.env]}","Checkout Bucket")]
        targets = [self._get_formatted_graphana_target(bucket_name,bucket_type,metric_name) for bucket_name, bucket_type in buckets]
        return targets