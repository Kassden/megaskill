"""Small locked, atomic storage primitives shared by runtime commands."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


@contextlib.contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+', encoding='utf-8') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix='.mega-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(raw, path)
    finally:
        if os.path.exists(raw):
            os.unlink(raw)


def append_jsonl(path, value):
    path = Path(path)
    with locked(path.with_suffix(path.suffix + '.lock')):
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(value, sort_keys=True) + '\n')
            handle.flush()
            os.fsync(handle.fileno())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_id(value):
    import re
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ValueError('invalid identifier')
    return value


def binding_root():
    return Path(os.environ.get('MEGA_BINDINGS_DIR', str(Path.home() / '.codex' / 'megaskill' / 'sessions')))
