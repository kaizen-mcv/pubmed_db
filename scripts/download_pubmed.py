#!/usr/bin/env python3
"""
Script principal de descarga masiva de PubMed.

Uso:
    python download_pubmed.py                  # Descarga nueva
    python download_pubmed.py --resume         # Reanudar descarga
    python download_pubmed.py --incremental    # Solo artículos nuevos (para CRON)
    python download_pubmed.py --config mi.yaml # Configuración personalizada

Características:
- Cumple políticas NCBI (rate limiting)
- Recuperación ante interrupciones
- Filtrado de autores españoles
- Logging completo
- Modo incremental para actualizaciones periódicas
"""

import sys
import os
import argparse
import logging
import signal
import time
from datetime import datetime
from pathlib import Path

# Añadir paths del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.download.pubmed_client import PubMedClient
from src.download.batch_downloader import PubMedBatchDownloader
from src.download.state_manager import DownloadState
from src.services.article_service import ArticleService
from src.database.connection import db


class PubMedDownloader:
    """
    Descargador masivo de PubMed.

    Integra todos los módulos del proyecto:
    - Cliente de PubMed
    - Rate limiting
    - Estado persistente
    - Servicio de artículos
    """

    def __init__(self, config_file: str = None):
        """
        Inicializa el descargador.

        Args:
            config_file: Ruta a configuración YAML personalizada (opcional)
        """
        # Setup logging
        self._setup_logging()

        # Cargar configuración
        self.config = settings.pubmed

        # Estado persistente
        state_file = self.config.get('state', {}).get(
            'state_file', 'data/download_state.json'
        )
        self.state = DownloadState(str(PROJECT_ROOT / state_file))

        # Descargador con rate limiting
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

        # Configuración de lotes
        batch_config = self.config.get('batch', {})
        self.downloader.batch_size = batch_config.get('ids_per_batch', 200)
        self.downloader.max_retries = batch_config.get('max_retries', 3)

        # Frecuencia de guardado
        self.save_frequency = self.config.get('state', {}).get(
            'save_frequency', 100
        )
        self.commit_frequency = self.config.get('database_config', {}).get(
            'commit_frequency', 50
        )

        # Delay entre lotes (margen de seguridad)
        self.batch_delay = batch_config.get('batch_delay', 30)

        # Control de interrupción
        self.interrupted = False
        self._setup_signal_handlers()

        self.logger.info("Sistema inicializado")

    def _setup_logging(self):
        """Configura el sistema de logging."""
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
        """Configura handlers para Ctrl+C."""
        def handler(sig, frame):
            self.logger.warning("\nInterrupción detectada (Ctrl+C)")
            self.interrupted = True

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def download(self, resume: bool = False, incremental: bool = False):
        """
        Ejecuta la descarga.

        Args:
            resume: Si True, continúa descarga previa
            incremental: Si True, solo descarga artículos nuevos desde última ejecución
        """
        if incremental:
            self.logger.info("Modo incremental: solo artículos nuevos")
            # No resetear estado en modo incremental
        elif not resume:
            self.logger.info("Iniciando descarga nueva")
            self.state.reset()
        else:
            self.logger.info("Reanudando descarga previa")

        self.state.start_download()

        # Construir query
        search_config = self.config.get('search', {})
        base_query = search_config.get('query', 'Spain[Affiliation]')

        date_from = search_config.get('date_from')
        date_to = search_config.get('date_to')

        # En modo incremental, usar fecha de última descarga exitosa
        if incremental:
            last_date = self.state.get_last_successful_date()
            if last_date:
                date_from = last_date
                self.logger.info(f"Buscando artículos desde: {date_from}")
            else:
                self.logger.warning("No hay fecha previa, usando date_from de config")
            # date_to siempre es hoy en modo incremental
            date_to = datetime.now().strftime("%Y/%m/%d")

        # Query completa para logging
        query = base_query
        if date_from or date_to:
            query += f" AND {date_from or '1900'}:{date_to or '2100'}[PDAT]"

        self.logger.info(f"Query: {query}")

        # Obtener PMIDs
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

        # Filtrar ya descargados
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

        # Guardar metadata
        self.state.set_metadata("query", query)
        self.state.set_metadata("total_pmids", len(all_pmids))

        # Procesar por lotes
        self._process_batches(pmids_to_download, len(all_pmids))

    def _process_batches(self, pmids: list, total: int):
        """Procesa los PMIDs en lotes."""
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

                # Descargar lote
                records = self.downloader.fetch_batch(batch)

                if not records or "PubmedArticle" not in records:
                    self.logger.warning(f"Lote {batch_num} falló")
                    continue

                # Procesar cada artículo
                # Lista de PMIDs procesados exitosamente en este lote (pendientes de commit)
                pmids_pending_commit = []

                with db.cursor_context() as cur:
                    for article in records["PubmedArticle"]:
                        if self.interrupted:
                            break

                        try:
                            pmid = ArticleService.process_and_save(cur, article)

                            if pmid:
                                # NO marcar como descargado aún - esperar al commit
                                pmids_pending_commit.append(pmid)
                                articles_since_commit += 1

                                # Commit periódico
                                if articles_since_commit >= self.commit_frequency:
                                    db.commit()
                                    # AHORA sí marcar como descargados (después del commit exitoso)
                                    for committed_pmid in pmids_pending_commit:
                                        self.state.mark_downloaded(committed_pmid)
                                        articles_processed += 1
                                    pmids_pending_commit = []
                                    articles_since_commit = 0

                        except Exception as e:
                            pmid = article.get('MedlineCitation', {}).get('PMID', 'unknown')
                            self.logger.error(f"Error PMID {pmid}: {e}")
                            self.state.mark_failed(int(pmid) if pmid != 'unknown' else 0, str(e))
                            # Rollback para recuperar la transacción y continuar
                            db.rollback()
                            # Limpiar PMIDs pendientes ya que el rollback los descartó
                            pmids_pending_commit = []
                            articles_since_commit = 0

                    # Commit final del lote
                    db.commit()
                    # Marcar los restantes como descargados
                    for committed_pmid in pmids_pending_commit:
                        self.state.mark_downloaded(committed_pmid)
                        articles_processed += 1

                # Guardar estado periódicamente
                if articles_processed % self.save_frequency == 0:
                    self.state.save()

                # Mostrar progreso
                progress = self.state.get_progress(total)
                self.logger.info(
                    f"Progreso: {progress.get('percent_complete', 0):.1f}% "
                    f"({progress['downloaded']:,}/{total:,})"
                )

                # Pausa entre lotes para no saturar NCBI
                if not self.interrupted and i + batch_size < len(pmids):
                    self.logger.debug(f"Esperando {self.batch_delay}s antes del siguiente lote...")
                    time.sleep(self.batch_delay)

        except Exception as e:
            self.logger.error(f"Error durante descarga: {e}", exc_info=True)

        finally:
            # Guardar estado final
            self.state.save()
            db.close()

            # Resumen
            self.state.print_summary()

            if self.interrupted:
                self.logger.warning(
                    "Descarga interrumpida. Usa --resume para continuar."
                )
            else:
                # Guardar fecha de descarga exitosa para modo incremental
                self.state.set_last_successful_date(
                    datetime.now().strftime("%Y/%m/%d")
                )
                self.state.save()
                self.logger.info("Descarga completada")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Descarga masiva de artículos de PubMed"
    )
    parser.add_argument(
        "--config",
        help="Ruta a configuración YAML personalizada"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanudar descarga previa"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Solo descargar artículos nuevos desde última ejecución (para CRON)"
    )

    args = parser.parse_args()

    downloader = PubMedDownloader(args.config)
    downloader.download(resume=args.resume, incremental=args.incremental)


if __name__ == "__main__":
    main()
