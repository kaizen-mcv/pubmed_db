#!/usr/bin/env python3
"""
Gestor de estado para reanudar descargas interrumpidas.

Guarda progreso en archivo JSON para poder continuar tras:
- Interrupciones manuales (Ctrl+C)
- Errores de red
- Errores de sistema
- Reinicios del servidor
"""

import json
import os
from datetime import datetime
from typing import Optional, Set, Dict, Any
from pathlib import Path


class DownloadState:
    """
    Gestor de estado persistente para descargas de PubMed.

    Mantiene registro de:
    - PMIDs ya descargados
    - PMIDs con error
    - Progreso de la descarga
    - Estadísticas
    """

    def __init__(self, state_file: str):
        """
        Inicializa el gestor de estado.

        Args:
            state_file: Ruta al archivo de estado JSON
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Estado en memoria
        self.downloaded_pmids: Set[int] = set()
        self.failed_pmids: Set[int] = set()
        self.metadata: Dict[str, Any] = {}

        # Estadísticas
        self.stats = {
            "total_downloaded": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "start_time": None,
            "last_update": None,
            "last_saved": None,
            "last_successful_date": None,  # Para modo incremental
        }

        # Cargar estado existente si hay
        self.load()

    def load(self):
        """Carga el estado desde archivo JSON."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)

            # Restaurar sets
            self.downloaded_pmids = set(data.get("downloaded_pmids", []))
            self.failed_pmids = set(data.get("failed_pmids", []))

            # Restaurar metadata
            self.metadata = data.get("metadata", {})

            # Restaurar estadísticas
            self.stats = data.get("stats", self.stats)

            print(f"✓ Estado cargado: {len(self.downloaded_pmids)} PMIDs descargados, "
                  f"{len(self.failed_pmids)} fallidos")

        except Exception as e:
            print(f"⚠ Error cargando estado: {e}")
            print("  Iniciando con estado limpio")

    def save(self):
        """Guarda el estado actual a archivo JSON."""
        try:
            # Actualizar timestamp
            self.stats["last_saved"] = datetime.now().isoformat()

            data = {
                "downloaded_pmids": list(self.downloaded_pmids),
                "failed_pmids": list(self.failed_pmids),
                "metadata": self.metadata,
                "stats": self.stats,
            }

            # Guardar a archivo temporal primero (atomic write)
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            # Mover archivo temporal al definitivo
            temp_file.replace(self.state_file)

        except Exception as e:
            print(f"⚠ Error guardando estado: {e}")

    def mark_downloaded(self, pmid: int):
        """
        Marca un PMID como descargado exitosamente.

        Args:
            pmid: PubMed ID descargado
        """
        self.downloaded_pmids.add(pmid)
        self.stats["total_downloaded"] += 1
        self.stats["last_update"] = datetime.now().isoformat()

        # Remover de fallidos si estaba
        if pmid in self.failed_pmids:
            self.failed_pmids.remove(pmid)

    def mark_failed(self, pmid: int, error: str = ""):
        """
        Marca un PMID como fallido.

        Args:
            pmid: PubMed ID que falló
            error: Mensaje de error (opcional)
        """
        self.failed_pmids.add(pmid)
        self.stats["total_failed"] += 1
        self.stats["last_update"] = datetime.now().isoformat()

        # Guardar info del error en metadata
        if error:
            if "errors" not in self.metadata:
                self.metadata["errors"] = {}
            self.metadata["errors"][str(pmid)] = error

    def is_downloaded(self, pmid: int) -> bool:
        """
        Verifica si un PMID ya fue descargado.

        Args:
            pmid: PubMed ID a verificar

        Returns:
            True si ya fue descargado exitosamente
        """
        return pmid in self.downloaded_pmids

    def is_failed(self, pmid: int) -> bool:
        """
        Verifica si un PMID falló previamente.

        Args:
            pmid: PubMed ID a verificar

        Returns:
            True si falló en intento previo
        """
        return pmid in self.failed_pmids

    def get_progress(self, total_pmids: Optional[int] = None) -> dict:
        """
        Retorna información de progreso.

        Args:
            total_pmids: Total de PMIDs a descargar (opcional)

        Returns:
            Diccionario con información de progreso
        """
        downloaded = len(self.downloaded_pmids)
        failed = len(self.failed_pmids)
        processed = downloaded + failed

        progress = {
            "downloaded": downloaded,
            "failed": failed,
            "processed": processed,
            "stats": self.stats.copy(),
        }

        if total_pmids is not None:
            progress["total"] = total_pmids
            progress["remaining"] = total_pmids - processed
            progress["percent_complete"] = (
                (processed / total_pmids * 100) if total_pmids > 0 else 0
            )

        # Calcular velocidad
        if self.stats["start_time"]:
            start = datetime.fromisoformat(self.stats["start_time"])
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed > 0:
                progress["articles_per_second"] = processed / elapsed
                progress["elapsed_time"] = elapsed

                if total_pmids and processed > 0:
                    estimated_total = (total_pmids / processed) * elapsed
                    progress["estimated_remaining_seconds"] = estimated_total - elapsed

        return progress

    def set_metadata(self, key: str, value: Any):
        """
        Guarda metadata adicional.

        Args:
            key: Clave del metadata
            value: Valor a guardar
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Obtiene metadata.

        Args:
            key: Clave del metadata
            default: Valor por defecto si no existe

        Returns:
            Valor del metadata o default
        """
        return self.metadata.get(key, default)

    def start_download(self):
        """Inicia una sesión de descarga (registra timestamp de inicio)."""
        if not self.stats["start_time"]:
            self.stats["start_time"] = datetime.now().isoformat()

    def reset(self):
        """Reinicia el estado completamente (¡usar con cuidado!)."""
        self.downloaded_pmids.clear()
        self.failed_pmids.clear()
        self.metadata.clear()
        self.stats = {
            "total_downloaded": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "start_time": None,
            "last_update": None,
            "last_saved": None,
            "last_successful_date": None,
        }
        self.save()

    def get_last_successful_date(self) -> Optional[str]:
        """
        Obtiene la fecha de la última descarga exitosa.

        Returns:
            Fecha en formato YYYY/MM/DD o None si no hay
        """
        return self.stats.get("last_successful_date")

    def set_last_successful_date(self, date_str: str):
        """
        Guarda la fecha de la última descarga exitosa.

        Args:
            date_str: Fecha en formato YYYY/MM/DD
        """
        self.stats["last_successful_date"] = date_str

    def print_summary(self):
        """Imprime un resumen del estado actual."""
        progress = self.get_progress()

        print("\n" + "=" * 60)
        print("RESUMEN DE DESCARGA")
        print("=" * 60)
        print(f"Descargados:  {progress['downloaded']:,}")
        print(f"Fallidos:     {progress['failed']:,}")
        print(f"Procesados:   {progress['processed']:,}")

        if "articles_per_second" in progress:
            print(f"\nVelocidad:    {progress['articles_per_second']:.2f} artículos/seg")
            print(f"Tiempo:       {progress['elapsed_time'] / 3600:.2f} horas")

        if "percent_complete" in progress:
            print(f"Progreso:     {progress['percent_complete']:.1f}%")

            if "estimated_remaining_seconds" in progress:
                remaining_hours = progress["estimated_remaining_seconds"] / 3600
                print(f"Estimado restante: {remaining_hours:.1f} horas")

        print("=" * 60 + "\n")
