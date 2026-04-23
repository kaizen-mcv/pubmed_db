#!/usr/bin/env python3
"""Main script for bulk PubMed download.

Usage:
    python download_pubmed.py                   # New download
    python download_pubmed.py --resume          # Resume download
    python download_pubmed.py --incremental     # Only new articles (for CRON)
    python download_pubmed.py --config mi.yaml  # Custom configuration

Features:
- Complies with NCBI policies (rate limiting).
- Recovery from interruptions.
- Filtering of Spanish authors.
- Complete logging.
- Incremental mode for periodic updates.
"""

import sys
import os
import argparse
import logging
import signal
import time
from datetime import datetime
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.download.pubmed_client import PubMedClient
from src.download.batch_downloader import PubMedBatchDownloader
from src.download.state_manager import DownloadState
from src.services.article_service import ArticleService
from src.database.connection import db


class PubMedDownloader:
    """Bulk PubMed downloader.

    Integrates all project modules:
    - PubMed client
    - Rate limiting
    - Persistent state
    - Article service
    """

    def __init__(self, config_file: str = None):
        """Initializes the downloader.

        Args:
            config_file: Path to a custom YAML configuration (optional).
        """
        # Setup logging
        self._setup_logging()

        # Load configuration
        self.config = settings.pubmed

        # Persistent state
        state_file = self.config.get('state', {}).get(
            'state_file', 'data/download_state.json'
        )
        self.state = DownloadState(str(PROJECT_ROOT / state_file))

        # Downloader with rate limiting
        download_config = self.config.get('download', {})
        rate_config = self.config.get('rate_limiting', {})

        self.downloader = PubMedBatchDownloader(
            email=download_config.get('email'),
            api_key=download_config.get('api_key'),
            requests_per_second=rate_config.get('requests_per_second', 3),
            requests_per_second_off_peak=rate_config.get(
                'requests_per_second_off_peak', 10
            ),
        )

        # Batch configuration
        batch_config = self.config.get('batch', {})
        self.downloader.batch_size = batch_config.get('ids_per_batch', 200)
        self.downloader.max_retries = batch_config.get('max_retries', 3)

        # Save frequency
        self.save_frequency = self.config.get('state', {}).get(
            'save_frequency', 100
        )
        self.commit_frequency = self.config.get('database_config', {}).get(
            'commit_frequency', 50
        )

        # Delay between batches (safety margin)
        self.batch_delay = batch_config.get('batch_delay', 30)

        # Interruption control
        self.interrupted = False
        self._setup_signal_handlers()

        self.logger.info("Sistema inicializado")

    def _setup_logging(self):
        """Configures the logging system."""
        log_dir = PROJECT_ROOT / 'data' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        log_level = settings.pubmed.get('state', {}).get('log_level', 'INFO')

        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout),
            ],
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Log: {log_file}")

    def _setup_signal_handlers(self):
        """Configures handlers for Ctrl+C."""
        def handler(sig, frame):
            self.logger.warning("\nInterrupción detectada (Ctrl+C)")
            self.interrupted = True

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def download(self, resume: bool = False, incremental: bool = False):
        """Runs the download.

        Args:
            resume: If True, continues a previous download.
            incremental: If True, only downloads new articles since the last run.
        """
        if incremental:
            self.logger.info("Modo incremental: solo artículos nuevos")
            # Do not reset state in incremental mode
        elif not resume:
            self.logger.info("Iniciando descarga nueva")
            self.state.reset()
        else:
            self.logger.info("Reanudando descarga previa")

        self.state.start_download()

        # Build query
        search_config = self.config.get('search', {})
        base_query = search_config.get('query', 'Spain[Affiliation]')

        date_from = search_config.get('date_from')
        date_to = search_config.get('date_to')

        # In incremental mode, use the date of the last successful download
        if incremental:
            last_date = self.state.get_last_successful_date()
            if last_date:
                date_from = last_date
                self.logger.info(f"Buscando artículos desde: {date_from}")
            else:
                self.logger.warning("No hay fecha previa, usando date_from de config")
            # date_to is always today in incremental mode
            date_to = datetime.now().strftime("%Y/%m/%d")

        # Full query for logging
        query = base_query
        if date_from or date_to:
            query += f" AND {date_from or '1900'}:{date_to or '2100'}[PDAT]"

        self.logger.info(f"Query: {query}")

        # Fetch PMIDs
        max_articles = search_config.get('max_articles')
        batch_config = self.config.get('batch', {})

        self.logger.info("Obteniendo lista de PMIDs...")
        all_pmids = self.downloader.search_all_pmids(
            query,
            batch_size=batch_config.get('search_batch_size', 9999),
            max_results=max_articles,
            date_from=date_from,
            date_to=date_to,
        )

        if not all_pmids:
            self.logger.error("No se encontraron PMIDs")
            return

        # Filter already downloaded
        pmids_to_download = [
            pmid for pmid in all_pmids
            if not self.state.is_downloaded(pmid)
        ]

        self.logger.info(f"PMIDs totales: {len(all_pmids):,}")
        self.logger.info(f"Ya descargados: {len(all_pmids) - len(pmids_to_download):,}")
        self.logger.info(f"A descargar: {len(pmids_to_download):,}")

        if not pmids_to_download:
            self.logger.info("Todos los artículos ya fueron descargados")
            return

        # Save metadata
        self.state.set_metadata("query", query)
        self.state.set_metadata("total_pmids", len(all_pmids))

        # Process in batches
        self._process_batches(pmids_to_download, len(all_pmids))

    def _process_batches(self, pmids: list, total: int):
        """Processes the PMIDs in batches."""
        batch_size = self.downloader.batch_size
        articles_processed = 0
        articles_since_commit = 0

        try:
            for i in range(0, len(pmids), batch_size):
                if self.interrupted:
                    break

                batch = pmids[i:i + batch_size]
                batch_num = i // batch_size + 1

                self.logger.info(f"Lote {batch_num} ({len(batch)} PMIDs)...")

                # Download batch
                records = self.downloader.fetch_batch(batch)

                if not records or "PubmedArticle" not in records:
                    self.logger.warning(f"Lote {batch_num} falló")
                    continue

                # Process each article
                # List of PMIDs successfully processed in this batch (pending commit)
                pmids_pending_commit = []

                with db.cursor_context() as cur:
                    for article in records["PubmedArticle"]:
                        if self.interrupted:
                            break

                        try:
                            pmid = ArticleService.process_and_save(cur, article)

                            if pmid:
                                # Do NOT mark as downloaded yet - wait for commit
                                pmids_pending_commit.append(pmid)
                                articles_since_commit += 1

                                # Periodic commit
                                if articles_since_commit >= self.commit_frequency:
                                    db.commit()
                                    # NOW mark as downloaded (after successful commit)
                                    for committed_pmid in pmids_pending_commit:
                                        self.state.mark_downloaded(committed_pmid)
                                        articles_processed += 1
                                    pmids_pending_commit = []
                                    articles_since_commit = 0

                        except Exception as e:
                            pmid = article.get('MedlineCitation', {}).get('PMID', 'unknown')
                            self.logger.error(f"Error PMID {pmid}: {e}")
                            self.state.mark_failed(int(pmid) if pmid != 'unknown' else 0, str(e))
                            # Rollback to recover the transaction and continue
                            db.rollback()
                            # Clear pending PMIDs since the rollback discarded them
                            pmids_pending_commit = []
                            articles_since_commit = 0

                    # Final commit of the batch
                    db.commit()
                    # Mark the remaining ones as downloaded
                    for committed_pmid in pmids_pending_commit:
                        self.state.mark_downloaded(committed_pmid)
                        articles_processed += 1

                # Save state periodically
                if articles_processed % self.save_frequency == 0:
                    self.state.save()

                # Show progress
                progress = self.state.get_progress(total)
                self.logger.info(
                    f"Progreso: {progress.get('percent_complete', 0):.1f}% "
                    f"({progress['downloaded']:,}/{total:,})"
                )

                # Pause between batches to avoid saturating NCBI
                if not self.interrupted and i + batch_size < len(pmids):
                    self.logger.debug(f"Esperando {self.batch_delay}s antes del siguiente lote...")
                    time.sleep(self.batch_delay)

        except Exception as e:
            self.logger.error(f"Error durante descarga: {e}", exc_info=True)

        finally:
            # Save final state
            self.state.save()
            db.close()

            # Summary
            self.state.print_summary()

            if self.interrupted:
                self.logger.warning(
                    "Descarga interrumpida. Usa --resume para continuar."
                )
            else:
                # Save successful download date for incremental mode
                self.state.set_last_successful_date(
                    datetime.now().strftime("%Y/%m/%d")
                )
                self.state.save()
                self.logger.info("Descarga completada")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Bulk download of PubMed articles"
    )
    parser.add_argument(
        "--config",
        help="Path to a custom YAML configuration"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume previous download"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only download new articles since the last run (for CRON)"
    )

    args = parser.parse_args()

    downloader = PubMedDownloader(args.config)
    downloader.download(resume=args.resume, incremental=args.incremental)


if __name__ == "__main__":
    main()
