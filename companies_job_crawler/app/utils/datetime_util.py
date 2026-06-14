from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


def now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return utc_now().isoformat()


def format_date_folder(dt: datetime | None = None) -> str:
    """Format datetime as DD-MM-YYYY for storage folders."""
    current = dt or utc_now()
    return current.strftime("%d-%m-%Y")


def format_time_filename(dt: datetime | None = None) -> str:
    """Format datetime as HH-MM-SS for sortable JSON filenames."""
    current = dt or utc_now()
    return current.strftime("%H-%M-%S")


def execution_id_timestamp(dt: datetime | None = None) -> str:
    """Format datetime as YYYYMMDD_HHMMSS for execution IDs."""
    current = dt or utc_now()
    return current.strftime("%Y%m%d_%H%M%S")
