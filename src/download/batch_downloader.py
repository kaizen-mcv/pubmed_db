#!/usr/bin/env python3
"""
Descargador por lotes de artículos de PubMed.

Cumple estrictamente con políticas de NCBI:
- Rate limiting configurable
- Gestión de errores y reintentos
- Descarga por lotes eficiente
- Recuperación ante interrupciones
"""

import sys
import os
import time
from typing import List, Optional, Dict, Any
from Bio import Entrez
from urllib.error import HTTPError

# Importar módulos del proyecto
sys.path.insert(0, os.path.dirname(__file__))
from rate_limiter import AdaptiveRateLimiter


class PubMedBatchDownloader:
    """
    Descargador por lotes que cumple con políticas de NCBI.

    Características:
    - Rate limiting automático
    - Reintentos con backoff exponencial
    - Descarga eficiente por lotes
    - Manejo robusto de errores
    """

    def __init__(
        self,
        email: str,
        api_key: Optional[str] = None,
        requests_per_second: float = 3.0,
        requests_per_second_off_peak: float = 10.0,
    ):
        """
        Inicializa el descargador.

        Args:
            email: Email requerido por NCBI
            api_key: API Key opcional (aumenta límite a 10 req/s)
            requests_per_second: Límite de requests/segundo
            requests_per_second_off_peak: Límite en horas off-peak
        """
        # Configurar Entrez
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
            # Con API key, usar límite mayor por defecto
            if requests_per_second == 3.0:
                requests_per_second = 10.0

        # Rate limiter adaptativo
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_second=requests_per_second,
            requests_per_second_off_peak=requests_per_second_off_peak,
        )

        # Configuración
        self.max_retries = 3
        self.retry_delay = 5
        self.batch_size = 200  # IDs por batch (efetch acepta hasta 500)

    def search_pmids(
        self,
        query: str,
        retmax: int = 10000,
        retstart: int = 0,
    ) -> List[int]:
        """
        Busca PMIDs usando esearch.

        Args:
            query: Query de búsqueda de PubMed
            retmax: Número máximo de resultados a retornar
            retstart: Offset de inicio

        Returns:
            Lista de PMIDs encontrados
        """
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self.rate_limiter.wait_if_needed()

                # Búsqueda
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=retmax,
                    retstart=retstart,
                    usehistory="y",  # Usar history server para grandes queries
                )
                record = Entrez.read(handle)
                handle.close()

                pmids = [int(pmid) for pmid in record["IdList"]]
                return pmids

            except HTTPError as e:
                if e.code == 429:
                    # Too many requests
                    self.rate_limiter.handle_429_error()
                    print(f"⚠ Rate limit excedido, reduciendo velocidad...")
                    continue

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠ Error HTTP {e.code}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠ Error en búsqueda: {e}, reintentando en {wait_time}s...")
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
        Descarga un lote de artículos usando efetch.

        Args:
            pmids: Lista de PMIDs a descargar
            rettype: Tipo de retorno (xml, medline, etc.)
            retmode: Modo de retorno

        Returns:
            Registros descargados o None si falla
        """
        if not pmids:
            return None

        # Convertir lista a string separada por comas
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
                    print(f"⚠ Rate limit excedido, reduciendo velocidad...")
                    continue

                if e.code == 400:
                    # Bad request, no reintentar
                    print(f"✗ Error 400 para PMIDs: {pmids[:5]}... (request inválido)")
                    return None

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠ Error HTTP {e.code}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Error HTTP {e.code} tras {self.max_retries} intentos")
                    return None

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠ Error en fetch: {e}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Error tras {self.max_retries} intentos: {e}")
                    return None

        return None

    def fetch_single(
        self,
        pmid: int,
        rettype: str = "xml",
        retmode: str = "xml",
    ) -> Optional[Any]:
        """
        Descarga un artículo individual.

        Args:
            pmid: PMID a descargar
            rettype: Tipo de retorno
            retmode: Modo de retorno

        Returns:
            Registro descargado o None si falla
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
        Descarga lista de PMIDs en lotes.

        Args:
            pmids: Lista de PMIDs a descargar
            callback: Función callback(article_data) llamada por cada artículo
            batch_size: Tamaño de lote (None = usar default)

        Returns:
            Estadísticas de la descarga
        """
        if batch_size is None:
            batch_size = self.batch_size

        total = len(pmids)
        downloaded = 0
        failed = 0

        print(f"Descargando {total:,} artículos en lotes de {batch_size}...")

        for i in range(0, total, batch_size):
            batch = pmids[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            print(f"\nLote {batch_num}/{total_batches} ({len(batch)} PMIDs)...", end=" ")

            records = self.fetch_batch(batch)

            if records and "PubmedArticle" in records:
                articles = records["PubmedArticle"]

                for article in articles:
                    try:
                        if callback:
                            callback(article)
                        downloaded += 1
                    except Exception as e:
                        print(f"\n  ✗ Error procesando artículo: {e}")
                        failed += 1

                print(f"✓ {len(articles)} artículos")
            else:
                print(f"✗ Lote falló")
                failed += len(batch)

        # Estadísticas finales
        stats = {
            "total": total,
            "downloaded": downloaded,
            "failed": failed,
            "rate_limiter_stats": self.rate_limiter.get_stats(),
        }

        return stats

    def get_total_count(self, query: str) -> int:
        """
        Obtiene el conteo total de resultados para una query.

        Args:
            query: Query de búsqueda

        Returns:
            Número total de artículos que coinciden
        """
        try:
            self.rate_limiter.wait_if_needed()

            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=0,  # Solo queremos el count
            )
            record = Entrez.read(handle)
            handle.close()

            return int(record["Count"])

        except Exception as e:
            print(f"✗ Error obteniendo conteo: {e}")
            return 0

    def search_all_pmids(
        self,
        query: str,
        batch_size: int = 10000,
        max_results: Optional[int] = None,
    ) -> List[int]:
        """
        Busca TODOS los PMIDs que coinciden con una query.

        Usa paginación para queries grandes (>10,000 resultados).

        Args:
            query: Query de búsqueda
            batch_size: Tamaño de cada página (max 10,000)
            max_results: Máximo de resultados (None = sin límite)

        Returns:
            Lista completa de PMIDs
        """
        # Obtener conteo total
        total_count = self.get_total_count(query)
        print(f"Total de artículos encontrados: {total_count:,}")

        if max_results:
            total_count = min(total_count, max_results)
            print(f"Limitado a: {total_count:,}")

        all_pmids = []
        retstart = 0

        while retstart < total_count:
            # Calcular tamaño del siguiente lote
            remaining = total_count - retstart
            current_batch = min(batch_size, remaining)

            print(f"Obteniendo PMIDs {retstart:,} a {retstart + current_batch:,}...", end=" ")

            pmids = self.search_pmids(query, retmax=current_batch, retstart=retstart)

            if not pmids:
                print("✗ Error en búsqueda")
                break

            all_pmids.extend(pmids)
            print(f"✓ {len(pmids)} PMIDs")

            retstart += current_batch

        print(f"\nTotal PMIDs obtenidos: {len(all_pmids):,}")
        return all_pmids
