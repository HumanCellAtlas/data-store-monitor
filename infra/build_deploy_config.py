#!/usr/bin/env python

import os
import glob
import json
import boto3
import argparse
from google.cloud.storage import Client
GCP_PROJECT_ID = Client().project

infra_root = os.path.abspath(os.path.dirname(__file__))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("component")
args = parser.parse_args()


terraform_variable_template = """
variable "{name}" {{
  default = "{val}"
}}
"""

terraform_backend_template = """# Auto-generated during infra build process.
# Please edit infra/build_deploy_config.py directly.
terraform {{
  backend "s3" {{
    bucket = "{bucket}"
    key = "dss-monitor/{comp}-{stage}.tfstate"
    region = "{region}"
    {profile_setting}
  }}
}}
"""

terraform_providers_template = """# Auto-generated during infra build process.
# Please edit infra/build_deploy_config.py directly.
provider aws {{
  region = "{aws_region}"
}}

provider google {{
  project = "{gcp_project_id}"
}}
"""

env_vars_to_infra = [
    "AWS_DEFAULT_REGION",
    "DSS_INFRA_TAG_PROJECT",
    "DSS_INFRA_TAG_SERVICE",
    "DSS_INFRA_TAG_STAGE",
    "DSS_INFRA_TAG_OWNER",
    "DSS_MONITOR_WEBHOOK_SECRET_NAME",
    "DSS_MONITOR_EVENT_BUCKET",
    "DSS_MON_GCP_SERVICE_ACCOUNT_NAME",
    "GCP_DEFAULT_REGION"
]

with open(os.path.join(infra_root, args.component, "backend.tf"), "w") as fp:
    caller_info = boto3.client("sts").get_caller_identity()
    if os.environ.get('AWS_PROFILE'):
        profile = os.environ['AWS_PROFILE']
        profile_setting = f'profile = "{profile}"'
    else:
        profile_setting = ''
    fp.write(terraform_backend_template.format(
        bucket=os.environ['DSS_MON_TERRAFORM_BACKEND_BUCKET_TEMPLATE'].format(account_id=caller_info['Account']),
        comp=args.component,
        stage=os.environ['DSS_INFRA_TAG_STAGE'],
        region=os.environ['AWS_DEFAULT_REGION'],
        profile_setting=profile_setting,
    ))

with open(os.path.join(infra_root, args.component, "variables.tf"), "w") as fp:
    fp.write("# Auto-generated during infra build process." + os.linesep)
    fp.write("# Please edit infra/build_deploy_config.py directly." + os.linesep)
    for key in env_vars_to_infra:
        val = os.environ[key]
        fp.write(terraform_variable_template.format(name=key, val=val))

with open(os.path.join(infra_root, args.component, "providers.tf"), "w") as fp:
    fp.write(terraform_providers_template.format(
        aws_region=os.environ['AWS_DEFAULT_REGION'],
        gcp_project_id=GCP_PROJECT_ID,
    ))
