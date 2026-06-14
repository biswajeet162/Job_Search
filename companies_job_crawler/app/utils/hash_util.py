import hashlib

from app.utils.datetime_util import execution_id_timestamp, utc_now


def generate_execution_id(company_id: str, dt=None) -> str:
    """Build a unique execution identifier for a crawler run."""
    timestamp = execution_id_timestamp(dt)
    return f"{company_id}_{timestamp}"


def generate_job_id(company_id: str, job_url: str, job_title: str = "") -> str:
    """Generate a stable job identifier from company and URL/title."""
    payload = f"{company_id}|{job_url}|{job_title}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:16]
    return f"{company_id}_{digest}"
