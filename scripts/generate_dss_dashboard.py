#!/usr/bin/env python

import json
import argparse
import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from monitor.external_export.graphana import LambdaMetrics, BundleMetrics, BucketMetrics,\
    DCPMetricsDash, format_panel_positioning, load_template_file



def build_dss_dashboard():
    invocation_lambda_metrics = LambdaMetrics()
    duration_lambda_metrics = LambdaMetrics()
    bundle_metrics = BundleMetrics()
    bucket_metrics = BucketMetrics()
    dcp_metrics = DCPMetricsDash()
    invocations = invocation_lambda_metrics.build_panel(metric_name="Invocations",
                                                        filepath=
                                                        invocation_lambda_metrics.lambda_panel_template_path,
                                                        gridPos={"h": 9, "w": 24, "x": 0, "y": 48},
                                                        panel_id=next(dcp_metrics.unused_id),
                                                        panel_title="Lambda Invocations")

    durations = duration_lambda_metrics.build_panel(metric_name="Duration",
                                                    filepath=duration_lambda_metrics.lambda_panel_template_path,
                                                    gridPos={"h": 9, "w": 24, "x": 0, "y": 57},
                                                    panel_id=next(dcp_metrics.unused_id),
                                                    panel_title="Lambda Durations")

    bundle_metrics = bundle_metrics.build_panel(metric_name='bundles',
                                                filepath=bundle_metrics.bundle_panel_template_path,
                                                gridPos={"h": 8, "w": 10, "x": 14, "y": 0},
                                                panel_id=next(dcp_metrics.unused_id),
                                                panel_title='Bundle Events')

    bucket_metrics = bucket_metrics.build_panel(metric_name="BucketSizeBytes",
                                                filepath=bucket_metrics.bucket_panel_template_path,
                                                gridPos={"h": 8, "w": 9, "x": 5, "y": 0},
                                                panel_id=next(dcp_metrics.unused_id),
                                                panel_title="Bucket Info")
    dcp_metrics_dash = dcp_metrics.get_current_dashboard()

    # Either Replace panel, where panel.Title == our panel Title, or just inject if its missing
    for inject_panel in [invocations, durations, bundle_metrics, bucket_metrics]:
        found = False
        for idx, panel in enumerate(dcp_metrics_dash["panels"]):
            if panel["title"] == inject_panel["title"]:
                dcp_metrics_dash['panels'][idx] = inject_panel
                found = True
                break
        if not found:
            dcp_metrics_dash['panels'].append(inject_panel)
    return dcp_metrics_dash


parser = argparse.ArgumentParser()


parser.add_argument("--position-dashboard", help="provide a source dashboard for positioning panels")
parser.add_argument('--print',help='Prints dashboard to screen', action='store_true')
parser.add_argument('--tf',help='saves dashboard to terraform file', action='store_true')



args = parser.parse_args()

if __name__ == '__main__':

    dcp_metrics_dash = build_dss_dashboard()
    if args.position_dashboard:
        dashboard_src = load_template_file(args.position_dashboard)
        dcp_metrics_dash = format_panel_positioning(dashboard_src, dcp_metrics_dash)
    if args.print:
        print(json.dumps(dcp_metrics_dash, indent=4))
    if args.tf:
        dcp_manager = DCPMetricsDash()
        outfile_name = 'dss-dashboard.tf'
        dcp_metrics_dash = dcp_manager.format_tf_templates(dcp_metrics_dash)
        with open(outfile_name, 'w') as outfile:
            outfile.write(dcp_metrics_dash)
        print(f'wrote dashboard to {outfile_name}\n')