# SightGlass

SightGlass is a monitoring plugin for the [DataStore](https://github.com/HumanCellAtlas/data-store)

## DSS-Authentication:
Due to the DSS requiring authentication for the /Subscription endpoint we must create a service account with GCP
that will be utilized for the hca cli tool login.
The service account is created for you, see [infra/google-account](infra/google-account) for more information
Once the service account is created head over to [gcp-dashboard](https://console.developers.google.com/) and get the
`gcp_credentials.json` associated with the account created. 

```
gcloud iam service-accounts keys create ${DSS_MON_HOME}/deployments/${DSS_INFRA_TAG_STAGE}/gcp-credentials.json --iam-account ${DSS_MON_GCP_SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_NAME}.iam.gserviceaccount.com
```

## Stages:
Stage configuration files are stored in the (deployments)[deployments] directory.
This includes a config file for the HCA tool, as well as the location to save the `gcp_credentials.json` for the applicable
service account. 
To deploy a different stage, perform:
``` export DEPLOYMENT={STAGE} && source environment```

## Secrets:

### Webhook
The DSS-Monitor can provide notifications for daily progress in a slack channel. Add a webhook url as follows
	`echo 'URL' | scripts/set_secret.py --secret-name $DSS_MONITOR_WEBHOOK_SECRET_NAME` 
	
