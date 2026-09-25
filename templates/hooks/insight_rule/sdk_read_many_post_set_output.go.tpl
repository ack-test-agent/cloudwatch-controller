	// Construct the ARN since DescribeInsightRules does not return it.
	// Format: arn:<partition>:cloudwatch:<region>:<account-id>:insight-rule/<rule-name>
	if ko.Spec.Name != nil {
		arnStr := fmt.Sprintf(
			"arn:%s:cloudwatch:%s:%s:insight-rule/%s",
			rm.awsPartition,
			rm.awsRegion,
			rm.awsAccountID,
			*ko.Spec.Name,
		)
		if ko.Status.ACKResourceMetadata == nil {
			ko.Status.ACKResourceMetadata = &ackv1alpha1.ResourceMetadata{}
		}
		tmpARN := ackv1alpha1.AWSResourceName(arnStr)
		ko.Status.ACKResourceMetadata.ARN = &tmpARN
	}
	// Fetch tags via ListTagsForResource (DescribeInsightRules does not return tags)
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
