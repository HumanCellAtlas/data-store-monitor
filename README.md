#  data-store-monitor

This is a monitoring plugin for the [DataStore](https://github.com/HumanCellAtlas/data-store)

## Stages:
Stage configuration files are stored in the (deployments)[deployments] directory.
Included in the deployments directory is a `config.json` that is used for the `dcp-cli` [hca](https://pypi.org/project/hca/) tool.
These configuration files have been altered to interface with different HCA-Data-Store Stages. 
To work a different stage, perform:
``` export DEPLOYMENT={STAGE} && source environment```

## Data-Store Authentication:
The DSS Monitor Service Identity is provided by a GCP Service account. This service account is used to authenticate to the data-store, in order
to perform actions on the /Subscriptions endpoint.
To create a service account use the commands:
```
make infra-apply-all
make infra-plan-all
```
Once the service account is created head over to [gcp-dashboard](https://console.developers.google.com/) and download the
`gcp_credentials.json` associated with the account created, this file needs to be placed inside the respected `${DSS_MON_HOME}/deployments/{stage}` folder.
Alternatively this short command can also be run:
```
gcloud iam service-accounts keys create ${DSS_MON_HOME}/deployments/${DSS_INFRA_TAG_STAGE}/gcp-credentials.json --iam-account ${DSS_MON_GCP_SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_NAME}.iam.gserviceaccount.com
```
See [infra/google-account](infra/google-account) for more information

## Secrets:

### Webhook
The DSS-Monitor can provide notifications for daily progress in a slack channel. Add a webhook url as follows
	`echo 'URL' | scripts/set_secret.py --secret-name $DSS_MONITOR_WEBHOOK_SECRET_NAME` 
	
## Deployments:

Once the appropriate service account config file has been saved according the instructions above, and there has been a
webhook placed into the secrete manager, perform:
`make DEPLOYMENT={STAGE} deploy`
to deploy the lambdas, and subscribe to the appropriate notifications in the DSS.