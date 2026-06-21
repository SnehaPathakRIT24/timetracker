# TimeTracker — AI-Powered Team Time Tracking

Automatically tracks what your team is working on and classifies it into:
**Next Level** · **Outgrow Media** · **Be Rolling Media** · Admin · Personal

Zero manual input. Team members just turn on their laptop.

---

## Architecture

```
[Agent on each laptop]
  → captures active window/app/URL every 60s
  → buffers locally in SQLite
  → uploads batch every 5 min to server

[FastAPI Server]
  → receives batches
  → runs rule engine (free, instant)
  → sends unclassified records to Claude Haiku
  → stores in PostgreSQL

[React Dashboard]
  → real-time via WebSocket
  → Today / Weekly / Projects / Team / Review / Insights
```

---

## Quickstart (Server)

**Requirements:** Docker + Docker Compose

```bash
cd docker
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and a secure JWT_SECRET
bash ../scripts/deploy_server.sh
```

Dashboard: http://localhost:3000  
API: http://localhost:8000  
Default login: `snehapathak752@gmail.com` / `changeme123`

> **Change your password** in Settings after first login.

---

## Onboarding a New Team Member

### Mac
```bash
bash scripts/setup_mac.sh
```
Installs the agent, configures launchd to run on startup, registers with server.

### Windows
```
scripts\setup_windows.bat
```
Installs the agent, adds Task Scheduler entry for startup.

That's it. The agent starts immediately and data appears in the dashboard within 5 minutes.

---

## Pause Tracking

- **Mac:** `Cmd+Shift+P` — pauses for 30 minutes (press again to resume)
- **Windows:** `Ctrl+Shift+P` — pauses for 30 minutes

---

## Adding a New Business / Category

1. Go to **Settings → Classification Rules** in the dashboard
2. Or edit `config/rules.yaml` and import rules via the `/rules` API
3. To add a new top-level business category, update the AI system prompt in `server/services/classifier.py` (the `SYSTEM_PROMPT` constant) and the `CategoryEnum` in `server/models/database.py`

---

## Adding Classification Rules (No-Code)

Rules are checked before AI — they're free, instant, and deterministic.

In the dashboard Settings tab:
- **Pattern:** the text to match (e.g. `BeRolling`, `premiere`, `nextlevel.com`)
- **Field:** `window_title`, `app_name`, or `url`
- **Match type:** `contains`, `startswith`, `exact`, or `regex`
- **Category:** which business to assign
- **Priority:** lower = checked first

Example rule: "if `window_title` contains `premiere` → Be Rolling Media"

---

## AI Classification

- Uses **Claude Haiku** (fast, cheap) for real-time classification
- Results are cached — identical app+title never hit the API twice
- Manual corrections in the **Review** tab become few-shot examples for future prompts
- Daily summaries use **Claude Opus** for deeper analysis

---

## Privacy

- No screenshots, no keylogging, no mouse tracking
- Only: app name, window title, URL
- Data encrypted in transit (HTTPS) and at rest
- Team members can always see their own full data
- Admins see category-level summaries only (unless member consents in Settings)

---

## Viewing Reports

| View | What you see |
|------|-------------|
| Today | Per-person pie chart + app breakdown + live timeline |
| Weekly | Stacked bar chart per day, per-member breakdown |
| Projects | Total hours per business this week + month |
| Team | Side-by-side comparison of all members |
| Review | Low-confidence AI calls that need human correction |
| Insights | Claude-generated daily team summary + anomalies + recommendations |

---

## Deploying to a VPS (DigitalOcean / Hetzner)

```bash
# On your VPS (Ubuntu 22.04)
apt install docker.io docker-compose-plugin -y
git clone https://github.com/yourorg/timetracker.git
cd timetracker/docker
cp .env.example .env
nano .env  # fill in your keys

# Point your domain to the VPS IP, then:
docker compose up -d

# For HTTPS, put Nginx + Certbot in front, or use Caddy
```

Then update agent `SERVER_URL` to `https://your-domain.com`.

---

## Exporting Data

```bash
# Export all activity as CSV via the API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://yourserver.com/report/daily?target_date=2024-01-15" | python3 -m json.tool

# Or connect directly to PostgreSQL
psql postgresql://tracker:PASSWORD@localhost:5432/timetracker
```

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Agent | Python 3.11, AppKit/Quartz (Mac), win32gui (Windows) |
| Server | FastAPI, SQLAlchemy, PostgreSQL |
| AI | Claude Haiku (classification), Claude Opus (insights) |
| Dashboard | React 18, TailwindCSS, Recharts |
| Infra | Docker, docker-compose |
| Auth | JWT + bcrypt |
