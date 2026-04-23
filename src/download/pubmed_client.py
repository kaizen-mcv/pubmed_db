"""
PubMed client.

Simplified wrapper that uses PubMedBatchDownloader internally.
Provides a clean interface for common operations.

NOTE: For large downloads or advanced rate limiting,
use PubMedBatchDownloader directly.
"""

from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings
from src.download.batch_downloader import PubMedBatchDownloader


class PubMedClient:
    """
    Simplified client for the PubMed (NCBI Entrez) API.

    Uses PubMedBatchDownloader internally for:
    - Automatic rate limiting
    - Retries with backoff
    - HTTP error handling

    For advanced operations or massive downloads,
    use PubMedBatchDownloader directly.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the PubMed client.

        Args:
            email: Email required by NCBI (uses config if not provided)
            api_key: Optional API Key for a higher rate limit
        """
        download_config = settings.pubmed.get('download', {})

        self.email = email or download_config.get('email')
        self.api_key = api_key or download_config.get('api_key')

        if not self.email:
            raise ValueError(
                "Email required by NCBI. "
                "Configure it in config/pubmed_config.yaml"
            )

        # Use batch_downloader internally
        rate_config = settings.pubmed.get('rate_limiting', {})
        self._downloader = PubMedBatchDownloader(
            email=self.email,
            api_key=self.api_key,
            requests_per_second=rate_config.get('requests_per_second', 3),
            requests_per_second_off_peak=rate_config.get('requests_per_second_off_peak', 10),
        )

    def search(
        self,
        query: str,
        retmax: int = 10000,
        retstart: int = 0
    ) -> List[int]:
        """
        Search PMIDs matching a query.

        Args:
            query: PubMed search query
            retmax: Maximum results to return
            retstart: Starting offset

        Returns:
            List of PMIDs found
        """
        return self._downloader.search_pmids(query, retmax=retmax, retstart=retstart)

    def get_count(self, query: str) -> int:
        """
        Get the total number of results for a query.

        Args:
            query: Search query

        Returns:
            Total number of articles
        """
        return self._downloader.get_total_count(query)

    def fetch(
        self,
        pmids: List[int],
        rettype: str = "xml",
        retmode: str = "xml"
    ) -> Optional[Dict[str, Any]]:
        """
        Download articles by their PMIDs.

        Args:
            pmids: List of PMIDs to download
            rettype: Return type (xml, medline, etc.)
            retmode: Return mode

        Returns:
            Downloaded records or None if it fails
        """
        return self._downloader.fetch_batch(pmids, rettype=rettype, retmode=retmode)

    def fetch_single(self, pmid: int) -> Optional[Dict[str, Any]]:
        """
        Download a single article.

        Args:
            pmid: PMID of the article

        Returns:
            Article data or None
        """
        return self._downloader.fetch_single(pmid)

    def search_all(
        self,
        query: str,
        batch_size: int = 9999,
        max_results: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[int]:
        """
        Search ALL PMIDs matching a query.

        Uses automatic pagination and splits by periods if the 9999 limit is exceeded.

        Args:
            query: Search query
            batch_size: Size of each page (max 9,999 due to PubMed limit)
            max_results: Maximum results (None = no limit)
            date_from: Start date in YYYY/MM/DD format
            date_to: End date in YYYY/MM/DD format

        Returns:
            Complete list of PMIDs
        """
        return self._downloader.search_all_pmids(
            query,
            batch_size=batch_size,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
        )
