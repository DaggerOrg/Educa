# CI/CD Environments

Create protected GitHub Environments named `development`, `staging`, and
`production`. Require reviewers for staging and production and restrict their
deployment branches in repository settings.

Each environment needs a `DEPLOY_WEBHOOK_URL` secret. The receiving platform
must validate the request, deploy the supplied GHCR image by digest, run health
checks, and support rollback. Runtime API keys stay in the target platform.

- Pushes to `main` deploy to `development`.
- `staging` and `production` are manually promoted from Actions with an exact
  commit, branch, or tag and are gated by their GitHub Environment rules.
- The image is tagged with the commit SHA; `latest` is never deployed.

The `Test` workflow runs unit tests, Postgres integration tests, and Playwright
browser tests on every pull request and push to `main`.