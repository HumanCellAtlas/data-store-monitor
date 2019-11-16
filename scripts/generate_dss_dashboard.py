#!/usr/bin/env python

import json
import argparse
import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from monitor.graphana import LambdaMetrics, BundleMetrics,DCPMetricsDash,format_panel_positioning, load_template_file



def build_dss_dashboard():
    invocation_lambda_metrics = LambdaMetrics()
    duration_lambda_metrics = LambdaMetrics()
    bundle_metrics = BundleMetrics()
    dcp_metrics = DCPMetricsDash()
    invocations = invocation_lambda_metrics.build_panel(metric_name="Invocations",
                                                        filepath=
                                                        invocation_lambda_metrics.lambda_panel_template_path,
                                                        gridPos={"h": 8, "w": 12, "x": 0, "y": 40},
                                                        id=next(dcp_metrics.unused_id),
                                                        panel_title="Lambda Invocations")

    durations = duration_lambda_metrics.build_panel(metric_name="Duration",
                                                    filepath=duration_lambda_metrics.lambda_panel_template_path,
                                                    gridPos={"h": 8, "w": 12, "x": 12, "y": 40},
                                                    id=next(dcp_metrics.unused_id),
                                                    panel_title="Lambda Durations")

    bundle_metrics = bundle_metrics.build_panel(metric_name='bundles',
                                                filepath=bundle_metrics.bundle_panel_template_path,
                                                gridPos={"h": 8, "w": 12, "x": 0, "y": 48},
                                                id=next(dcp_metrics.unused_id),
                                                panel_title='Bundle Events')
    dcp_metrics_dash = dcp_metrics.get_current_dashboard()

    # Either Replace panel, where panel.Title == our panel Title, or just inject if its missing
    for inject_panel in [invocations, durations, bundle_metrics]:
        for idx, panel in enumerate(dcp_metrics_dash["panels"]):
            if panel["title"] == inject_panel["title"]:
                dcp_metrics_dash['panels'][idx] = inject_panel
                break
        dcp_metrics_dash['panels'].append(inject_panel)

    return dcp_metrics_dash


parser = argparse.ArgumentParser()


parser.add_argument("--position", help="Replaces gid positions with into a templated dashboard", action='store_true')
parser.add_argument("--dashboard",help='Builds out dashboard', action='store_true')
parser.add_argument('--print',help='Prints dashboard to screen', action='store_true')
parser.add_argument('--tf',help='saves dashboard to terraform file', action='store_true')



args = parser.parse_args()

if __name__ == '__main__':
    if args.dashboard:
        dcp_metrics_dash = build_dss_dashboard()
    elif args.position:
        dashboard_src =  load_template_file(args[2])
        dashboard_dst = load_template_file(args[3])
        dcp_metrics_dash = format_panel_positioning(dashboard_src, dashboard_dst)
    if args.print:
        print(json.dumps(dcp_metrics_dash, indent=4))