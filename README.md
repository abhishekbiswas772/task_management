# task_management

Postgres-based TaskBoard with Docker, pgAdmin, and Redis-backed sessions.

## Run with Docker Compose

```bash
docker compose up --build
```

Services:

- App: `http://localhost:5000`
- pgAdmin: `http://localhost:5050`
- Postgres: `localhost:5432`

Default credentials from `docker-compose.yml`:

- Postgres DB: `taskboard`
- Postgres user: `taskboard`
- Postgres password: `taskboard`
- pgAdmin email: `admin@taskboard.local`
- pgAdmin password: `admin123`

## Notes

- SQLite file-copy backups are disabled for the Postgres deployment path.
- The app now uses `asyncpg` for SQLAlchemy async access and `psycopg` for the sync login loader.
