"""Vercel hosts the read-only public export, never a temporary SQLite backend."""
import os,re
from build import build
host=os.environ.get('VERCEL_PROJECT_PRODUCTION_URL') or os.environ.get('VERCEL_URL')
if not host or not re.fullmatch(r'[a-zA-Z0-9.-]+',host):raise ValueError('A valid deployment host is required for canonical metadata')
build('', 'https://'+host)
