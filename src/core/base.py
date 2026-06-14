from abc import ABC, abstractmethod


class FileDiscoverer(ABC):
    @abstractmethod
    def discover(self) -> list[str] | None: ...


class Downloader(ABC):
    @abstractmethod
    def download_all(self) -> None: ...
