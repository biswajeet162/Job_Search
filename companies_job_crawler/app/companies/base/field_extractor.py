from typing import Any


class FieldExtractor:
    """
    Resolve company-specific field names to a single value.

    Career sites use inconsistent keys (jobId, work_id, requisitionId,
    job_description, description, jobTitle, etc.). Subclasses and mappers
    declare the key priority order per company.
    """

    @staticmethod
    def first_present(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            value = data.get(key)
            if value is not None and str(value).strip():
                return value
        return default

    @staticmethod
    def nested_first_present(
        data: dict[str, Any],
        paths: list[tuple[str, ...]],
        default: Any = None,
    ) -> Any:
        for path in paths:
            current: Any = data
            for part in path:
                if not isinstance(current, dict) or part not in current:
                    current = None
                    break
                current = current[part]
            if current is not None and str(current).strip():
                return current
        return default
