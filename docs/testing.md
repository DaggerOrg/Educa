# Testing

Educa uses three test layers.

## Backend unit tests

These tests do not require Postgres:

```bash
cd backend
pytest -m unit
```

## Backend integration tests

Integration tests use the real pgvector service:

```bash
cd backend
docker compose up -d postgres
pytest -m integration
```

Set `DATABASE_URL` when using a non-default database endpoint.

## Playwright browser tests

The browser suite builds the frontend, starts the Vite preview server, and runs
Chromium against it:

```bash
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

The suite mocks only external authentication responses. It verifies the real
production bundle and browser behavior while remaining deterministic and free
of test accounts or provider API keys.

CI runs all three layers on pull requests and pushes to `main`. Failed
Playwright runs upload the HTML report, traces, screenshots, and videos when
available.