# RhythmTyper Discord Bot

Discord bot integration for **RhythmTyper**, built with **py-cord** and **PostgreSQL**.  
This repository is intended for **developers** who want to extend or build on top of the bot.

---

## Tech Stack

- Python 3.13+
- py-cord
- aiohttp
- asyncpg
- PostgreSQL

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS linked_users (
    discord_id BIGINT PRIMARY KEY,
    userid BIGINT NOT NULL,
    username TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS link_codes (
    discord_id BIGINT PRIMARY KEY,
    userid BIGINT NOT NULL,
    code TEXT NOT NULL,
    expires_at BIGINT NOT NULL
);

## .env File

```.env
BOT_TOKEN=your_discord_bot_token

PG_HOST=your_postgres_host
PG_PORT=5432
PG_DB=database_name
PG_USER=database_user
PG_PASS=database_password
```
