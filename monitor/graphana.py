#!/usr/bin/env python
import json
import os
import requests
import string
from itertools import cycle


from monitor import get_lambda_names


mon_home = os.getenv('DSS_MON_HOME')
bundle_panel_template_path = mon_home+'/templates/graphana/bucket_panel_template.json'


def load_template_file(template_path: str):
    """Loads JSON template to dict."""
    with open(template_path) as file:
        data = json.load(file)
    return data


class DCPMetricsDash:
    def __init__(self):
        self.current_dashboard = self.get_current_dashboard()

    def get_current_dashboard(self):
        dcp_monitor_dashboard_url = 'https://raw.githubusercontent.com/HumanCellAtlas/dcp-monitoring/master/terraform/'\
                            'modules/env-dashboards/dss-dashboard.tf'
        resp = requests.get(url=dcp_monitor_dashboard_url)
        return json.loads(resp.text.split('EOF')[1])


class LambdaMetrics:
    def __init__(self):

        self.lambda_names = self._get_stripped_lambda_names()
        self.lambda_panel_template_path = mon_home+'/templates/graphana/lambda_panel_template.json'
        self.refid = self.get_refid()

    def get_refid(self):
        alpha_chars = [char for char in string.ascii_uppercase]
        for char in cycle(alpha_chars):
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

    def _build_lambda_targets(self, metric_name:str):
        targets = [self._get_formatted_graphana_target(lambda_name=f'{lambda_name}'+'-${var.env}',
                                                       metric_name=metric_name)
                   for lambda_name in self.lambda_names]
        return targets

    def build_lambda_panel(self, metric_name: str):
        panel_template = load_template_file(bundle_panel_template_path)
        targets = self._build_lambda_targets(metric_name)
        for target in targets:
            panel_template['targets'].append(target)
        panel_template["Title"] = f'Lambda {metric_name}'
        return panel_template

class BundleMetrics:
    def __init__(self):
        self.refid = self.get_refid()

    def get_refid(self):
        alpha_chars = [char for char in string.ascii_uppercase]
        for char in cycle(alpha_chars):
            yield char

    def _get_formatted_graphana_target(self, event_type: str, metric_name: str, namespace: str):
        target_template = {
            "alias": event_type,
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
            "statistics": [
                "Sum"
            ]

        }
        return target_template

    def _build_bundle_targets(self):
        """ Builds out bundle targets for consumption into terraform"""
        event_types = ["CREATE", "TOMBSTONE", "DELETE"]
        targets = [self._get_formatted_graphana_target(event_type=event,
                                                       metric_name='bundles',
                                                       namespace='${DSS-${var.env}')
                   for event in event_types]
        return targets

    def build_bundle_panel(self) -> json:
        panel_template = load_template_file(bundle_panel_template_path)
        targets = self._build_bundle_targets()
        for target in targets:
            panel_template['targets'].append(target)
        return panel_template



if __name__ == '__main__':
    invocation_lambda_metrics = LambdaMetrics()
    duration_lambda_metrics = LambdaMetrics()
    invocations = invocation_lambda_metrics.build_lambda_panel(metric_name="Invocations")
    durations = duration_lambda_metrics.build_lambda_panel(metric_name="Duration")
    bundle_metrics = BundleMetrics().build_bundle_panel()
    dcp_metrics_dash = DCPMetricsDash().get_current_dashboard()

    # Either Replace panel, where panel.Title == our panel Title, or just inject if its missing
    for inject_panel in [invocations,durations,bundle_metrics]:
        for idx, panel in enumerate(dcp_metrics_dash["panels"]):
            if panel["title"] == inject_panel["title"]:
                dcp_metrics_dash['panels'][idx] = inject_panel
                break
        dcp_metrics_dash['panels'].append(inject_panel)

    print(json.dumps(dcp_metrics_dash, indent=4))