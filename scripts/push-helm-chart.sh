#!/usr/bin/env bash

CHART_VERSION=${VERSION//v/}

helm init --client-only
helm plugin install https://github.com/nouney/helm-gcs
helm repo add repo $REPO
helm package infra/helm/$CHART_NAME --version=$CHART_VERSION
helm gcs push $CHART_NAME-$CHART_VERSION.tgz repo
