"""Small, per-user preferences; no ROM data or project changes are stored here."""
import json
import os
from pathlib import Path
import tempfile


def preferences_path():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local'/'share'))
    return base/'New Horizons Editor'/'preferences.json'


def last_rom():
    try:
        data = json.loads(preferences_path().read_text(encoding='utf-8'))
        value = data.get('last_rom') if isinstance(data, dict) else None
        return value if isinstance(value, str) and value.strip() and Path(value).is_absolute() else None
    except (OSError, ValueError):
        return None


def remember_rom(path):
    """Called only after the editor has verified and loaded the ROM successfully."""
    target = preferences_path()
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(target.read_text(encoding='utf-8'))
            if not isinstance(data, dict): data = {}
        except (OSError, ValueError):
            data = {}
        data['last_rom'] = str(Path(path).resolve())
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(data, file, indent=2)
        os.replace(temporary, target)
        return True
    except OSError:
        return False
    finally:
        if temporary is not None:
            try: temporary.unlink(missing_ok=True)
            except OSError: pass
