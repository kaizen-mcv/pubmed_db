"""
Cliente de PubMed.

Wrapper simplificado que usa PubMedBatchDownloader internamente.
Proporciona una interfaz limpia para operaciones comunes.

NOTA: Para descargas grandes o con rate limiting avanzado,
usar PubMedBatchDownloader directamente.
"""

from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings
from src.download.batch_downloader import PubMedBatchDownloader


class PubMedClient:
    """
    Cliente simplificado para la API de PubMed (NCBI Entrez).

    Usa PubMedBatchDownloader internamente para:
    - Rate limiting automático
    - Reintentos con backoff
    - Manejo de errores HTTP

    Para operaciones avanzadas o descargas masivas,
    usar PubMedBatchDownloader directamente.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Inicializa el cliente de PubMed.

        Args:
            email: Email requerido por NCBI (usa config si no se proporciona)
            api_key: API Key opcional para mayor rate limit
        """
        download_config = settings.pubmed.get('download', {})

        self.email = email or download_config.get('email')
        self.api_key = api_key or download_config.get('api_key')

        if not self.email:
            raise ValueError(
                "Email requerido por NCBI. "
                "Configúralo en config/pubmed_config.yaml"
            )

        # Usar batch_downloader internamente
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
        Busca PMIDs que coinciden con una query.

        Args:
            query: Query de búsqueda de PubMed
            retmax: Máximo de resultados a retornar
            retstart: Offset de inicio

        Returns:
            Lista de PMIDs encontrados
        """
        return self._downloader.search_pmids(query, retmax=retmax, retstart=retstart)

    def get_count(self, query: str) -> int:
        """
        Obtiene el número total de resultados para una query.

        Args:
            query: Query de búsqueda

        Returns:
            Número total de artículos
        """
        return self._downloader.get_total_count(query)

    def fetch(
        self,
        pmids: List[int],
        rettype: str = "xml",
        retmode: str = "xml"
    ) -> Optional[Dict[str, Any]]:
        """
        Descarga artículos por sus PMIDs.

        Args:
            pmids: Lista de PMIDs a descargar
            rettype: Tipo de retorno (xml, medline, etc.)
            retmode: Modo de retorno

        Returns:
            Registros descargados o None si falla
        """
        return self._downloader.fetch_batch(pmids, rettype=rettype, retmode=retmode)

    def fetch_single(self, pmid: int) -> Optional[Dict[str, Any]]:
        """
        Descarga un solo artículo.

        Args:
            pmid: PMID del artículo

        Returns:
            Datos del artículo o None
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
        Busca TODOS los PMIDs que coinciden con una query.

        Usa paginación automática y división por períodos si excede límite de 9999.

        Args:
            query: Query de búsqueda
            batch_size: Tamaño de cada página (max 9,999 por límite de PubMed)
            max_results: Máximo de resultados (None = sin límite)
            date_from: Fecha inicio formato YYYY/MM/DD
            date_to: Fecha fin formato YYYY/MM/DD

        Returns:
            Lista completa de PMIDs
        """
        return self._downloader.search_all_pmids(
            query,
            batch_size=batch_size,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
        )
