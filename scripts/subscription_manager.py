#!/usr/bin/env python

import hca
import os
import argparse
import boto3
import json


def _get_dss_client(stage:str):
    if stage == "prod":
        dss_client = hca.dss.DSSClient(swagger_url="https://dss.data.humancellatlas.org/v1/swagger.json")
    else:
        dss_client = hca.dss.DSSClient(swagger_url=f"https://dss.{stage}.data.humancellatlas.org/v1/swagger.json")
    return dss_client

def list_subscriptions(replica:str):
    return dss_client.get_subscriptions(replica=replica,subscription_type='jmespath').get('subscriptions')

def delete_subscription(replica:str, uuid:str):
    return dss_client.delete_subscription(replica=replica, uuid=uuid)

def create_subscription(replica:str, event_type:str, url:str):
    return dss_client.put_subscription(replica=replica,jmespath_query=event_type,callback_url=url)

def get_api_gateway(gateway_name: str):

    rest_apis = apigateway_client.get_rest_apis(limit=500).get("items")
    for api in rest_apis:
        if api['name'] == gateway_name:
            return api
            break
    return None

parser = argparse.ArgumentParser()
parser.add_argument("--list", help="lists out all subscriptions", action='store_true')
parser.add_argument("--resubscribe", help="create all new subscriptions", action='store_true')
parser.add_argument("--stage",default=os.getenv('DSS_DEPLOYMENT_STAGE'),
                    choices=['dev','integration','staging','prod'],
                    help="pass stage for override, default to env",
                    nargs=1,
                    type=str)
parser.add_argument("--replica", help="specify replica",
                    nargs=1,
                    choices=['aws','gcp'],
                    required=True,
                    type=str)

args = parser.parse_args()


bundle_event_types = ['TOMBSTONE','DELETE','CREATE']
# TODO figure out if stage can be removed from chalice lambda deployment
lambda_name = f'{os.getenv("CHALICE_APP_NAME")}-dev'
dss_client = _get_dss_client(args.stage)
region = os.getenv('AWS_DEFAULT_REGION')
apigateway_client = boto3.client('apigateway')
api_data = get_api_gateway(lambda_name)

if api_data is not None:
    invoke_url = f'https://{api_data.get("id")}.execute-api.{region}.amazonaws.com/dev/notifications'
    msg = f'Found Lambda {api_data.get("name")} \n url: {invoke_url}'

    if args.list:
        print(json.dumps(list_subscriptions(replica=args.replica),indent=4))

    elif args.resubscribe:
        subscriptions = list_subscriptions(args.replica)
        for sub in subscriptions:
            uuid = sub.get('uuid')
            print(delete_subscription(replica=args.replica, uuid=uuid))
        for event_type in bundle_event_types:
            new_sub = create_subscription(replica=args.replica,event_type=event_type,url=invoke_url)
            print(json.dumps(new_sub,indent=4))
else:
    print(f"error unable to locate lambda: {lambda_name}")

