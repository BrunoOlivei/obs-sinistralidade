import io
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx

from src.core.base import Downloader
from src.utils.logger import log


class ANSDownloader(Downloader):
    """Downloads and extracts ZIP files from the ANS open-data FTP server."""

    def __init__(self, zip_urls: list[str], dataset_source_name: str) -> None:
        """
        Args:
            zip_urls: List of absolute URLs pointing to ZIP files on the ANS FTP server.
            data_source: The source of the data (e.g. "TISS").
        """
        self.zip_urls = zip_urls
        self.dataset_source_name = dataset_source_name
        self.landzone_root = Path("data/landzone")
        self.zips_root = self.landzone_root / "zips"
        self.csv_root = self.landzone_root / "csv"

    def download_zip(self, zip_url: str) -> bytes | None:
        """Fetch a ZIP file from the given URL and return its raw content.

        Args:
            zip_url: Absolute URL to the ZIP file.

        Returns:
            Raw bytes of the ZIP file, or ``None`` if the request fails.
        """
        try:
            response = httpx.get(zip_url, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"HTTP error downloading {zip_url}: {e}")
            return None
        except Exception as e:
            log.error(f"Error downloading {zip_url}: {e}")
            return None
        log.info(f"Downloaded {zip_url}")
        return response.content

    def save_zip(self, content: bytes, zip_url: str) -> Path | None:
        """Persist a ZIP file to ``landzone/zips/{dataset}/{filename}.zip``.

        The destination directory is created on demand if it does not exist.

        Args:
            content: Raw bytes of the ZIP file.
            zip_url: Original URL used to derive the dataset name and filename.

        Returns:
            Path to the saved file, or ``None`` if writing fails.
        """
        filename = Path(urlparse(zip_url).path).name
        dest_dir = self.zips_root / self.dataset_source_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / filename
        try:
            dest_file.write_bytes(content)
        except OSError as e:
            log.error(f"Error saving ZIP to {dest_file}: {e}")
            return None
        log.info(f"Saved ZIP to {dest_file}")
        return dest_file

    def extract_zip(self, content: bytes, zip_url: str) -> bool:
        """Extract a ZIP archive into ``landzone/csv/{dataset}/``.

        All files from the archive are extracted flat into the dataset directory,
        so multiple ZIPs from the same dataset accumulate in one place for easy
        PySpark reads.  The destination directory is created on demand.

        Args:
            content: Raw bytes of the ZIP file.
            zip_url: Original URL used to derive the target dataset directory.

        Returns:
            ``True`` on success, ``False`` if the archive is corrupt or
            extraction raises an unexpected error.
        """
        dest_dir = self.csv_root / self.dataset_source_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                zf.extractall(dest_dir)
        except zipfile.BadZipFile as e:
            log.error(f"Bad ZIP: {e}")
            return False
        except Exception as e:
            log.error(f"Extraction error at {dest_dir}: {e}")
            return False
        log.info(f"Extracted to {dest_dir}")
        return True

    def download_all(self) -> None:
        """Download and extract every URL in ``self.zip_urls``.

        For each URL the ZIP is saved to the landzone before extraction.
        If extraction fails the ZIP is still retained on disk so it can be
        reprocessed without re-downloading.  URLs that fail to download are
        skipped with an error log.
        """
        for zip_url in self.zip_urls:
            content = self.download_zip(zip_url)
            if content is None:
                continue
            self.save_zip(content, zip_url)
            if not self.extract_zip(content, zip_url):
                log.warning(f"Extraction failed for {zip_url}, skipping")
