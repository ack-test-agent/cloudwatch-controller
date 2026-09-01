	if r.ko.Status.AnomalyDetectorID == nil || *r.ko.Status.AnomalyDetectorID == "" {
		return nil, ackerr.NotFound
	}
	input.AnomalyDetectorIds = []string{*r.ko.Status.AnomalyDetectorID}
