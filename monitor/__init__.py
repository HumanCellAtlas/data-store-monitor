#! /usr/bin/env python

import os
import boto3
import datetime
import json
import requests
import collections

from dcplib.aws.clients import cloudwatch, resourcegroupstaggingapi, secretsmanager, logs # typing: ignore
from monitor.external_export import time_ms_after_epoch
from monitor.external_export.slack import send_slack_post

chalice_app_name = os.getenv("CHALICE_APP_NAME")

def get_webhook_ssm(secret_name=None):
    #  fetch webhook url from Secrets Store.
    stage = os.environ['DSS_INFRA_TAG_STAGE']
    secrets_store = os.environ['DSS_MON_SECRETS_STORE']
    if secret_name is None:
        secret_name = 'monitor-webhook'
    secret_id = f'{secrets_store}/{stage}/{secret_name}'
    res = secretsmanager.get_secret_value(SecretId=secret_id)
    return res['SecretString']


def get_dss_resource(resource_string: str, tag_filter: list):
    dss_resources = resourcegroupstaggingapi.get_resources(ResourceTypeFilters=[resource_string],
                                                           TagFilters=tag_filter)
    return dss_resources


def get_lambda_names(stage=None):
    # Returns all the names for deployed lambdas
    if stage is None:
        stage = os.getenv('DSS_INFRA_TAG_STAGE')
    service_tags = [{"Key": "service", "Values": ["dss"]}, {"Key": "env", "Values": [stage]}]
    resource_list = get_dss_resource(resource_string='lambda:function', tag_filter=service_tags)
    lambda_names = [x['ResourceARN'].rsplit(':', 1)[1] for x in resource_list['ResourceTagMappingList'] if
                    stage in x['ResourceARN']]
    return sorted(lambda_names)


def get_cloudwatch_metric_stat(start_time: datetime, end_time: datetime, namespace: str, metric_name: str, stats: list,
                               dimensions):
    #  Returns a formatted MetricDataQuery that can be used with CloudWatch Metrics
    end_time = end_time
    start_time = start_time
    period = 12 * 60 * 60  # 12 hours
    if not stats:
        stats = ['Sum']
    return {"Namespace": namespace,
            "MetricName": metric_name,
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": period,
            "Statistics": stats,
            "Dimensions": dimensions}


def summation_from_datapoints_response(response):
    # Datapoints from CloudWatch queries may need to be summed due to how durations for time delta's are calculated.
    return sum([x['Sum'] for x in response['Datapoints']])


def search_cloudwatch_dates(start_time: datetime, end_time: datetime, group_name: str, filter_pattern: str):
    # this function is used to figure out what logstreams to look inside, if we dont do this, boto3 searches through all
    # log streams starting from the lambda initialization, this can lead to hitting limits for python recursion.
    log_stream_lookup = list()
    log_stream_lookup.append(f"{end_time.strftime('%Y/%m/%d')}/")
    log_stream_lookup.append(f"{(end_time - datetime.timedelta(days=1)).strftime('%Y/%m/%d')}/")
    events = list()
    for logs_stream_prefix in log_stream_lookup:
        new_events = get_cloudwatch_log_events(start_time, end_time, group_name, filter_pattern, logs_stream_prefix)
        events.extend(new_events)
    return events


def get_cloudwatch_log_events(start_time: datetime, end_time: datetime, group_name: str, filter_pattern: str,
                              log_stream_prefix: str):
        paginator = logs.get_paginator('filter_log_events')
        epoch = datetime.datetime.utcfromtimestamp(0)
        events = []

        kwargs = {'endTime': time_ms_after_epoch(end_time),
                  'startTime': time_ms_after_epoch(start_time),
                  'logGroupName': group_name, 'filterPattern': filter_pattern, 'interleaved': True,
                  'logStreamNamePrefix': log_stream_prefix}
        for page in paginator.paginate(**kwargs):
            if len(page["events"]) > 0:
                for x in page["events"]:
                    index = x['message'].find('{')
                    x = json.loads(x['message'][index:])
                    events.append(x)

        return events

def get_lambda_metrics(start_time:datetime, end_time:datetime, metric_names: list):
    stage_lambdas = {i: collections.defaultdict(collections.defaultdict) for i in get_lambda_names()}
    for ln in stage_lambdas.keys():
        for lambda_metric in metric_names:
            lambda_res = cloudwatch.get_metric_statistics(**get_cloudwatch_metric_stat(start_time,
                                                                                       end_time,
                                                                                       'AWS/Lambda',
                                                                                       lambda_metric,
                                                                                       ['Sum'],
                                                                                       [{"Name": "FunctionName",
                                                                                         "Value": ln}]))
            stage_lambdas[ln][lambda_metric] = int(summation_from_datapoints_response(lambda_res))
    return stage_lambdas

def run(push_to_webhook:bool = None, webhook: str = None):
    if os.environ["DSS_INFRA_TAG_STAGE"] is None:
        raise ValueError('Missing DSS_INFRA_TAG_STAGE, exiting....')
        exit(1)

    # variables
    aws_end_time = datetime.datetime.utcnow()
    aws_start_time = aws_end_time - datetime.timedelta(days=1)
    bucket_list = [os.environ['DSS_S3_BUCKET'], os.environ['DSS_S3_CHECKOUT_BUCKET']]
    bucket_query_metric_names = ['BytesDownloaded', 'BytesUploaded']
    lambda_query_metric_names = ['Duration', 'Invocations']
    notification_filter_type = ['DELETE', 'CREATE', 'TOMBSTONE']
    stages = {f'{os.environ["DSS_INFRA_TAG_STAGE"]}': collections.defaultdict(collections.defaultdict)}

    for stage in stages.keys():
        stage_lambdas = get_lambda_metrics(aws_start_time, aws_end_time, lambda_query_metric_names)
        stages[stage]['lambdas'].update(stage_lambdas)
        for bucket_name in bucket_list:
            #  Fetch Data for Buckets Data Consumption
            temp_dict = collections.defaultdict(int)
            for metric in bucket_query_metric_names:
                bucket_upload_res = cloudwatch.get_metric_statistics(**get_cloudwatch_metric_stat(aws_start_time,
                                                                                                  aws_end_time,
                                                                                                  'AWS/S3',
                                                                                                  metric,
                                                                                                  ['Sum'],
                                                                                                  [{"Name": "BucketName",
                                                                                                    "Value": bucket_name},
                                                                                                   {"Name": "FilterId",
                                                                                                    "Value": "EntireBucket"}]))
                temp_dict[metric] = int(summation_from_datapoints_response(bucket_upload_res))
            stages[stage]['buckets'].update({bucket_name: temp_dict})
        #
        api_temp_dict = dict.fromkeys(notification_filter_type, 0)
        events = search_cloudwatch_dates(aws_start_time,
                                         aws_end_time,
                                         f'/aws/lambda/{chalice_app_name}-{stage}',
                                         '{ ($.event.event_type = "CREATE" ) ||'
                                         '( ($.event.event_type = "DELETE")  ||'
                                         '  ($.event.event_type = "TOMBSTONE")) }')
        for x in events:
            api_temp_dict[x["event"]["event_type"]] += 1
        stages[stage]['bundles'].update(api_temp_dict)

    print(json.dumps(stages, indent=4, sort_keys=True))
    if push_to_webhook:
        if not webhook:
            webhook = get_webhook_ssm()
        send_slack_post(aws_start_time, aws_end_time, webhook, stages)


if __name__ == '__main__':
    run()
