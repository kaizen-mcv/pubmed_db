#!/usr/bin/env python3
"""
Batch downloader for PubMed articles.

Strictly complies with NCBI policies:
- Configurable rate limiting
- Error handling and retries
- Efficient batch downloading
- Recovery from interruptions
"""

import sys
import os
import time
import logging
from typing import List, Optional, Dict, Any
from Bio import Entrez
from urllib.error import HTTPError

# Import project modules
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from rate_limiter import AdaptiveRateLimiter

# Module logger
logger = logging.getLogger(__name__)


class PubMedBatchDownloader:
    """
    Batch downloader that complies with NCBI policies.

    Features:
    - Automatic rate limiting
    - Retries with exponential backoff
    - Efficient batch downloading
    - Robust error handling
    """

    def __init__(
        self,
        email: str,
        api_key: Optional[str] = None,
        requests_per_second: float = 3.0,
        requests_per_second_off_peak: float = 10.0,
    ):
        """
        Initialize the downloader.

        Args:
            email: Email required by NCBI
            api_key: Optional API Key (raises limit to 10 req/s)
            requests_per_second: Requests/second limit
            requests_per_second_off_peak: Limit during off-peak hours
        """
        # Configure Entrez
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
            # With API key, use higher limit by default
            if requests_per_second == 3.0:
                requests_per_second = 10.0

        # Adaptive rate limiter
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_second=requests_per_second,
            requests_per_second_off_peak=requests_per_second_off_peak,
        )

        # Configuration
        self.max_retries = 3
        self.retry_delay = 5
        self.batch_size = 200  # IDs per batch (efetch accepts up to 500)

    def search_pmids(
        self,
        query: str,
        retmax: int = 10000,
        retstart: int = 0,
    ) -> List[int]:
        """
        Search PMIDs using esearch.

        Args:
            query: PubMed search query
            retmax: Maximum number of results to return
            retstart: Starting offset

        Returns:
            List of PMIDs found
        """
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self.rate_limiter.wait_if_needed()

                # Search
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=retmax,
                    retstart=retstart,
                    usehistory="y",  # Use history server for large queries
                )
                record = Entrez.read(handle)
                handle.close()

                pmids = [int(pmid) for pmid in record["IdList"]]
                return pmids

            except HTTPError as e:
                if e.code == 429:
                    # Too many requests
                    self.rate_limiter.handle_429_error()
                    logger.warning("Rate limit excedido, reduciendo velocidad...")
                    continue

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Error HTTP {e.code}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Error en búsqueda: {e}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

        return []

    def fetch_batch(
        self,
        pmids: List[int],
        rettype: str = "xml",
        retmode: str = "xml",
    ) -> Optional[Any]:
        """
        Download a batch of articles using efetch.

        Args:
            pmids: List of PMIDs to download
            rettype: Return type (xml, medline, etc.)
            retmode: Return mode

        Returns:
            Downloaded records or None if it fails
        """
        if not pmids:
            return None

        # Convert list to comma-separated string
        id_list = ",".join(str(pmid) for pmid in pmids)

        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self.rate_limiter.wait_if_needed()

                # Fetch
                handle = Entrez.efetch(
                    db="pubmed",
                    id=id_list,
                    rettype=rettype,
                    retmode=retmode,
                )

                records = Entrez.read(handle)
                handle.close()

                return records

            except HTTPError as e:
                if e.code == 429:
                    # Too many requests
                    self.rate_limiter.handle_429_error()
                    logger.warning("Rate limit excedido, reduciendo velocidad...")
                    continue

                if e.code == 400:
                    # Bad request, do not retry
                    logger.error(f"Error 400 para PMIDs: {pmids[:5]}... (request inválido)")
                    return None

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Error HTTP {e.code}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error HTTP {e.code} tras {self.max_retries} intentos")
                    return None

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Error en fetch: {e}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error tras {self.max_retries} intentos: {e}")
                    return None

        return None

    def fetch_single(
        self,
        pmid: int,
        rettype: str = "xml",
        retmode: str = "xml",
    ) -> Optional[Any]:
        """
        Download a single article.

        Args:
            pmid: PMID to download
            rettype: Return type
            retmode: Return mode

        Returns:
            Downloaded record or None if it fails
        """
        records = self.fetch_batch([pmid], rettype, retmode)
        if records and "PubmedArticle" in records and records["PubmedArticle"]:
            return records["PubmedArticle"][0]
        return None

    def download_in_batches(
        self,
        pmids: List[int],
        callback=None,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Download a list of PMIDs in batches.

        Args:
            pmids: List of PMIDs to download
            callback: Callback function callback(article_data) called for each article
            batch_size: Batch size (None = use default)

        Returns:
            Download statistics
        """
        if batch_size is None:
            batch_size = self.batch_size

        total = len(pmids)
        downloaded = 0
        failed = 0

        logger.info(f"Descargando {total:,} artículos en lotes de {batch_size}...")

        for i in range(0, total, batch_size):
            batch = pmids[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"Lote {batch_num}/{total_batches} ({len(batch)} PMIDs)...")

            records = self.fetch_batch(batch)

            if records and "PubmedArticle" in records:
                articles = records["PubmedArticle"]

                for article in articles:
                    try:
                        if callback:
                            callback(article)
                        downloaded += 1
                    except Exception as e:
                        logger.error(f"Error procesando artículo: {e}")
                        failed += 1

                logger.debug(f"Lote {batch_num}: {len(articles)} artículos descargados")
            else:
                logger.warning(f"Lote {batch_num} falló")
                failed += len(batch)

        # Final statistics
        stats = {
            "total": total,
            "downloaded": downloaded,
            "failed": failed,
            "rate_limiter_stats": self.rate_limiter.get_stats(),
        }

        return stats

    def get_total_count(self, query: str) -> int:
        """
        Get the total count of results for a query.

        Args:
            query: Search query

        Returns:
            Total number of matching articles
        """
        try:
            self.rate_limiter.wait_if_needed()

            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=0,  # We only want the count
            )
            record = Entrez.read(handle)
            handle.close()

            return int(record["Count"])

        except Exception as e:
            logger.error(f"Error obteniendo conteo: {e}")
            return 0

    def search_all_pmids(
        self,
        query: str,
        batch_size: int = 9999,
        max_results: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[int]:
        """
        Search ALL PMIDs matching a query.

        NOTE: PubMed ESearch has a limit of 9,999 results per search.
        For large queries, this method automatically divides by time periods
        (months) to retrieve all results.

        Args:
            query: Search query
            batch_size: Size of each page (max 9,999 due to PubMed limit)
            max_results: Maximum results (None = no limit)
            date_from: Start date in YYYY/MM/DD format (for subdivision)
            date_to: End date in YYYY/MM/DD format (for subdivision)

        Returns:
            Complete list of PMIDs
        """
        # PubMed ESearch limit
        PUBMED_MAX_RESULTS = 9999

        # Get total count
        total_count = self.get_total_count(query)
        logger.info(f"Total de artículos encontrados: {total_count:,}")

        target_count = total_count
        if max_results:
            target_count = min(total_count, max_results)
            logger.info(f"Limitado a: {target_count:,}")

        # If there are more than 9999 results, we need to split by periods
        if total_count > PUBMED_MAX_RESULTS:
            logger.warning(f"Query supera límite de {PUBMED_MAX_RESULTS:,} de PubMed. Dividiendo por períodos...")
            # Extract base query (without dates) for subdivision
            base_query = query.split(" AND ")[0] if " AND " in query and "[PDAT]" in query else query
            return self._search_by_time_periods(
                base_query,
                max_results=max_results,
                date_from=date_from,
                date_to=date_to
            )

        all_pmids = []
        retstart = 0
        batch_size = min(batch_size, PUBMED_MAX_RESULTS)

        while retstart < target_count:
            # Calculate size of next batch
            remaining = target_count - retstart
            current_batch = min(batch_size, remaining)

            logger.debug(f"Obteniendo PMIDs {retstart:,} a {retstart + current_batch:,}...")

            pmids = self.search_pmids(query, retmax=current_batch, retstart=retstart)

            if not pmids:
                logger.error("Error en búsqueda")
                break

            all_pmids.extend(pmids)
            logger.debug(f"Obtenidos {len(pmids)} PMIDs")

            retstart += current_batch

        logger.info(f"Total PMIDs obtenidos: {len(all_pmids):,}")
        return all_pmids

    def _search_by_time_periods(
        self,
        base_query: str,
        max_results: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[int]:
        """
        Split large searches into time periods to avoid the 9999 limit.

        Strategy: Search by months. If a month has >9999, search by days.
        """
        from datetime import datetime, timedelta

        PUBMED_MAX_RESULTS = 9999

        # Parse dates
        if date_from:
            start = datetime.strptime(date_from.replace("/", "-"), "%Y-%m-%d")
        else:
            start = datetime(1900, 1, 1)

        if date_to:
            end = datetime.strptime(date_to.replace("/", "-"), "%Y-%m-%d")
        else:
            end = datetime.now()

        all_pmids = set()  # Use set to avoid duplicates
        current = start

        logger.info(f"Buscando desde {start.strftime('%Y/%m/%d')} hasta {end.strftime('%Y/%m/%d')}...")

        while current <= end:
            if max_results and len(all_pmids) >= max_results:
                break

            # Try by month first
            month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            if month_end > end:
                month_end = end

            period_query = f"{base_query} AND {current.strftime('%Y/%m/%d')}:{month_end.strftime('%Y/%m/%d')}[PDAT]"
            count = self.get_total_count(period_query)

            if count == 0:
                logger.debug(f"{current.strftime('%Y/%m')}: 0 artículos")
                current = month_end + timedelta(days=1)
                continue

            if count <= PUBMED_MAX_RESULTS:
                # The month fits in a single search
                logger.debug(f"{current.strftime('%Y/%m')}: {count:,} artículos...")
                pmids = self.search_pmids(period_query, retmax=PUBMED_MAX_RESULTS)
                if pmids:
                    all_pmids.update(pmids)
                    logger.debug(f"{current.strftime('%Y/%m')}: OK")
                else:
                    logger.warning(f"{current.strftime('%Y/%m')}: Error")
                current = month_end + timedelta(days=1)
            else:
                # Month too large, search by days
                logger.info(f"{current.strftime('%Y/%m')}: {count:,} artículos (dividiendo por días)...")
                day_current = current
                while day_current <= month_end:
                    if max_results and len(all_pmids) >= max_results:
                        break

                    day_query = f"{base_query} AND {day_current.strftime('%Y/%m/%d')}[PDAT]"
                    day_count = self.get_total_count(day_query)

                    if day_count > 0:
                        logger.debug(f"{day_current.strftime('%Y/%m/%d')}: {day_count:,}...")
                        if day_count <= PUBMED_MAX_RESULTS:
                            pmids = self.search_pmids(day_query, retmax=PUBMED_MAX_RESULTS)
                            if pmids:
                                all_pmids.update(pmids)
                            else:
                                logger.warning(f"{day_current.strftime('%Y/%m/%d')}: Error")
                        else:
                            # Even a single day has more than 9999 (very rare)
                            logger.warning(f"Demasiados artículos en un día ({day_count}), obteniendo primeros {PUBMED_MAX_RESULTS}")
                            pmids = self.search_pmids(day_query, retmax=PUBMED_MAX_RESULTS)
                            if pmids:
                                all_pmids.update(pmids)

                    day_current += timedelta(days=1)

                current = month_end + timedelta(days=1)

        result = list(all_pmids)
        if max_results:
            result = result[:max_results]

        logger.info(f"Total PMIDs obtenidos: {len(result):,}")
        return result
