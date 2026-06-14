from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.core.base import FileDiscoverer
from src.utils.logger import log


class ANSDiscoverer(FileDiscoverer):
    """Discovers downloadable ZIP files for a given ANS open-data dataset."""

    def __init__(self, dataset_source_name: str) -> None:
        """
        Args:
            dataset_source_name: Name of the dataset directory on the ANS FTP server
                (e.g. ``"demonstracoes_contabeis"``). Used to build the index URL
                ``https://dadosabertos.ans.gov.br/FTP/PDA/{dataset_source_name}/``.
        """
        self.dataset_source_name = dataset_source_name
        self.url_base = "https://dadosabertos.ans.gov.br/FTP/PDA/"
        self.url_file = self.url_base + self.dataset_source_name + "/"

    def _get_soup(self) -> BeautifulSoup | None:
        """Fetch and parse the HTML index page for the dataset directory.

        The ANS FTP server returns pages encoded in Latin-1, so the response
        body is decoded accordingly before parsing.

        Returns:
            A ``BeautifulSoup`` object representing the index page, or ``None``
            if the request fails or an unexpected error occurs.
        """
        try:
            response = httpx.get(self.url_file, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content.decode("latin-1"), "html.parser")
        except httpx.HTTPError as e:
            log.error(f"HTTP error fetching index: {e}")
            return None
        except Exception as e:
            log.error(f"Error fetching {self.url_file}: {e}")
            return None

    def _list_zips(self, soup: BeautifulSoup) -> list[str] | None:
        """Extract absolute URLs of all ZIP files linked from the index page.

        Args:
            soup: Parsed HTML of the dataset index page.

        Returns:
            List of absolute ZIP URLs, an empty list if none are found, or
            ``None`` if parsing fails.
        """
        try:
            urls = [
                urljoin(self.url_file, link.get("href"))
                for link in soup.find_all("a")
                if link.get("href", "").endswith(".zip")
            ]
        except Exception as e:
            log.error(f"Error parsing HTML: {e}")
            return None

        if not urls:
            log.warning(f"No ZIP files found at {self.url_file}")
        else:
            log.info(f"Found {len(urls)} ZIP file(s) at {self.url_file}")

        return urls

    def discover(self) -> list[str] | None:
        """Return all ZIP URLs available for the configured dataset.

        Fetches the index page and extracts links ending in ``.zip``.

        Returns:
            List of absolute ZIP URLs, or ``None`` if the index page could not
            be retrieved.
        """
        soup = self._get_soup()
        if soup is None:
            return None
        return self._list_zips(soup)
