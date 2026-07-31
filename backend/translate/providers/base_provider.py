"""
Base Translation Provider
=========================
Interface yang harus diimplementasi oleh semua provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class BaseTranslationProvider(ABC):
    """Interface provider terjemahan."""

    name: str = "base"

    @abstractmethod
    def initialize(self) -> bool:
        """Inisialisasi provider. Return True jika berhasil."""
        ...

    @abstractmethod
    def translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str
    ) -> List[str]:
        """
        Terjemahkan batch teks.
        Return list hasil terjemahan dengan panjang sama dengan input.
        """
        ...

    def health_check(self) -> bool:
        """Cek apakah provider online/tersedia."""
        return True

    def shutdown(self) -> None:
        """Cleanup resources."""
        pass
