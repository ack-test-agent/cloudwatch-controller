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

"""Utilities for working with AnomalyDetector resources"""

import datetime
import time

import boto3
import pytest

DEFAULT_WAIT_UNTIL_DELETED_TIMEOUT_SECONDS = 60 * 10
DEFAULT_WAIT_UNTIL_DELETED_INTERVAL_SECONDS = 15


def wait_until_deleted(
        anomaly_detector_id: str,
        timeout_seconds: int = DEFAULT_WAIT_UNTIL_DELETED_TIMEOUT_SECONDS,
        interval_seconds: int = DEFAULT_WAIT_UNTIL_DELETED_INTERVAL_SECONDS,
    ) -> None:
    """Waits until an AnomalyDetector with a supplied ID is no longer returned
    from the CloudWatch API.

    Raises:
        pytest.fail upon timeout
    """
    now = datetime.datetime.now()
    timeout = now + datetime.timedelta(seconds=timeout_seconds)

    while True:
        if datetime.datetime.now() >= timeout:
            pytest.fail(
                "Timed out waiting for AnomalyDetector to be "
                "deleted in CloudWatch API"
            )
        time.sleep(interval_seconds)

        latest = get(anomaly_detector_id)
        if latest is None:
            break


def get(anomaly_detector_id: str):
    """Returns a dict containing the AnomalyDetector record from the
    CloudWatch API.

    If no such AnomalyDetector exists, returns None.
    """
    c = boto3.client('cloudwatch')
    resp = c.describe_anomaly_detectors(
        AnomalyDetectorIds=[anomaly_detector_id],
    )
    detectors = resp.get('AnomalyDetectors', [])
    if len(detectors) == 1:
        return detectors[0]
    return None


def exists(anomaly_detector_id: str) -> bool:
    """Returns True if the supplied AnomalyDetector exists, False otherwise."""
    return get(anomaly_detector_id) is not None
