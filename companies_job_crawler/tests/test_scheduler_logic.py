import pytest

from app.models.company import CompanyConfig
from app.scheduler.scheduler_service import should_execute_company


@pytest.mark.parametrize(
    ("offset", "interval", "minute", "expected"),
    [
        (0, 15, 0, True),
        (0, 15, 15, True),
        (0, 15, 7, False),
        (1, 15, 1, True),
        (1, 15, 16, True),
        (1, 15, 0, False),
        (2, 10, 2, True),
        (2, 10, 12, True),
        (2, 10, 5, False),
    ],
)
def test_should_execute_company(offset: int, interval: int, minute: int, expected: bool) -> None:
    company = CompanyConfig(
        id="test",
        name="Test",
        enabled=True,
        interval_minutes=interval,
        offset_minutes=offset,
        crawler_type="html",
        url="https://example.com",
    )
    assert should_execute_company(company, minute) is expected


def test_disabled_company_never_executes() -> None:
    company = CompanyConfig(
        id="test",
        name="Test",
        enabled=False,
        interval_minutes=15,
        offset_minutes=0,
        crawler_type="html",
        url="https://example.com",
    )
    assert should_execute_company(company, 0) is False
