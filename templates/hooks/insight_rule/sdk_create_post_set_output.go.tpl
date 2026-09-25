	// PutInsightRuleOutput is empty — construct the ARN manually.
	// Format: arn:<partition>:cloudwatch:<region>:<account-id>:insight-rule/<rule-name>
	if desired.ko.Spec.Name != nil {
		arnStr := fmt.Sprintf(
			"arn:%s:cloudwatch:%s:%s:insight-rule/%s",
			rm.awsPartition,
			rm.awsRegion,
			rm.awsAccountID,
			*desired.ko.Spec.Name,
		)
		if ko.Status.ACKResourceMetadata == nil {
			ko.Status.ACKResourceMetadata = &ackv1alpha1.ResourceMetadata{}
		}
		tmpARN := ackv1alpha1.AWSResourceName(arnStr)
		ko.Status.ACKResourceMetadata.ARN = &tmpARN
	}
