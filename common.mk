SHELL=/bin/bash



ifndef DSS_MON_HOME
$(error Please run "source environment" in the data-store repo root directory before running make commands)
endif

ifeq (,$(wildcard ${DSS_MON_HOME}/${DSS_INFRA_TAG_STAGE}/gcp-credentials.json))
$(error Missing GOOGLE_APPLICATION_CREDENTIALS from deployments folder)
endif

ifeq ($(shell which jq),)
$(error Please install jq using "apt-get install jq" or "brew install jq")
endif

ifeq ($(shell which sponge),)
$(error Please install sponge using "apt-get install moreutils" or "brew install moreutils")
endif

ifeq ($(shell which envsubst),)
$(error Please install envsubst using "apt-get install gettext" or "brew install gettext; brew link gettext")
endif

