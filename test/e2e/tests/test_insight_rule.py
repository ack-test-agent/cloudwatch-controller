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

"""Integration tests for the CloudWatch API InsightRule resource
"""

import time

import pytest

from acktest.k8s import resource as k8s
from acktest.resources import random_suffix_name
from acktest import tags
from e2e import service_marker, CRD_GROUP, CRD_VERSION, load_cloudwatch_resource
from e2e.replacement_values import REPLACEMENT_VALUES
from e2e import condition
from e2e import insight_rule

RESOURCE_PLURAL = 'insightrules'

CHECK_STATUS_WAIT_SECONDS = 10
MODIFY_WAIT_AFTER_SECONDS = 10
DELETE_WAIT_AFTER_SECONDS = 5


def _make_insight_rule(name_prefix: str, resource_name: str,
                       additional_replacements: dict = None):
    """Creates an InsightRule from a resource file and deletes it afterwards.

    Yields the (reference, custom resource) pair.
    """
    insight_rule_name = random_suffix_name(name_prefix, 24)

    replacements = REPLACEMENT_VALUES.copy()
    replacements["INSIGHT_RULE_NAME"] = insight_rule_name
    if additional_replacements:
        replacements.update(additional_replacements)
    resource_data = load_cloudwatch_resource(
        resource_name,
        additional_replacements=replacements,
    )

    # Create the k8s resource
    ref = k8s.CustomResourceReference(
        CRD_GROUP, CRD_VERSION, RESOURCE_PLURAL,
        insight_rule_name, namespace="default",
    )
    k8s.create_custom_resource(ref, resource_data)
    cr = k8s.wait_resource_consumed_by_controller(ref)

    assert cr is not None
    assert k8s.get_resource_exists(ref)

    yield (ref, cr)

    # Try to delete, if doesn't already exist
    _, deleted = k8s.delete_custom_resource(
        ref,
        period_length=DELETE_WAIT_AFTER_SECONDS,
    )
    assert deleted

    insight_rule.wait_until_deleted(insight_rule_name)


@pytest.fixture
def _insight_rule():
    yield from _make_insight_rule("ack-test-insight-rule", "insight_rule")


@pytest.fixture
def _tagged_insight_rule():
    yield from _make_insight_rule(
        "ack-test-tagged-rule", "insight_rule_with_tags",
        additional_replacements={"TAG_VALUE": "test"})


@service_marker
@pytest.mark.canary
class TestInsightRule:
    def test_crud(self, _insight_rule):
        (ref, cr) = _insight_rule
        insight_rule_name = ref.name

        time.sleep(CHECK_STATUS_WAIT_SECONDS)

        condition.assert_synced(ref)

        assert insight_rule.exists(insight_rule_name)
        assert k8s.get_resource_exists(ref)

        # Verify the CR fields
        cr = k8s.get_resource(ref)
        assert cr["spec"]["ruleName"] == insight_rule_name
        assert cr["spec"]["ruleState"] == "ENABLED"
        assert cr["spec"]["ruleDefinition"] is not None

        # Verify Status fields are populated
        assert cr["status"].get("schema") is not None
        assert cr["status"]["ackResourceMetadata"]["arn"] is not None

        # Verify via the AWS API
        aws_rule = insight_rule.get(insight_rule_name)
        assert aws_rule is not None
        assert aws_rule["Name"] == insight_rule_name
        assert aws_rule["State"] == "ENABLED"

        # Update: change the rule state to DISABLED
        updates = {
            "spec": {
                "ruleState": "DISABLED",
            }
        }
        k8s.patch_custom_resource(ref, updates)
        cr = k8s.wait_resource_consumed_by_controller(ref)

        assert cr is not None
        assert k8s.get_resource_exists(ref)

        time.sleep(MODIFY_WAIT_AFTER_SECONDS)
        condition.assert_synced(ref)

        # Verify the update via the CR
        cr = k8s.get_resource(ref)
        assert cr["spec"]["ruleState"] == "DISABLED"

        # Verify the update via the AWS API
        updated_rule = insight_rule.get(insight_rule_name)
        assert updated_rule is not None
        assert updated_rule["State"] == "DISABLED"


@service_marker
class TestInsightRuleTags:
    """Covers tag reconciliation on an InsightRule.

    PutInsightRule ignores the Tags field when updating an existing rule, so
    tag changes are synced via the dedicated TagResource/UntagResource APIs.
    """

    def test_tag_sync(self, _tagged_insight_rule):
        (ref, cr) = _tagged_insight_rule
        insight_rule_name = ref.name

        time.sleep(CHECK_STATUS_WAIT_SECONDS)
        condition.assert_synced(ref)

        assert insight_rule.exists(insight_rule_name)

        # The ARN is required to list tags in the AWS API.
        cr = k8s.get_resource(ref)
        insight_rule_arn = cr["status"]["ackResourceMetadata"]["arn"]

        # Verify the create-time tag via the CR.
        tags.assert_present(
            expected={"env": "test"},
            actual=cr["spec"].get("tags"),
            key_member_name="key",
            value_member_name="value",
        )

        # Verify via the AWS API.
        aws_tags = insight_rule.get_tags(insight_rule_arn)
        tags.assert_present(expected={"env": "test"}, actual=aws_tags)
        # The controller must also apply the ACK system tags on create.
        tags.assert_ack_system_tags(tags=aws_tags)

        # Add a tag and update the value of the existing tag.
        updates = {
            "spec": {
                "tags": [
                    {"key": "env", "value": "prod"},
                    {"key": "team", "value": "platform"},
                ]
            }
        }
        k8s.patch_custom_resource(ref, updates)
        k8s.wait_resource_consumed_by_controller(ref)
        time.sleep(MODIFY_WAIT_AFTER_SECONDS)
        condition.assert_synced(ref)

        aws_tags = insight_rule.get_tags(insight_rule_arn)
        tags.assert_present(
            expected={"env": "prod", "team": "platform"},
            actual=aws_tags,
        )
        # The ACK system tags must survive the TagResource call.
        tags.assert_ack_system_tags(tags=aws_tags)

        # Remove a tag. Exercises UntagResource.
        updates = {
            "spec": {
                "tags": [
                    {"key": "env", "value": "prod"},
                ]
            }
        }
        k8s.patch_custom_resource(ref, updates)
        k8s.wait_resource_consumed_by_controller(ref)
        time.sleep(MODIFY_WAIT_AFTER_SECONDS)
        condition.assert_synced(ref)

        aws_tags = insight_rule.get_tags(insight_rule_arn)
        tags.assert_equal_without_ack_tags(
            expected={"env": "prod"},
            actual=aws_tags,
        )
        # The ACK system tags must survive the UntagResource call.
        tags.assert_ack_system_tags(tags=aws_tags)
