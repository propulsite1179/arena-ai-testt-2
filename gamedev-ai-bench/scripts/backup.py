"""Portable SQLite/evidence backup. Stop writes; secrets are backed up separately."""
from pathlib import Path
import argparse,hashlib,json,shutil,sqlite3,sys
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gamedev.config import Settings

def files(root):
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError('Symlinks are not accepted in backup trees')
        if path.is_file() and path.name!='backup-manifest.json':yield path

def verify(backup):
    root=Path(backup).resolve();manifest=json.loads((root/'backup-manifest.json').read_text())
    observed={path.relative_to(root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in files(root)}
    if observed!=manifest['files']:raise ValueError('Backup integrity check failed')
    if 'database.sqlite3' not in observed:raise ValueError('Database backup missing')
    with closing(sqlite3.connect((root/'database.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True)) as connection:
        if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity check failed')
    return manifest

def create(settings,destination):
    if not settings.database_url.startswith('sqlite:///'):raise ValueError('Use pg_dump plus an evidence snapshot for PostgreSQL')
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Backup destination must not already exist')
    if destination.is_relative_to(settings.data_dir.resolve()):raise ValueError('Backups must be outside the live data directory')
    source=Path(settings.database_url.removeprefix('sqlite:///')).resolve()
    if not source.is_file():raise ValueError('Source database not found')
    destination.mkdir(parents=True)
    with closing(sqlite3.connect(source)) as live,closing(sqlite3.connect(destination/'database.sqlite3')) as backup:
        live.backup(backup)
        backup.execute('PRAGMA journal_mode=DELETE')
        backup.commit()
    artifacts=settings.data_dir/'artifacts'
    if artifacts.exists():
        list(files(artifacts))
        shutil.copytree(artifacts,destination/'artifacts')
    manifest={'format':'gdb-sqlite-backup/1','secrets_included':False,'requires_quiesced_writes':True,'files':{path.relative_to(destination).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in files(destination)}}
    (destination/'backup-manifest.json').write_text(json.dumps(manifest,indent=2))
    verify(destination);return manifest

def restore(backup,destination):
    verify(backup);destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Restore destination must not already exist')
    shutil.copytree(backup,destination);verify(destination)
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    c=sub.add_parser('create');c.add_argument('--destination',type=Path,required=True)
    v=sub.add_parser('verify');v.add_argument('--backup',type=Path,required=True)
    r=sub.add_parser('restore');r.add_argument('--backup',type=Path,required=True);r.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    result=create(Settings.from_env(),args.destination) if args.action=='create' else verify(args.backup) if args.action=='verify' else restore(args.backup,args.destination)
    print('Completed',args.action,'- verify restored application before switching traffic')
