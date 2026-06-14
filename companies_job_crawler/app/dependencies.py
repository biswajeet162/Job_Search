from app.config.settings import Settings, get_settings
from app.config.config_loader import ConfigLoader
from app.services.file_service import FileService
from app.services.storage_service import StorageService
from app.services.crawl_service import CrawlService
from app.companies.registry import CompanyServiceRegistry
from app.scheduler.scheduler_service import SchedulerService


class AppContainer:
    """Dependency container wiring application services."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = (settings or get_settings()).resolve_paths()
        self.config_loader = ConfigLoader(self.settings)
        self.file_service = FileService()
        self.storage_service = StorageService(self.settings, self.file_service)
        self.company_registry = CompanyServiceRegistry(self.settings)
        self.crawl_service = CrawlService(
            self.settings,
            self.config_loader,
            self.storage_service,
            self.company_registry,
        )
        self.scheduler_service = SchedulerService(
            self.config_loader,
            self.crawl_service,
        )


_container: AppContainer | None = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


def reset_container() -> None:
    global _container
    _container = None
