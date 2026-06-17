from datetime import date

from src.core.ans_discoverer import ANSDiscoverer
from src.core.ans_downloader import ANSDownloader
from src.utils.logger import log

DATASET = "demonstracoes_contabeis"


class DemonstracoesContabeisIngestor:
    """Orchestrates discovery and download of ANS financial statements (demonstrações contábeis).

    ZIP files are organised on the ANS FTP server under
    ``demonstracoes_contabeis/{year}/{quarter}T{year}.zip``.
    This class discovers all available ZIPs for each requested year and
    delegates downloading and extraction to ``ANSDownloader``.
    """

    def __init__(
        self,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> None:
        """
        Args:
            start_year: First year of the range to ingest (inclusive).
                Defaults to the current year when omitted.
            end_year: Last year of the range to ingest (inclusive).
                Defaults to ``start_year`` when omitted, so passing only
                ``start_year`` ingests a single year.
        """
        current_year = date.today().year
        self.start_year = start_year or current_year
        self.end_year = end_year or self.start_year
        self.years = list(range(self.start_year, self.end_year + 1))

    def _discover_urls(self) -> list[str]:
        """Collect ZIP URLs for every year in the configured range.

        A separate ``ANSDiscoverer`` is created per year because the ANS FTP
        server organises files under per-year subdirectories
        (``demonstracoes_contabeis/{year}/``).

        Returns:
            Aggregated list of absolute ZIP URLs across all requested years.
        """
        urls: list[str] = []
        for year in self.years:
            discoverer = ANSDiscoverer(f"{DATASET}/{year}")
            found = discoverer.discover()
            if found:
                urls.extend(found)
            else:
                log.warning(f"No ZIP files found for year {year}")
        return urls

    def run(self) -> None:
        """Run the full ingestion: discover URLs, download ZIPs, extract CSVs.

        Skips execution if no URLs are found for the requested year range.
        """
        log.info(f"Starting ingestion for years {self.years}")
        urls = self._discover_urls()
        if not urls:
            log.warning("No ZIP files found — ingestion aborted")
            return
        log.info(f"Discovered {len(urls)} ZIP file(s) — starting download")
        downloader = ANSDownloader(urls, DATASET)
        downloader.download_all()
        log.info("Ingestion complete")
