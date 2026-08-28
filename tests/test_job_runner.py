from jobs.runner import job_failed


def test_job_failure_status_propagates_to_scheduler():
    assert job_failed({"tickers_failed": 1, "tickers_succeeded": 9}) is True
    assert job_failed({"articles_failed": 1, "articles_analyzed": 99}) is True
    assert job_failed({"status": "insufficient_historical_validation_data"}) is True
    assert job_failed({"status": "validated", "predictions_upserted": 10}) is False
    assert job_failed({"tickers_failed": 0, "tickers_succeeded": 10}) is False