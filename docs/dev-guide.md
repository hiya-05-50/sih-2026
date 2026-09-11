# Developer Guide

## Running Backend Tests

```bash
cd backend
pip install -e ".[dev]"
pytest -q
```

## Running Integration Tests

From the repository root:

```bash
pip install -e "backend/.[dev]"
python -m pytest tests -q
```

## Building the Frontend

```bash
cd frontend
npm ci
npm run build
```

## CI

GitHub Actions runs all three validations automatically on push and pull request.

See `.github/workflows/ci.yml`.
