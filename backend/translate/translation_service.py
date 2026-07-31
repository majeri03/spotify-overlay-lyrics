"""
Translation Service
===================
Orchestrator terjemahan.
Mendengarkan LYRICS_FOUND, menerjemahkan di background thread,
lalu emit TRANSLATION_READY.

Priority cache: Memory Cache → SQLite → Provider (Google → MyMemory fallback)

Perbaikan:
- Batch translation (1 request untuk semua baris)
- Fallback ke MyMemory jika Google gagal
- Language detector threshold lebih ketat (95%)
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Dict, List, Optional

from backend.translate.language_detector import detect_language, is_already_target
from backend.translate.formatter import format_translation, check_quality
from backend.translate.providers.google_provider import GoogleTranslateProvider
from backend.translate.providers.mymemory_provider import MyMemoryProvider
from backend.database.repositories.lyrics_repo import LyricsRepository
from backend.database.repositories.translation_repo import TranslationRepository
from backend.models.models import SubtitleLine, TrackTimeline, TranslationResult
from backend.events.event_bus import EventBus
from backend.events.event_types import EventType
from backend.logger.app_logger import app_logger

_WORKERS     = 2
_TARGET_LANG = "id"
_SOURCE_LANG = "en"


class TranslationService:
    def __init__(
        self,
        event_bus: EventBus,
        lyrics_repo: LyricsRepository,
        translation_repo: TranslationRepository,
    ) -> None:
        self._bus             = event_bus
        self._lyrics_repo     = lyrics_repo
        self._translation_repo = translation_repo
        self._primary   = GoogleTranslateProvider()
        self._fallback  = MyMemoryProvider()
        self._executor  = concurrent.futures.ThreadPoolExecutor(max_workers=_WORKERS)
        self._memory_cache: Dict[str, List[str]] = {}  # track_id → translations
        self._lock = threading.Lock()

        self._bus.subscribe(EventType.LYRICS_FOUND, self._on_lyrics_found)

    def _on_lyrics_found(self, data: Optional[dict]) -> None:
        if not data:
            return
        self._executor.submit(self._process, data)

    def _process(self, data: dict) -> None:
        try:
            timeline: TrackTimeline = data.get("timeline")
            track_id: int           = data.get("track_id", 0)

            if not timeline or not timeline.lines:
                return

            self._bus.publish(EventType.TRANSLATION_STARTED, None)

            # 1. Memory cache
            cache_key = str(track_id)
            with self._lock:
                if cache_key in self._memory_cache:
                    translations = self._memory_cache[cache_key]
                    self._apply_translations(timeline.lines, translations)
                    self._bus.publish(EventType.TRANSLATION_READY, timeline)
                    app_logger.info(f"[TransService] Memory cache hit for track_id={track_id}")
                    return

            # 2. SQLite cache
            if self._translation_repo.has_translations(track_id, _TARGET_LANG):
                app_logger.info(f"[TransService] SQLite cache hit for track_id={track_id}")
                rows = self._lyrics_repo.load_lines(track_id)
                translations = [r.get("text_translation", "") for r in rows]
                with self._lock:
                    self._memory_cache[cache_key] = translations
                self._apply_translations(timeline.lines, translations)
                self._bus.publish(EventType.TRANSLATION_READY, timeline)
                return

            # 3. Detect language — hanya skip jika sangat yakin sudah Indonesia (≥95%)
            sample    = " ".join(l.original_text for l in timeline.lines[:8])
            lang_info = detect_language(sample)

            if is_already_target(lang_info, _TARGET_LANG):
                app_logger.info("[TransService] Already Indonesian, skip translation.")
                self._bus.publish(EventType.TRANSLATION_READY, timeline)
                return

            # ★ Emit dulu agar lirik langsung muncul tanpa terjemahan
            self._bus.publish(EventType.TRANSLATION_READY, timeline)

            # 4. Terjemahkan — coba Google dulu, fallback ke MyMemory
            texts = [l.original_text for l in timeline.lines]
            app_logger.info(
                f"[TransService] Translating {len(texts)} lines "
                f"via {self._primary.name} (batch)..."
            )

            formatted = self._translate_with_fallback(texts)
            if not formatted:
                app_logger.warning("[TransService] Both providers failed, showing lyrics without translation.")
                return

            # 5. Quality check
            final = []
            for orig, trans in zip(texts, formatted):
                t = format_translation(trans)
                if not check_quality(orig, t):
                    t = ""
                final.append(t)

            # 6. Simpan ke SQLite cache
            lyrics_ids = self._lyrics_repo.get_lyrics_ids(track_id)
            if lyrics_ids:
                tr_results = [
                    TranslationResult(
                        original=orig,
                        translated=trans,
                        language=_TARGET_LANG,
                        provider=self._primary.name,
                    )
                    for orig, trans in zip(texts, final)
                ]
                self._translation_repo.save_translations(lyrics_ids, tr_results, _TARGET_LANG)

            # 7. Apply ke timeline dan emit TRANSLATION_READY dengan terjemahan
            with self._lock:
                self._memory_cache[cache_key] = final
            self._apply_translations(timeline.lines, final)

            # ★ Emit kedua: terjemahan siap, overlay update otomatis
            self._bus.publish(EventType.TRANSLATION_READY, timeline)
            self._bus.publish(EventType.TRANSLATION_FINISHED, None)
            app_logger.info(f"[TransService] Translation complete for track_id={track_id}")

        except Exception as e:
            app_logger.error(f"[TransService] Unexpected error: {e}")
            self._bus.publish(EventType.TRANSLATION_FAILED, None)

    def _translate_with_fallback(self, texts: List[str]) -> Optional[List[str]]:
        """
        Coba Google Translate dulu.
        Jika gagal atau hasilnya sama dengan input (tidak terterjemahkan),
        fallback ke MyMemory.
        """
        try:
            result = self._primary.translate(texts, _SOURCE_LANG, _TARGET_LANG)
            # Cek apakah minimal sebagian sudah terterjemahkan (beda dari input)
            translated_count = sum(
                1 for orig, trans in zip(texts, result)
                if orig.strip() and trans.strip() and trans.strip().lower() != orig.strip().lower()
            )
            if translated_count > 0:
                app_logger.info(
                    f"[TransService] Google translated {translated_count}/{len(texts)} lines"
                )
                return result
            else:
                app_logger.warning("[TransService] Google returned same as input, trying fallback...")
        except Exception as e:
            app_logger.warning(f"[TransService] Google failed: {e}, trying fallback...")

        # Fallback ke MyMemory
        try:
            app_logger.info(f"[TransService] Translating via {self._fallback.name} (fallback)...")
            result = self._fallback.translate(texts, _SOURCE_LANG, _TARGET_LANG)
            app_logger.info(f"[TransService] MyMemory fallback succeeded.")
            return result
        except Exception as e:
            app_logger.error(f"[TransService] Fallback also failed: {e}")
            return None

    def _apply_translations(
        self,
        lines: List[SubtitleLine],
        translations: List[str]
    ) -> None:
        for i, line in enumerate(lines):
            if i < len(translations):
                line.translated_text = translations[i]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
