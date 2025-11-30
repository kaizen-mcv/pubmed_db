#!/usr/bin/env python3
"""
Módulo de rate limiting para cumplir con políticas de NCBI/PubMed.

Política oficial: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- Sin API Key: máx 3 requests/segundo
- Con API Key: máx 10 requests/segundo
- Horas off-peak (fines de semana, 9pm-5am EST): límites más flexibles
"""

import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


class RateLimiter:
    """
    Gestor de rate limiting que cumple con políticas de NCBI.

    Usa token bucket algorithm para control preciso de rate.
    """

    def __init__(
        self,
        requests_per_second: float = 3.0,
        requests_per_second_off_peak: float = 10.0,
        min_delay: float = 0.34,
        min_delay_off_peak: float = 0.1,
    ):
        """
        Inicializa el rate limiter.

        Args:
            requests_per_second: Requests permitidos por segundo (peak hours)
            requests_per_second_off_peak: Requests en horas off-peak
            min_delay: Delay mínimo entre requests (segundos)
            min_delay_off_peak: Delay mínimo en off-peak
        """
        self.requests_per_second = requests_per_second
        self.requests_per_second_off_peak = requests_per_second_off_peak
        self.min_delay = min_delay
        self.min_delay_off_peak = min_delay_off_peak

        # Estado interno
        self.last_request_time: Optional[float] = None
        self.request_count = 0
        self.total_wait_time = 0.0

        # Timezone EST para detectar horas off-peak
        self.est_tz = ZoneInfo("US/Eastern")

    def is_off_peak_hours(self) -> bool:
        """
        Detecta si estamos en horas off-peak según NCBI.

        Off-peak: Weekends o entre 9pm-5am EST en días laborables.

        Returns:
            True si estamos en horas off-peak
        """
        now_est = datetime.now(self.est_tz)

        # Fin de semana (sábado=5, domingo=6)
        if now_est.weekday() in [5, 6]:
            return True

        # Entre 9pm (21:00) y 5am (05:00)
        hour = now_est.hour
        if hour >= 21 or hour < 5:
            return True

        return False

    def wait_if_needed(self) -> float:
        """
        Espera el tiempo necesario para cumplir con rate limit.

        Returns:
            Tiempo esperado en segundos
        """
        if self.last_request_time is None:
            self.last_request_time = time.time()
            self.request_count += 1
            return 0.0

        # Determinar delay según horario
        if self.is_off_peak_hours():
            min_delay = self.min_delay_off_peak
        else:
            min_delay = self.min_delay

        # Calcular tiempo desde último request
        elapsed = time.time() - self.last_request_time

        # Esperar si no ha pasado suficiente tiempo
        if elapsed < min_delay:
            wait_time = min_delay - elapsed
            time.sleep(wait_time)
            self.total_wait_time += wait_time
        else:
            wait_time = 0.0

        # Actualizar estado
        self.last_request_time = time.time()
        self.request_count += 1

        return wait_time

    def get_stats(self) -> dict:
        """
        Retorna estadísticas del rate limiter.

        Returns:
            Diccionario con estadísticas
        """
        return {
            "total_requests": self.request_count,
            "total_wait_time": self.total_wait_time,
            "avg_wait_per_request": (
                self.total_wait_time / self.request_count
                if self.request_count > 0
                else 0.0
            ),
            "is_off_peak": self.is_off_peak_hours(),
            "current_rate_limit": (
                self.requests_per_second_off_peak
                if self.is_off_peak_hours()
                else self.requests_per_second
            ),
        }

    def reset(self):
        """Reinicia las estadísticas del rate limiter."""
        self.last_request_time = None
        self.request_count = 0
        self.total_wait_time = 0.0


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter adaptativo que ajusta el rate según errores HTTP 429.

    Si recibimos 429 (Too Many Requests), reduce automáticamente el rate.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_429_count = 0
        self.rate_reduction_factor = 0.8  # Reducir al 80% tras error 429

    def handle_429_error(self):
        """
        Ajusta el rate limit tras recibir error 429.

        Reduce el rate al 80% del actual y aumenta delays.
        """
        self.error_429_count += 1

        # Reducir rate
        self.requests_per_second *= self.rate_reduction_factor
        self.requests_per_second_off_peak *= self.rate_reduction_factor

        # Aumentar delays
        self.min_delay /= self.rate_reduction_factor
        self.min_delay_off_peak /= self.rate_reduction_factor

        # Esperar más tiempo antes del siguiente request
        time.sleep(self.min_delay * 3)

    def get_stats(self) -> dict:
        """Retorna estadísticas incluyendo errores 429."""
        stats = super().get_stats()
        stats["error_429_count"] = self.error_429_count
        return stats
