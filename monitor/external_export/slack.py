import datetime
import requests


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