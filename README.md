# RhythmTyper Discord Bot

Discord bot integration for **RhythmTyper**, built with **py-cord** and **PostgreSQL**.  
This repository is intended for **developers** who want to extend or build on top of the bot.

---

## Tech Stack

- Python 3.11+
- py-cord
- aiohttp
- asyncpg
- PostgreSQL
- Python-Dotenv

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS linked_users (
    discord_id BIGINT PRIMARY KEY,
    userid TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS link_codes (
    discord_id BIGINT PRIMARY KEY,
    userid TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_link_codes_expiry ON link_codes (expires_at);

CREATE TABLE IF NOT EXISTS user_peak (
    userid TEXT PRIMARY KEY,
    peak_rank INTEGER NOT NULL,
    achieved_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_peak_achieved_at ON user_peak (achieved_at);
```

## .env File

```.env
BOT_TOKEN=your_discord_bot_token

PG_HOST=your_postgres_host
PG_PORT=5432
PG_DB=database_name
PG_USER=database_user
PG_PASS=database_password
```
