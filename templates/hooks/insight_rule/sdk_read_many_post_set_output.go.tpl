	// Construct the ARN for this InsightRule since DescribeInsightRules
	// does not return an ARN field.
	if ko.Spec.RuleName != nil {
		arnStr := fmt.Sprintf(
			"arn:%s:cloudwatch:%s:%s:insight-rule/%s",
			rm.awsPartition,
			rm.awsRegion,
			rm.awsAccountID,
			*ko.Spec.RuleName,
		)
		if ko.Status.ACKResourceMetadata == nil {
			ko.Status.ACKResourceMetadata = &ackv1alpha1.ResourceMetadata{}
		}
		tmpARN := ackv1alpha1.AWSResourceName(arnStr)
		ko.Status.ACKResourceMetadata.ARN = &tmpARN
	}

	// DescribeInsightRules does not return tags — fetch them separately.
	if ko.Status.ACKResourceMetadata != nil && ko.Status.ACKResourceMetadata.ARN != nil {
		tagsInput := &svcsdk.ListTagsForResourceInput{
			ResourceARN: aws.String(string(*ko.Status.ACKResourceMetadata.ARN)),
		}
		tagsResp, tagsErr := rm.sdkapi.ListTagsForResource(ctx, tagsInput)
		rm.metrics.RecordAPICall("READ_MANY", "ListTagsForResource", tagsErr)
		if tagsErr != nil {
			return nil, tagsErr
		}
		ko.Spec.Tags = nil
		for _, t := range tagsResp.Tags {
			tCopy := svcapitypes.Tag{Key: t.Key, Value: t.Value}
			ko.Spec.Tags = append(ko.Spec.Tags, &tCopy)
		}
	}
