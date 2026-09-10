# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may
# not use this file except in compliance with the License. A copy of the
# License is located at
#
#         http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Utilities for working with InsightRule resources"""

import datetime
import time

import boto3
import pytest

DEFAULT_WAIT_UNTIL_DELETED_TIMEOUT_SECONDS = 60*20
DEFAULT_WAIT_UNTIL_DELETED_INTERVAL_SECONDS = 15


def wait_until_deleted(
        insight_rule_name: str,
        timeout_seconds: int = DEFAULT_WAIT_UNTIL_DELETED_TIMEOUT_SECONDS,
        interval_seconds: int = DEFAULT_WAIT_UNTIL_DELETED_INTERVAL_SECONDS,
    ) -> None:
    """Waits until an InsightRule with a supplied name is no longer returned from
    the CloudWatch API.

    Usage:
        from e2e.insight_rule import wait_until_deleted

        wait_until_deleted(rule_name)

    Raises:
        pytest.fail upon timeout
    """
    now = datetime.datetime.now()
    timeout = now + datetime.timedelta(seconds=timeout_seconds)

    while True:
        if datetime.datetime.now() >= timeout:
            pytest.fail(
                "Timed out waiting for InsightRule to be "
                "deleted in CloudWatch API"
            )
        time.sleep(interval_seconds)

        latest = get(insight_rule_name)
        if latest is None:
            break


def exists(insight_rule_name):
    """Returns True if the supplied InsightRule exists, False otherwise.
    """
    return get(insight_rule_name) is not None


def get(insight_rule_name):
    """Returns a dict containing the InsightRule record from the CloudWatch API.

    If no such InsightRule exists, returns None.
    """
    c = boto3.client('cloudwatch')
    # describe_insight_rules does not support boto3 paginators, so we
    # paginate manually via NextToken.
    kwargs = {}
    while True:
        resp = c.describe_insight_rules(**kwargs)
        for rule in resp.get('InsightRules', []):
            if rule.get('Name') == insight_rule_name:
                return rule
        next_token = resp.get('NextToken')
        if not next_token:
            break
        kwargs['NextToken'] = next_token
    return None


def get_tags(insight_rule_arn):
    """Returns a list containing the InsightRule's tag records from the
    CloudWatch API.

    If no such InsightRule exists, returns None.
    """
    c = boto3.client('cloudwatch')
    try:
        resp = c.list_tags_for_resource(
            ResourceARN=insight_rule_arn,
        )
        return resp['Tags']
    except c.exceptions.ResourceNotFoundException:
        return None
