	// DescribeInsightRules returns ALL rules with no name filter.
	// We must scan the response to find the matching rule by name.
	if r.ko.Spec.Name == nil {
		return nil, ackerr.NotFound
	}
	desiredName := *r.ko.Spec.Name
	matchFound := false
	for _, rule := range resp.InsightRules {
		if rule.Name != nil && *rule.Name == desiredName {
			resp.InsightRules = []svcsdktypes.InsightRule{rule}
			matchFound = true
			break
		}
	}
	if !matchFound {
		return nil, ackerr.NotFound
	}
