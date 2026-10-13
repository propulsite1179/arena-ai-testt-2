"""Portable archive safety and read-only export contracts."""
import hashlib,json,zipfile
from scripts import build as builder
from gamedev.config import ROOT


def test_source_discovery_excludes_generated_manifests_and_secrets(tmp_path):
    for name in ('README.md','.env.example','SOURCE_MANIFEST.json','.env','.local-session-key','data.db'):
        (tmp_path/name).write_text('test')
    (tmp_path/'var').mkdir();(tmp_path/'var/private.json').write_text('secret')
    names={p.relative_to(tmp_path).as_posix() for p in builder.source_files(tmp_path)}
    assert names=={'README.md','.env.example'}


def test_rebuilt_archive_has_unique_and_verified_manifest(tmp_path,monkeypatch):
    (tmp_path/'README.md').write_text('source')
    (tmp_path/'SOURCE_MANIFEST.json').write_text('{}')
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    original=builder.source_files
    monkeypatch.setattr(builder,'source_files',lambda:original(tmp_path))
    with zipfile.ZipFile(builder.archive()) as archive:
        assert len(archive.namelist())==len(set(archive.namelist()))==2
        manifest=json.loads(archive.read('gamedev-ai-bench/SOURCE_MANIFEST.json'))
        assert manifest=={'README.md':hashlib.sha256(b'source').hexdigest()}


def test_static_save_is_explicitly_disabled():
    script=(ROOT/'gamedev/web/static/app.js').read_text()
    assert "if(isStatic){const save=$('#save-comparison');save.disabled=true;save.title=t('server_required');}" in script
