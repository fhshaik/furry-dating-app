# FurConnect

Minimal setup notes for running the app locally and deploying the containerized stack.

## Local Development

1. Create a local env file:

```bash
cp .env.example .env
```

2. Fill in the values you need in `.env`.
3. Start the local stack:

```bash
docker compose -f docker-compose.local.yml up --build
```

4. Migrations run automatically when the backend starts. On a **fresh database**, a seed migration loads example data: 5 demo users (with fursonas), 3 packs, matches, conversations, messages, swipes, and notifications. To see it, open the login page and click **Try demo (example data)**—you’ll be logged in as the first seed user (Luna). If that link returns “No demo user found”, the seed was skipped because the database already had users; remove the `mysql_data` volume and run `docker compose -f docker-compose.local.yml up` again for a fresh DB.

Local endpoints:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend health check: `http://localhost:8000/health`

The local frontend proxies `/api` requests to the backend container, so the default browser API base path can stay as `/api`.

## Environment Variables

Set these in `.env` for the backend:

| Variable | Required | Purpose |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | OAuth only | Google login client ID. |
| `GOOGLE_CLIENT_SECRET` | OAuth only | Google login client secret. |
| `DISCORD_CLIENT_ID` | OAuth only | Discord login client ID. |
| `DISCORD_CLIENT_SECRET` | OAuth only | Discord login client secret. |
| `JWT_SECRET` | Yes | Session and auth secret. Replace the default in any non-local environment. |
| `FRONTEND_URL` | Yes | Allowed frontend origin for CORS. Use `http://localhost:5173` locally. |
| `BACKEND_URL` | Yes for OAuth | Public backend origin used to build Google/Discord callback URLs. Use `http://localhost:8000` locally. |
| `MYSQL_HOST` | Yes | MySQL hostname. Use `mysql` in local Docker Compose. |
| `MYSQL_PORT` | Yes | MySQL port, defaults to `3306`. |
| `MYSQL_USER` | Yes | MySQL username. |
| `MYSQL_PASSWORD` | Yes | MySQL password. |
| `MYSQL_DATABASE` | Yes | MySQL database name. |
| `AWS_ACCESS_KEY_ID` | S3 only | AWS access key for uploads. |
| `AWS_SECRET_ACCESS_KEY` | S3 only | AWS secret key for uploads. |
| `AWS_S3_BUCKET` | S3 only | S3 bucket for uploaded assets. |
| `AWS_REGION` | S3 only | AWS region for the bucket. |
| `ENVIRONMENT` | Recommended | App environment, for example `development` or `production`. |
| `API_RATE_LIMIT` | Optional | Request limit string. Default is `60/minute`. |
| `SENTRY_DSN` | Optional | Enables Sentry when set. |
| `SENTRY_TRACES_SAMPLE_RATE` | Optional | Sentry traces sample rate, for example `0.25`. |

Frontend env notes:

- `VITE_API_BASE_URL` is optional when building the frontend outside the bundled nginx proxy. The app defaults to `/api`.
- The Vite dev server proxy target is controlled by `VITE_API_URL` and defaults to `http://localhost:8000`.

OAuth callback URLs to register locally:

- Google: `http://localhost:8000/api/auth/google/callback`
- Discord: `http://localhost:8000/api/auth/discord/callback`

## Deploy

## RC Release Pipeline

Pushes to the `rc` branch trigger an automated release candidate flow via GitHub Actions:

1. `semantic-release` inspects commits since the last tag using Conventional Commits format.
2. 2. A pre-release version tag is created automatically (e.g. `v1.2.0-rc.1`).
   3. 3. A `rc-release` dispatch event is sent to `furry-dating-infra`, which pulls the new image and deploys it to `https://rc.furconnect.xyz`.
     
      4. To promote RC to production, merge `rc` into `main`. The same pipeline runs on `main` and cuts a stable release (e.g. `v1.2.0`) which deploys to `https://furconnect.xyz`.
     
      5. ### Commit message format (Conventional Commits)
     
      6. | Prefix | Effect |
      7. |--------|--------|
      8. | `feat:` | Minor version bump (1.x.0) |
      9. | `fix:` | Patch bump (1.0.x) |
      10. | `feat!:` or `BREAKING CHANGE:` | Major bump (x.0.0) |
      11. | `chore:`, `docs:`, `style:` | No release |

`docker-compose.prod.yml` starts the frontend and backend containers only. It does not provision MySQL, so production deploys must point `MYSQL_*` values at an external database.

1. Prepare a production `.env` with real secrets, `ENVIRONMENT=production`, the public `FRONTEND_URL`, and external `MYSQL_*` values.
2. Build and start the production stack:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

3. Run database migrations against the production database:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

4. Expose port `80` for the frontend and port `8000` for the backend, or place them behind your existing reverse proxy/load balancer.

The production frontend container serves the SPA with nginx and proxies `/api` and `/ws` traffic to the backend service on the internal Docker network.
