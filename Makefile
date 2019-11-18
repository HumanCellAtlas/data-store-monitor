include common.mk

STAGE=${DSS_DEPLOYMENT_STAGE}

json:
	python $(DSS_MON_HOME)/monitor/__init__.py

deploy-chalice:
	source environment && \
	$(MAKE) -C chalice deploy

infra-plan-all:
	$(MAKE) -C infra plan-all

infra-apply-all:
	$(MAKE) -C infra apply-all

list-subs:
	./scripts/subscription_manager.py --list --replica aws --stage $(STAGE)
	./scripts/subscription_manager.py --list --replica gcp --stage $(STAGE)

refresh-subs:
	./scripts/subscription_manager.py --resubscribe --replica aws --stage $(STAGE)
	./scripts/subscription_manager.py --resubscribe --replica gcp --stage $(STAGE)

list-all-stages:
	$(MAKE) list-subs STAGE=dev
	$(MAKE) list-subs STAGE=integration
	$(MAKE) list-subs STAGE=staging
	$(MAKE) list-subs STAGE=prod

refresh-all-stages:
	$(MAKE) refresh-subs STAGE=dev
	$(MAKE) refresh-subs STAGE=integration
	$(MAKE) refresh-subs STAGE=staging
	$(MAKE) refresh-subs STAGE=prod

gen-dashboard-tf:
	./scripts/generate_dss_dashboard.py --tf
