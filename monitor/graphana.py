import json
import copy
import monitor
import os
import uuid

mon_home = os.getenv('DSS_MON_HOME')
panel_template_path = mon_home+'/templates/graphana/panel_template.json'

lambda_names = monitor.get_lambda_names()
graphana_lambda_duration_template = json.loads(' {"alias": "{{FunctionName}}", "dimensions": { "FunctionName": "" },'
                                               ' "expression": "", "highResolution": true, "id": "", "metricName":'
                                               ' "Duration", "namespace": "AWS/Lambda", "period": "",'
                                               ' "refId": "", "region": "us-east-1","returnData": false,'
                                               ' "statistics": [ "Sum" ] }')


graphana_lambda_invocation_template = json.loads(' {"alias": "{{FunctionName}}", "dimensions": { "FunctionName": "" },'
                                                 ' "expression": "", "highResolution": true, "id": "", "metricName":'
                                                 ' "Invocations", "namespace": "AWS/Lambda", "period": "",'
                                                 ' "refId": "", "region": "us-east-1","returnData": false,'
                                                 ' "statistics": [ "Sum" ] }')


def generate_array_lambda_targets(template: json):
    filled = list()
    for l in lambda_names:
        temp = copy.deepcopy(template)
        temp['dimensions']['FunctionName'] = l
        temp['refId'] = l
        filled.append(temp)
    return filled


def load_tempalte_file(template_path: str):
    """Loads JSON template to dict."""
    with open(template_path) as file:
        data = json.load(file)
    return data


def generate_templates(print_json=None):
    duration_targets = generate_array_lambda_targets(graphana_lambda_duration_template)
    invocation_targets = generate_array_lambda_targets(graphana_lambda_invocation_template)

    panel_template = load_tempalte_file(panel_template_path)
    duration_panel = copy.deepcopy(panel_template)
    invocation_panel = copy.deepcopy(panel_template)

    duration_panel['targets'] = duration_targets
    invocation_panel['targets'] = invocation_targets

    if print_json:
        print(f'graphana panels for : {os.getenv("DSS_INFRA_TAG_STAGE")}')
        print('These need to be injected into the graphana dashboard')
        print(json.dumps(duration_panel, indent=4) + ', \n' +json.dumps(invocation_panel, indent=4))


if __name__ == '__main__':
    generate_templates(print_json=True)
