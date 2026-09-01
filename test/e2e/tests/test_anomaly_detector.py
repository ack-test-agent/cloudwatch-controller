# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may
# not use this file except in compliance with the License. A copy of the
# License is located at
#
#	 http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Integration tests for the CloudWatch API AnomalyDetector resource
"""

import time

import pytest

from acktest.k8s import resource as k8s
from acktest.resources import random_suffix_name
from e2e import service_marker, CRD_GROUP, CRD_VERSION, load_cloudwatch_resource
from e2e.replacement_values import REPLACEMENT_VALUES
from e2e import condition
from e2e import anomaly_detector

RESOURCE_PLURAL = 'anomalydetectors'

CHECK_STATUS_WAIT_SECONDS = 10
MODIFY_WAIT_AFTER_SECONDS = 10
DELETE_WAIT_AFTER_SECONDS = 5


@pytest.fixture
def simple_anomaly_detector():
    resource_name = random_suffix_name("ack-test-ad", 24)

    replacements = REPLACEMENT_VALUES.copy()
    replacements["ANOMALY_DETECTOR_NAME"] = resource_name

    resource_data = load_cloudwatch_resource(
        "anomaly_detector",
        additional_replacements=replacements,
    )

    # Create the k8s resource
    ref = k8s.CustomResourceReference(
        CRD_GROUP, CRD_VERSION, RESOURCE_PLURAL,
        resource_name, namespace="default",
    )
    k8s.create_custom_resource(ref, resource_data)
    cr = k8s.wait_resource_consumed_by_controller(ref)

    assert cr is not None
    assert k8s.get_resource_exists(ref)

    yield (ref, cr)

    # Try to delete, if doesn't already exist
    try:
        _, deleted = k8s.delete_custom_resource(
            ref,
            wait_periods=5,
            period_length=DELETE_WAIT_AFTER_SECONDS,
        )
        assert deleted
    except Exception:
        pass


@service_marker
@pytest.mark.canary
class TestAnomalyDetector:
    def test_crud_anomaly_detector(self, simple_anomaly_detector, cloudwatch_client):
        (ref, cr) = simple_anomaly_detector

        time.sleep(CHECK_STATUS_WAIT_SECONDS)

        condition.assert_synced(ref)

        # Verify the CR has the expected spec fields
        cr = k8s.get_resource(ref)
        assert cr is not None
        assert 'singleMetricAnomalyDetector' in cr['spec']
        sma = cr['spec']['singleMetricAnomalyDetector']
        assert sma['namespace'] == 'AWS/EC2'
        assert sma['metricName'] == 'CPUUtilization'
        assert sma['stat'] == 'Average'

        # Verify the Status has the AnomalyDetectorID
        assert 'anomalyDetectorID' in cr['status']
        detector_id = cr['status']['anomalyDetectorID']
        assert detector_id is not None and detector_id != ""

        # Verify via the AWS API
        aws_detector = anomaly_detector.get(detector_id)
        assert aws_detector is not None, \
            f"AnomalyDetector {detector_id} not found in AWS API"
        assert aws_detector.get('SingleMetricAnomalyDetector', {}).get('MetricName') == 'CPUUtilization'
        assert aws_detector.get('SingleMetricAnomalyDetector', {}).get('Namespace') == 'AWS/EC2'
        assert aws_detector.get('SingleMetricAnomalyDetector', {}).get('Stat') == 'Average'

        # Update: change the Configuration (mutable field)
        updates = {
            "spec": {
                "configuration": {
                    "metricTimezone": "UTC",
                },
            },
        }
        k8s.patch_custom_resource(ref, updates)
        time.sleep(MODIFY_WAIT_AFTER_SECONDS)
        condition.assert_synced(ref)

        # Verify the update via the CR
        cr = k8s.get_resource(ref)
        assert cr is not None
        assert 'configuration' in cr['spec']
        assert cr['spec']['configuration']['metricTimezone'] == 'UTC'

        # Verify the update via the AWS API
        aws_detector = anomaly_detector.get(detector_id)
        assert aws_detector is not None
        config = aws_detector.get('Configuration', {})
        assert config.get('MetricTimezone') == 'UTC'

        # Delete is handled by the fixture teardown.
        # After fixture cleanup, verify the detector is gone from AWS.
