import json
import os
from pathlib import Path

from models import CharacterProfile, CharacterManifest

_CHARACTERS_DIR = Path(os.environ.get("CHARACTERS_DIR", "./characters"))


def character_dir(character_id: str) -> Path:
    d = _CHARACTERS_DIR / character_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_bio(profile: CharacterProfile) -> Path:
    path = character_dir(profile.id) / "bio.json"
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_bio(character_id: str) -> CharacterProfile:
    path = _CHARACTERS_DIR / character_id / "bio.json"
    return CharacterProfile.model_validate_json(path.read_text(encoding="utf-8"))


def save_manifest(manifest: CharacterManifest) -> Path:
    path = character_dir(manifest.character_id) / "manifest.json"
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def list_characters() -> list[CharacterManifest]:
    if not _CHARACTERS_DIR.exists():
        return []
    manifests = []
    for manifest_path in _CHARACTERS_DIR.glob("*/manifest.json"):
        try:
            manifests.append(CharacterManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            ))
        except Exception:
            pass
    return manifests
