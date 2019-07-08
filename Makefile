include common.mk


# api_gateway_id:=aws apigateway get-rest-apis | jq -r '.items[] | select(.name=="${DSS_MON_API_GATEWAY_NAME}") | .id'
api_gateway_id:=$(shell aws apigateway get-rest-apis | jq -r '.items[] | select(.name=="azul-service-hannes") | .id')
api_gateway_url:=https://$(api_gateway_id).execute-api.${AWS_DEFAULT_REGION}.amazonaws.com/${DSS_INFRA_TAG_STAGE}
subscriptions:=$(shell hca dss get-subscriptions --replica aws | jq -r '.subscriptions[] | .uuid ')

echo:
	echo $(subscriptions)


deploy-chalice:
	$(MAKE) -C chalice deploy
	delete-subscriptions
	create-all-subscriptions

delete-subscriptions:
	for uuid in $(subscriptions) ; do \
		hca dss delete-subscription --uuid $$uuid --replica aws ; \
	done

create-all-subscriptions: request-tombstone-subscription request-delete-subscription request-create-subscription

request-tombstone-subscription:
	hca dss put-subscription --replica aws --callback-url $(api_gateway_url) --jmespath-query "event_type=='TOMBSTONE'"

request-delete-subscription:
	hca dss put-subscription --replica aws --callback-url $(api_gateway_url) --jmespath-query "event_type=='DELETE'"

request-create-subscription:
	hca dss put-subscription --replica aws --callback-url $(api_gateway_url) --jmespath-query "event_type=='CREATE'"

