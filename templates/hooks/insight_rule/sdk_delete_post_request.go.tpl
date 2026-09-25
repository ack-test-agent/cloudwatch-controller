	// DeleteInsightRules is a batch API — check for partial failures.
	if resp != nil && len(resp.Failures) > 0 {
		failMsg := "failed to delete insight rule"
		if resp.Failures[0].FailureDescription != nil {
			failMsg = *resp.Failures[0].FailureDescription
		}
		return nil, fmt.Errorf("%s", failMsg)
	}
