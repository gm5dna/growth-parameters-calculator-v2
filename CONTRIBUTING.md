# Contributing

Keep changes small, clinically safe, and consistent with the existing Flask
plus vanilla ES-module frontend architecture.

## Setup

Python 3.12 is required.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install
```

## Local Checks

These commands assume the virtualenv is active:

```bash
python -m ruff check .
python -m pytest -q
npm run lint
npm test
```

## Clinical Safety

- Use `rcpchgrowth` for all growth reference calculations. Do not hand-code
  growth references, SDS, centile, or chart reference logic.
- Treat client-side validation as user experience only. Server-side validation
  in `validation.py` is authoritative.
- Keep the app stateless. Do not add a database or retain clinical payloads
  across requests.
- Do not write PHI to localStorage, browser storage, server logs, analytics,
  caches, files, or any persistent storage.
- Ensure PDF export and other secondary outputs are derived from validated
  server-side calculations, not trusted client-supplied result objects.
