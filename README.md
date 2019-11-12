#  data-store-monitor

This is a monitoring plugin for the [DataStore](https://github.com/HumanCellAtlas/data-store)

## Overview:
The data-store-monitor plugin utilizes subscriptions to get bundle events notifications from the data-store.
There is a singular aws-lambda function that serves as a backend for processing these events into cloudwatch metrics.


## Data-Store Authentication:
The DSS Monitor Service Identity is provided by a GCP Service account. This service account is used to authenticate to the data-store, in order
to perform actions on the /Subscriptions endpoint. One service-account can be used to create subscriptions on multiple stages. 
To create a service account use the commands:
```
make infra-apply-all
make infra-plan-all
```
Once the service account is created head over to [gcp-dashboard](https://console.developers.google.com/) and download the
`gcp_credentials.json` associated with the account created, this file needs to be placed inside the `${DSS_MON_HOME}/deployments/` folder.
Alternatively this short command can also be run:
```
source evironment
gcloud iam service-accounts keys create ${DSS_MON_HOME}/gcp-credentials.json --iam-account ${DSS_MON_GCP_SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_NAME}.iam.gserviceaccount.com
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