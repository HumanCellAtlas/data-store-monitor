include common.mk


api_gateway_id:=$(shell aws apigateway get-rest-apis | jq -r '.items[] | select(.name=="${CHALICE_APP_NAME}-${DSS_INFRA_TAG_STAGE}") | .id')
api_gateway_url:=https://$(api_gateway_id).execute-api.${AWS_DEFAULT_REGION}.amazonaws.com/${DSS_INFRA_TAG_STAGE}/notifications
subscriptions:=$(shell hca dss get-subscriptions --replica aws | jq -r '.subscriptions[] | .uuid ')

get-url:
	echo $(api_gateway_url)
json:
	python $(DSS_MON_HOME)/monitor/__init__.py

deploy: deploy-chalice delete-subscriptions create-all-subscriptions

deploy-chalice:
	source environment && \
	$(MAKE) -C chalice deploy

refresh-subscriptions: delete-subscriptions create-all-subscriptions

delete-subscriptions:
	source environment && \
	for uuid in $(subscriptions) ; do \
		hca dss delete-subscription --uuid $$uuid --replica aws ; \
	done

create-all-subscriptions: request-tombstone-subscription request-delete-subscription request-create-subscription

request-tombstone-subscription:
	source environment && \
	hca dss put-subscription --replica aws --callback-url $(api_gateway_url) --jmespath-query "event_type=='TOMBSTONE'"

request-delete-subscription:
	source environment && \
	hca dss put-subscription --replica aws --callback-url $(api_gateway_url) --jmespath-query "event_type=='DELETE'"

request-create-subscription:
	source environment && \
	hca dss put-subscription --replica aws --callback-url $(api_gateway_url) --jmespath-query "event_type=='CREATE'"

list-subscriptions:
	source environment && \
	hca dss get-subscriptions --replica aws