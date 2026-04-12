"""
ai_core/copilot/library_fetcher.py
====================================
Library Fetcher: Downloads and caches KiCad symbols/footprints.

Sources (in order of priority):
  1. Local KiCad 10 built-in library (fastest, no network)
  2. LCSC/JLCPCB via JLC2KiCadLib (broad catalog)
  3. SnapEDA scrape (fallback, rate-limited)

Caches everything to: NeuroBoard/lib/
  lib/
  ├── symbols/
  ├── footprints/
  └── datasheets/
"""

import os
import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger("SystemLogger")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT       = Path(__file__).resolve().parent.parent.parent
LIB_DIR         = REPO_ROOT / "lib"
SYMBOLS_DIR     = LIB_DIR / "symbols"
FOOTPRINTS_DIR  = LIB_DIR / "footprints"
DATASHEETS_DIR  = LIB_DIR / "datasheets"
CACHE_FILE      = LIB_DIR / "fetch_cache.json"

KICAD_SYM_DIR   = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
KICAD_FP_DIR    = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")


# LCSC part numbers for known components
LCSC_PART_MAP = {
    "24LC32":              "C2502",    # AT24C32 EEPROM SOIC-8
    "Micro_SD_Card":       "C91145",   # Micro SD card slot
    "MountingHole":        None,       # No LCSC — mechanical only
    "Conn_02x20_Odd_Even": "C429954",  # 2x20 2.54mm female header
    "Conn_01x16":          "C530969",  # 16-pin 0.5mm FPC connector
}


class LibraryFetcher:
    """
    Fetches, caches, and validates KiCad symbols and footprints
    for a given component manifest.
    """

    def __init__(self):
        # Ensure lib directories exist
        for d in [LIB_DIR, SYMBOLS_DIR, FOOTPRINTS_DIR, DATASHEETS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

        self._cache = self._load_cache()

    # -----------------------------------------------------------------------
    #  Public API
    # -----------------------------------------------------------------------

    def fetch_manifest(self, component_manifest: List[Dict]) -> Dict[str, Any]:
        """
        For each component in a manifest, ensure its symbol and footprint
        are available locally. Returns a fetch report.
        """
        report = {"fetched": [], "cached": [], "failed": [], "missing": []}

        for comp in component_manifest:
            comp_id    = comp.get("component_id", "unknown")
            sym_lib    = comp.get("skidl_lib")
            sym_name   = comp.get("skidl_symbol")
            fp_name    = comp.get("footprint")

            if not sym_lib or not sym_name:
                continue

            cache_key = f"{sym_lib}:{sym_name}"

            # 1. Already cached?
            if cache_key in self._cache:
                log.debug(f"[LibFetch] Cache hit: {cache_key}")
                report["cached"].append(cache_key)
                continue

            # 2. Try local KiCad library
            found_locally = self._check_kicad_local(sym_lib, sym_name, fp_name)
            if found_locally:
                self._cache[cache_key] = {
                    "source": "kicad_local",
                    "symbol_lib": sym_lib,
                    "symbol_name": sym_name,
                    "footprint": fp_name,
                }
                report["fetched"].append(cache_key)
                continue

            # 3. Try LCSC / JLC2KiCadLib
            lcsc_id = LCSC_PART_MAP.get(sym_name)
            if lcsc_id:
                success = self._fetch_from_lcsc(lcsc_id, comp_id)
                if success:
                    self._cache[cache_key] = {
                        "source": "lcsc",
                        "lcsc_part": lcsc_id,
                        "symbol_lib": sym_lib,
                        "footprint": fp_name,
                    }
                    report["fetched"].append(cache_key)
                    continue

            # 4. Mark as missing but don't block pipeline
            log.warning(f"[LibFetch] Could not fetch: {cache_key} — will use KiCad built-in at SKiDL runtime.")
            report["missing"].append(cache_key)

        self._save_cache()
        log.info(f"[LibFetch] Fetch complete. cached={len(report['cached'])} "
                 f"fetched={len(report['fetched'])} missing={len(report['missing'])}")
        return report

    def is_available(self, skidl_lib: str, skidl_symbol: str) -> bool:
        """Check if a symbol is available in local KiCad or our lib cache."""
        cache_key = f"{skidl_lib}:{skidl_symbol}"
        if cache_key in self._cache:
            return True
        return self._check_kicad_local(skidl_lib, skidl_symbol, None)

    # -----------------------------------------------------------------------
    #  Internal helpers
    # -----------------------------------------------------------------------

    def _check_kicad_local(self, sym_lib: str, sym_name: str, fp_name: Optional[str]) -> bool:
        """Return True if symbol exists in the local KiCad 10 installation."""
        sym_file = KICAD_SYM_DIR / f"{sym_lib}.kicad_sym"
        if not sym_file.exists():
            return False

        # Quick string-search inside the symbol file for the symbol name
        try:
            content = sym_file.read_text(encoding="utf-8", errors="ignore")
            if f'(symbol "{sym_name}"' in content or f"(symbol \"{sym_name}\"" in content:
                return True
        except Exception:
            pass
        return False

    def _fetch_from_lcsc(self, lcsc_part: str, ref_name: str) -> bool:
        """
        Download footprint and symbol from LCSC using JLC2KiCadLib.
        pip install JLC2KiCadLib
        """
        try:
            result = subprocess.run(
                [
                    "python", "-m", "JLC2KiCadLib", lcsc_part,
                    "--symbol_lib",   str(SYMBOLS_DIR  / f"{ref_name}_lcsc.kicad_sym"),
                    "--footprint_lib", str(FOOTPRINTS_DIR / f"{ref_name}_lcsc.pretty"),
                ],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                log.info(f"[LibFetch] JLC2KiCadLib fetched {lcsc_part} → {ref_name}")
                return True
            else:
                log.debug(f"[LibFetch] JLC2KiCadLib failed for {lcsc_part}: {result.stderr[:200]}")
        except FileNotFoundError:
            log.debug("[LibFetch] JLC2KiCadLib not installed. Skipping LCSC fetch.")
        except subprocess.TimeoutExpired:
            log.warning(f"[LibFetch] LCSC fetch timed out for {lcsc_part}.")
        except Exception as e:
            log.debug(f"[LibFetch] LCSC fetch error: {e}")
        return False

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                return json.loads(CACHE_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save_cache(self):
        try:
            CACHE_FILE.write_text(json.dumps(self._cache, indent=2))
        except Exception as e:
            log.warning(f"[LibFetch] Failed to save cache: {e}")

    def get_cache_stats(self) -> Dict:
        return {
            "total_cached": len(self._cache),
            "lib_dir": str(LIB_DIR),
            "symbols_dir": str(SYMBOLS_DIR),
            "footprints_dir": str(FOOTPRINTS_DIR),
        }
