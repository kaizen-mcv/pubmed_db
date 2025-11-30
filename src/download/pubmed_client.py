"""
Cliente de PubMed.

Wrapper limpio de Entrez para búsquedas y descargas.
"""

from typing import Any, Dict, List, Optional

from Bio import Entrez

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings


class PubMedClient:
    """
    Cliente para la API de PubMed (NCBI Entrez).

    Proporciona métodos simplificados para:
    - Buscar PMIDs (esearch)
    - Descargar artículos (efetch)
    - Obtener conteos (esearch count)
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

        # Configurar Entrez
        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key

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
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=retmax,
            retstart=retstart,
            usehistory="y",
        )
        record = Entrez.read(handle)
        handle.close()

        return [int(pmid) for pmid in record.get("IdList", [])]

    def get_count(self, query: str) -> int:
        """
        Obtiene el número total de resultados para una query.

        Args:
            query: Query de búsqueda

        Returns:
            Número total de artículos
        """
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=0,
        )
        record = Entrez.read(handle)
        handle.close()

        return int(record.get("Count", 0))

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
        if not pmids:
            return None

        id_list = ",".join(str(pmid) for pmid in pmids)

        handle = Entrez.efetch(
            db="pubmed",
            id=id_list,
            rettype=rettype,
            retmode=retmode,
        )
        records = Entrez.read(handle)
        handle.close()

        return records

    def fetch_single(self, pmid: int) -> Optional[Dict[str, Any]]:
        """
        Descarga un solo artículo.

        Args:
            pmid: PMID del artículo

        Returns:
            Datos del artículo o None
        """
        records = self.fetch([pmid])

        if records and "PubmedArticle" in records:
            if records["PubmedArticle"]:
                return records["PubmedArticle"][0]

        return None

    def search_all(
        self,
        query: str,
        batch_size: int = 10000,
        max_results: Optional[int] = None
    ) -> List[int]:
        """
        Busca TODOS los PMIDs que coinciden con una query.

        Usa paginación para queries grandes.

        Args:
            query: Query de búsqueda
            batch_size: Tamaño de cada página (max 10,000)
            max_results: Máximo de resultados (None = sin límite)

        Returns:
            Lista completa de PMIDs
        """
        total_count = self.get_count(query)

        if max_results:
            total_count = min(total_count, max_results)

        all_pmids = []
        retstart = 0

        while retstart < total_count:
            remaining = total_count - retstart
            current_batch = min(batch_size, remaining)

            pmids = self.search(query, retmax=current_batch, retstart=retstart)

            if not pmids:
                break

            all_pmids.extend(pmids)
            retstart += current_batch

        return all_pmids
