#!/usr/bin/env python3
"""
State manager to resume interrupted downloads.

Saves progress to a JSON file so the download can continue after:
- Manual interruptions (Ctrl+C)
- Network errors
- System errors
- Server restarts
"""

import json
import os
from datetime import datetime
from typing import Optional, Set, Dict, Any
from pathlib import Path


class DownloadState:
    """
    Persistent state manager for PubMed downloads.

    Keeps track of:
    - PMIDs already downloaded
    - PMIDs with errors
    - Download progress
    - Statistics
    """

    def __init__(self, state_file: str):
        """
        Initialize the state manager.

        Args:
            state_file: Path to the JSON state file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory state
        self.downloaded_pmids: Set[int] = set()
        self.failed_pmids: Set[int] = set()
        self.metadata: Dict[str, Any] = {}

        # Statistics
        self.stats = {
            "total_downloaded": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "start_time": None,
            "last_update": None,
            "last_saved": None,
            "last_successful_date": None,  # For incremental mode
        }

        # Load existing state if any
        self.load()

    def load(self):
        """Load state from JSON file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)

            # Restore sets
            self.downloaded_pmids = set(data.get("downloaded_pmids", []))
            self.failed_pmids = set(data.get("failed_pmids", []))

            # Restore metadata
            self.metadata = data.get("metadata", {})

            # Restore statistics
            self.stats = data.get("stats", self.stats)

            print(f"✓ Estado cargado: {len(self.downloaded_pmids)} PMIDs descargados, "
                  f"{len(self.failed_pmids)} fallidos")

        except Exception as e:
            print(f"⚠ Error cargando estado: {e}")
            print("  Iniciando con estado limpio")

    def save(self):
        """Save the current state to JSON file."""
        try:
            # Update timestamp
            self.stats["last_saved"] = datetime.now().isoformat()

            data = {
                "downloaded_pmids": list(self.downloaded_pmids),
                "failed_pmids": list(self.failed_pmids),
                "metadata": self.metadata,
                "stats": self.stats,
            }

            # Write to a temp file first (atomic write)
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            # Move temp file to the final one
            temp_file.replace(self.state_file)

        except Exception as e:
            print(f"⚠ Error guardando estado: {e}")

    def mark_downloaded(self, pmid: int):
        """
        Mark a PMID as successfully downloaded.

        Args:
            pmid: Downloaded PubMed ID
        """
        self.downloaded_pmids.add(pmid)
        self.stats["total_downloaded"] += 1
        self.stats["last_update"] = datetime.now().isoformat()

        # Remove from failed if it was there
        if pmid in self.failed_pmids:
            self.failed_pmids.remove(pmid)

    def mark_failed(self, pmid: int, error: str = ""):
        """
        Mark a PMID as failed.

        Args:
            pmid: PubMed ID that failed
            error: Error message (optional)
        """
        self.failed_pmids.add(pmid)
        self.stats["total_failed"] += 1
        self.stats["last_update"] = datetime.now().isoformat()

        # Save error info in metadata
        if error:
            if "errors" not in self.metadata:
                self.metadata["errors"] = {}
            self.metadata["errors"][str(pmid)] = error

    def is_downloaded(self, pmid: int) -> bool:
        """
        Check whether a PMID has already been downloaded.

        Args:
            pmid: PubMed ID to check

        Returns:
            True if already downloaded successfully
        """
        return pmid in self.downloaded_pmids

    def is_failed(self, pmid: int) -> bool:
        """
        Check whether a PMID failed previously.

        Args:
            pmid: PubMed ID to check

        Returns:
            True if it failed in a previous attempt
        """
        return pmid in self.failed_pmids

    def get_progress(self, total_pmids: Optional[int] = None) -> dict:
        """
        Return progress information.

        Args:
            total_pmids: Total PMIDs to download (optional)

        Returns:
            Dictionary with progress information
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

        # Calculate speed
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
        Save additional metadata.

        Args:
            key: Metadata key
            value: Value to save
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata.

        Args:
            key: Metadata key
            default: Default value if it does not exist

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def start_download(self):
        """Start a download session (records the start timestamp)."""
        if not self.stats["start_time"]:
            self.stats["start_time"] = datetime.now().isoformat()

    def reset(self):
        """Completely reset state (use with care!)."""
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
        Get the date of the last successful download.

        Returns:
            Date in YYYY/MM/DD format or None if none
        """
        return self.stats.get("last_successful_date")

    def set_last_successful_date(self, date_str: str):
        """
        Save the date of the last successful download.

        Args:
            date_str: Date in YYYY/MM/DD format
        """
        self.stats["last_successful_date"] = date_str

    def print_summary(self):
        """Print a summary of the current state."""
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
