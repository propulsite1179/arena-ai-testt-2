"""Content-addressed evidence; never executes or renders generated HTML in the app."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import json
import os
import re

ALLOWED = {'.html', '.css', '.js', '.json', '.txt', '.luau', '.lua', '.png', '.jpg', '.webp'}
MAX_BYTES = 2_000_000


def safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or '\x00' in name or path.is_absolute() or '..' in path.parts or any(p.startswith('.') for p in path.parts):
        raise ValueError('Unsafe artifact path')
    if not re.fullmatch(r'[A-Za-z0-9_./-]{1,180}', name):
        raise ValueError('Artifact paths must use portable ASCII filenames')
    if str(path) != name:
        raise ValueError('Artifact paths must be normalized')
    if path.suffix.lower() not in ALLOWED:
        raise ValueError('Artifact extension is not permitted')
    return path


def validate_project(files: dict[str, str]) -> dict[str, str]:
    if not isinstance(files, dict) or not 1 <= len(files) <= 64 or 'index.html' not in files:
        raise ValueError('Web projects need index.html and at most 64 text files')
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError('Case-insensitive filename collision')
    for name in files:
        if any(str(parent) in files for parent in PurePosixPath(name).parents if str(parent) != '.'):
            raise ValueError('A file cannot also be a directory')
    total = 0
    for name, content in files.items():
        safe_relative(name)
        if not isinstance(content, str):
            raise ValueError('Generated files must be UTF-8 text')
        total += len(content.encode('utf-8'))
    if total > MAX_BYTES:
        raise ValueError('Generated project exceeds size limit')
    return files


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes) -> str:
        if len(data) > 8_000_000:
            raise ValueError('Artifact too large')
        digest = sha256(data).hexdigest()
        path = self.root / digest[:2] / digest
        path.parent.mkdir(exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Existing content-addressed object is corrupt')
        return digest

    def get(self, digest: str) -> bytes:
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Invalid artifact hash')
        data = (self.root / digest[:2] / digest).read_bytes()
        if sha256(data).hexdigest() != digest:
            raise ValueError('Artifact integrity check failed')
        return data

    def put_json(self, value: object) -> str:
        return self.put(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode())
