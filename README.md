# RhythmTyper Discord Bot

Discord bot integration for **RhythmTyper**, a rhythm-based typing game. Built with **py-cord** and **PostgreSQL**.

This repository is intended for **developers** who want to extend, contribute to, or build on top of the bot.

---

## 🎮 Features

- **User Linking**: Connect Discord accounts to RhythmTyper profiles via verification codes
- **Profile Display**: View detailed user stats, peak ranks, and play history
- **Leaderboard Integration**: Browse global and country rankings with flexible filtering
- **Recent Plays**: Display the latest scores with detailed stats and beatmap info
- **Beatmap Search**: Find maps with interactive dropdown selection
- **Auto Peak Tracking**: Automatically tracks and updates users' highest ranks
- **Caching System**: Reduces API calls with smart TTL-based caching
- **Error Handling**: Robust retry logic and graceful degradation

---

## 🛠️ Tech Stack

- **Python 3.11+**
- **py-cord** - Discord API wrapper
- **aiohttp** - Async HTTP client for API requests
- **asyncpg** - Async PostgreSQL driver
- **PostgreSQL** - Primary database
- **Python-Dotenv** - Environment variable management

---

## 📊 Database Schema

The bot uses PostgreSQL with the following tables:

```sql
-- Stores linked Discord accounts
CREATE TABLE IF NOT EXISTS linked_users (
    discord_id BIGINT PRIMARY KEY,
    userid TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT now()
);

-- Temporary codes for account linking
CREATE TABLE IF NOT EXISTS link_codes (
    discord_id BIGINT PRIMARY KEY,
    userid TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_link_codes_expiry ON link_codes (expires_at);

-- Tracks users' peak rankings
CREATE TABLE IF NOT EXISTS user_peak (
    userid TEXT PRIMARY KEY,
    peak_rank INTEGER NOT NULL,
    achieved_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_peak_achieved_at ON user_peak (achieved_at);
```

---

## ⚙️ Environment Setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 12+
- A Discord Bot Token ([How to get one](https://discord.com/developers/applications))
- Basic knowledge of Git and terminal commands

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/RhythmTyper-Tools-And-Extensions/RhythmTyper-Discord-Bot.git
   cd RhythmTyper-Discord-Bot
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL**
   - Create a new database for the bot
   - Run the SQL schema provided above
   - Note your database credentials

5. **Configure environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   TOKEN=your_discord_bot_token
   PG_HOST=localhost
   PG_PORT=5432
   PG_DB=rhythmtyper_bot
   PG_USER=your_postgres_user
   PG_PASS=your_postgres_password
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

   If everything is set up correctly, you should see the bot come online in your Discord server!

---

## 🤝 Contributing

We welcome contributions from developers of all skill levels! Whether you're fixing a bug, adding a feature, or improving documentation, your help is appreciated.

### For First-Time Contributors

Never made a Discord bot before? No problem! Here's what you need to know:

- **Discord Bots 101**: Bots respond to commands and events in Discord servers
- **py-cord**: The library we use to interact with Discord's API ([Documentation](https://docs.pycord.dev/))
- **Async/Await**: Python's way of handling concurrent operations (used heavily in Discord bots)
- **PostgreSQL**: Our database for storing user data and stats

**Helpful Resources**:
- [py-cord Getting Started](https://docs.pycord.dev/en/stable/index.html)
- [Discord Developer Portal](https://discord.com/developers/docs/intro)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/current/)

**Need Help?** Join the [RhythmTyper Bot Development Server](https://discord.gg/Kc6nJWJG8v) to ask questions and get guidance from other contributors!

### How to Contribute

1. **Fork the repository**
   
   Click the "Fork" button at the top right of this page to create your own copy.

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/RhythmTyper-Discord-Bot.git
   cd RhythmTyper-Discord-Bot
   ```

3. **Create a new branch**
   ```bash
   git checkout -b feature/my-awesome-feature
   ```
   
   Use a descriptive name:
   - `feature/add-stats-command` for new features
   - `fix/leaderboard-crash` for bug fixes
   - `docs/update-readme` for documentation

4. **Make your changes**
   - Keep code clean and modular
   - Add comments to explain complex logic
   - Follow existing code style and conventions
   - Test your changes thoroughly

5. **Test locally**
   
   Make sure the bot runs without errors:
   ```bash
   python main.py
   ```
   
   Test your new feature/fix in a Discord server.

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description of what you did"
   ```
   
   Write clear commit messages:
   - ✅ "Add /profile command to display user stats"
   - ❌ "updated stuff"

7. **Push to your fork**
   ```bash
   git push origin feature/my-awesome-feature
   ```

8. **Open a Pull Request**
   - Go to the original repository on GitHub
   - Click "Pull Requests" → "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template:
     - **What does this PR do?**
     - **Why is this change needed?**
     - **How did you test it?**
     - **Screenshots** (if applicable)
   - Submit and wait for review!

### Code Review Process

- A maintainer will review your PR within a few days
- They may request changes or ask questions
- Make requested changes by pushing new commits to your branch
- Once approved, your PR will be merged! 🎉

### What to Contribute

Not sure where to start? Check out:
- [Good First Issues](https://github.com/RhythmTyper-Tools-And-Extensions/RhythmTyper-Discord-Bot/labels/good%20first%20issue)
- [Help Wanted](https://github.com/RhythmTyper-Tools-And-Extensions/RhythmTyper-Discord-Bot/labels/help%20wanted)

**Ideas for contributions**:
- Add new slash commands (e.g., `/compare`, `/top` for user top plays)
- Improve error handling and user feedback
- Add command cooldowns to prevent spam
- Write unit tests for utilities
- Update documentation
- Optimize database queries with better indexing
- Add embed customization options
- Create admin commands for moderation
- Implement pagination for long leaderboards
- Add statistics visualizations (graphs, charts)
- Build a help command with detailed usage examples
- Add support for beatmap difficulty filtering
- Implement user notifications for rank milestones

---

## 📝 Code Style Guidelines

- Use **4 spaces** for indentation
- Follow [PEP 8](https://pep8.org/) Python style guide
- Use **type hints** where possible
- Write **docstrings** for functions and classes
- Keep functions focused and single-purpose
- Use **async/await** for I/O operations

Example:
```python
async def get_user_stats(user_id: str) -> dict:
    """
    Fetch user statistics from the database.
    
    Args:
        user_id: The RhythmTyper user ID
        
    Returns:
        Dictionary containing user stats
    """
    async with bot.db_pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM linked_users WHERE userid = $1",
            user_id
        )
```

---

## 🐛 Reporting Issues

Found a bug? Please [open an issue](https://github.com/RhythmTyper-Tools-And-Extensions/RhythmTyper-Discord-Bot/issues/new) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/error logs (if applicable)
- Your environment (Python version, OS, etc.)

---

## 📖 Bot Commands

### User Commands
- `/link <username>` - Link your Discord account to RhythmTyper (DM only)
- `/verify` - Verify your account with the code in your profile (DM only)
- `/unlink` - Unlink your RhythmTyper account (DM only)
- `/status` - Check your linking status (DM only)
- `/user [target]` - Display detailed user profile and stats
  - Use without target to show your own profile
  - Mention a Discord user: `/user @someone`
  - Use RhythmTyper username: `/user playerName`
- `/recent [target]` - Show the most recent score
  - Same targeting options as `/user`

### Leaderboard Commands
- `/leaderboard` - Show top 10 global players (PP)
- `/leaderboard pp` - Show PP leaderboard
- `/leaderboard score` - Show ranked score leaderboard
- `/leaderboard <rank>` - Show specific rank (e.g., `/leaderboard 50`)
- `/leaderboard <start>-<end>` - Show rank range (max 11 entries, e.g., `/leaderboard 10-20`)
- `/leaderboard <country>` - Filter by country code (e.g., `/leaderboard US`)
- Combine options: `/leaderboard pp US 5-15`

### Beatmap Commands
- `/map <keywords>` - Search for beatmaps
  - `/map <keywords> <status>` - Filter by status (ranked, qualified, nominated, unranked, all)
  - Returns interactive dropdown with up to 50 results

### Utility Commands
- `/ping` - Check bot latency
- `/uptime` - Show how long the bot has been running

**Note**: Link/verify/unlink/status commands only work in DMs for security and to prevent spam in channels.

---

## 🔧 Architecture Notes

### Command System
- Uses **py-cord's bridge commands** - supports both slash commands (`/`) and prefix commands (`>`)
- Commands automatically register as slash commands in Discord
- Cogs are dynamically loaded from the `cogs/` directory on startup

### Background Tasks
- **`cleanup_link_codes()`**: Runs every 5 minutes (300s) to remove expired verification codes
- Gracefully cancels on bot shutdown to prevent data inconsistencies
- Add new background tasks in `main.py` using `@tasks.loop()`

### API Integration
- All API calls use `aiohttp.ClientSession` for async requests
- **Retry Logic**: Automatically retries failed requests up to 3 times with exponential backoff
- **Timeout**: 5-second timeout per request to prevent hanging
- Session is initialized on bot startup and properly closed on shutdown
- Caching layer reduces redundant API calls (60s TTL for leaderboards)

### Database Architecture
- Uses **asyncpg connection pool** for efficient concurrent database access
- Pool configuration: 1-10 connections (auto-scales based on load)
- **Query Helpers**: `fetchrow()`, `fetch()`, `execute()` wrap common patterns
- Always use `async with bot.db_pool.acquire()` for manual queries
- Pool is created on startup and closed on shutdown

### User Resolution System
- **`resolve_target()`** utility handles flexible user targeting:
  - No argument → uses command author
  - Discord mention → looks up linked account
  - Username string → searches RhythmTyper API
- Returns normalized user data: `{discord_user, userid, username}`
- Prevents code duplication across commands

### Error Handling
- Commands handle errors gracefully with user-friendly messages
- API failures trigger automatic retries before surfacing errors
- Database errors are logged and reported to users appropriately
- Ephemeral responses used for error messages to reduce clutter

### Caching Strategy
- **Leaderboard Cache**: 60s TTL to balance freshness and API load
- Cache key format: `{metric}:{country}:{offset}:{limit}`
- Cache automatically invalidates after TTL expires
- Reduces API calls by ~80% for popular leaderboard queries

### Logging
- **Console**: DEBUG level (all events)
- **File (`bot.log`)**: INFO level (important events only)
- Timestamped entries with clear log levels
- Separate loggers for different subsystems (API, DB, main)

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- RhythmTyper game developers
- py-cord community
- All contributors who help improve this bot

---

## 💬 Support

Need help? Have questions?
- Join the [RhythmTyper Bot Development Server](https://discord.gg/c4x4NefeTW) - for bot development discussions
- Join the [RhythmTyper Discord Server](https://discord.gg/Kc6nJWJG8v) - for the game community
- Open an [issue](https://github.com/RhythmTyper-Tools-And-Extensions/RhythmTyper-Discord-Bot/issues)
- Check existing [discussions](https://github.com/RhythmTyper-Tools-And-Extensions/RhythmTyper-Discord-Bot/discussions)

---

**Happy coding! 🚀**
