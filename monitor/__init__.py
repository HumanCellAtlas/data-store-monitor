#! /usr/bin/env python

import os
import boto3
import datetime
import json
import requests
import collections


chalice_app_name = os.getenv("CHALICE_APP_NAME")

cloudwatch = boto3.client('cloudwatch')
resourcegroupstaggingapi = boto3.client('resourcegroupstaggingapi')
secretsmanager = boto3.client('secretsmanager')
logsmanager = boto3.client('logs')

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
    period = 43200
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
    temp_sum = 0.0
    if len(response['Datapoints']) is not 0:
        for x in response['Datapoints']:
            temp_sum += x['Sum']
        return temp_sum
    return 0.0


def format_lambda_results_for_slack(start_time: datetime, end_time: datetime, results: dict):
    # Formats json lambda data into something that can be presented in slack
    header = '\n {} : {} -> {} | \n  Lambda Name | Invocations | Duration (seconds) \n'
    bucket_header = '\n Bucket | BytesUploaded | BytesDownloaded \n'
    bundle_header = '\n Bundles | {} CREATE | {} TOMBSTONE | {} DELETE \n'
    payload = []
    for stage, infra in results.items():
        temp_results_lambdas = [header.format(stage, start_time, end_time)]
        temp_results_buckets = [bucket_header]
        temp_results_bundles = []
        for k, v in infra.items():
            if 'lambdas' in k:
                for ln, val in v.items():
                    temp_results_lambdas.append(f'\n\t | {ln} | {val["Invocations"]} | {val["Duration"]/1000} ')
            elif 'buckets' in k:
                for bn, val in v.items():
                    temp_results_buckets.append(f'\n\t | {bn} | {format_data_size(val["BytesUploaded"])}, | '
                                                f'{format_data_size(val["BytesDownloaded"])}')
            elif 'bundles' in k:
                temp_results_bundles.append(bundle_header.format(v["CREATE"], v["TOMBSTONE"], v["DELETE"]))
        payload.append(''.join(temp_results_lambdas+temp_results_buckets+temp_results_bundles))

    return ''.join(payload)


def send_slack_post(start_time, end_time, webhook: str, stages: dict):
    payload = {"text": f"{format_lambda_results_for_slack(start_time, end_time, stages)}"}
    res = requests.post(webhook, json=payload, headers={'Content-Type': 'application/json'})
    if res.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (res.status_code, res.text)
        )


def format_data_size(value: int):
    base = 1024
    value = float(value)
    suffix = ('kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    if value < base:
        return '%d Bytes' % value
    for i, s in enumerate(suffix):
        unit = base ** (i + 2)
        if value < unit:
            return f'{round((base * value / unit),2)} {s}'


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
        paginator = logsmanager.get_paginator('filter_log_events')
        epoch = datetime.datetime.utcfromtimestamp(0)
        events = []

        kwargs = {'endTime': int((end_time - epoch).total_seconds()*1000),
                  'startTime': int((start_time - epoch).total_seconds()*1000),
                  'logGroupName': group_name, 'filterPattern': filter_pattern, 'interleaved': True,
                  'logStreamNamePrefix': log_stream_prefix}
        for page in paginator.paginate(**kwargs):
            if len(page["events"]) > 0:
                for x in page["events"]:
                    index = x['message'].find('{')
                    x = json.loads(x['message'][index:])
                    events.append(x)

        return events


def run(webhook: bool = None):
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
        stage_lambdas = {i: collections.defaultdict(collections.defaultdict) for i in get_lambda_names(stage)}
        for ln in stage_lambdas.keys():
            for lambda_metric in lambda_query_metric_names:
                lambda_res = cloudwatch.get_metric_statistics(**get_cloudwatch_metric_stat(aws_start_time,
                                                                                           aws_end_time,
                                                                                           'AWS/Lambda',
                                                                                           lambda_metric,
                                                                                           ['Sum'],
                                                                                           [{"Name": "FunctionName",
                                                                                             "Value": ln}]))
                stage_lambdas[ln][lambda_metric] = int(summation_from_datapoints_response(lambda_res))
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
    if webhook:
        send_slack_post(aws_start_time, aws_end_time, get_webhook_ssm(), stages)


if __name__ == '__main__':
    run()
