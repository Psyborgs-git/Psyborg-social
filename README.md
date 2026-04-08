# SocialMind

Autonomous social media management platform powered by AI.

## Development

Use Python 3.12 with `uv` for the backend and Bun for the UI:

- `uv sync --python 3.12 --extra dev`
- `uv sync --python 3.12 --extra browser --extra media --extra social-instagram --extra social-reddit --extra social-twitter --extra social-youtube`
- `cd ui && bun install && bun run build`
- `uv run --python 3.12 uvicorn socialmind.api.main:app --reload`

## Docker

Build and run the stack with Docker Compose using `docker-compose.yml`. Use `docker-compose.dev.yml` as an override on top of the base file for live-reload development.
The default Compose topology expects a host PostgreSQL cluster listening on `localhost:5432` / `0.0.0.0:5432`; containers reach that host database as `host.docker.internal:5432`. The default credentials are the `socialmind` database/user, or equivalent values supplied via `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

- `docker compose up -d --build`
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
- `DATABASE_HOST=postgres docker compose --profile docker-db up -d --build` if you want Docker to manage Postgres instead of the host machine
- `docker compose exec ollama ollama pull llama3.2`
- `docker compose exec ollama ollama pull nomic-embed-text`
- `curl http://localhost:8000/health`
- `curl http://localhost:8001/health`
- `UV_EXTRAS=browser,media,social-instagram,social-reddit,social-twitter,social-youtube`
- `INSTALL_PLAYWRIGHT=true`

Supported platforms now include Instagram, TikTok, Reddit, YouTube, Facebook, Twitter, Threads, and LinkedIn.
