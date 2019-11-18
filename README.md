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
webhook placed into the secret manager, perform:
```
make deploy-chalice
make refresh-all-stages
```
to deploy the lambdas, and subscribe to the appropriate notifications in the DSS across all stages

## Graphana Dashboards:

The HCA DSS uses [dcp-monitoring](https://github.com/HumanCellAtlas/dcp-monitoring) to deploy and manage graphana dashboards.
('./scripts/generate_dss_dashboard.py')[] handles modification to the lambda metrics panels, and will format the panel to be used by the dcp-metrics repository.
to create a new dashboard use:
`make generate-dashboard-tf`
this formats the output into a file called dss-dashboard.tf which can be placed into [dcp-monitoring/../env-dashboards](https://github.com/HumanCellAtlas/dcp-monitoring/tree/master/terraform/modules/env-dashboards)

### Panel Formatting
Panel placement in graphana can be challenging when dealing with templates, (./scripts/generate_dss_dashboard.py)[] also offers a way to map an existing dashboard to a new dashboard template.
Start off by creating a dashboard in graphana, dont worry about populating the panels with data, just organize them.
Within the graphana dashboard settings, copy over the source dashboard json to a file locally.
`./scripts/generate_dss_dashboard.py --tf --position-dashboard {path-too-source-json} `
This will build out new lambda-panes but take the grid positioning from the source dashboard that was provided. 
 