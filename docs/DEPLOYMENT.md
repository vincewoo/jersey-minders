# Deploying to Synology NAS

Synology DSM 7.2+ includes **Container Manager**, which supports Docker Compose projects natively. This is the easiest way to run Jersey Minders on your NAS.

## Prerequisites

- DSM 7.2 or later
- Container Manager installed (via Package Center)
- SSH enabled on the NAS (Control Panel → Terminal & SNMP → Enable SSH service)

## 1. Get the code onto your NAS

Copy the project files from your Mac to the NAS using `scp`:

```bash
# Run this on your Mac, not on the NAS
scp -P 89 -r ~/workspace/jersey-minders your-user@your-nas-ip:/volume1/
```

This creates `/volume1/jersey-minders/` on the NAS with all project files.

Alternatively, drag the folder into **File Station** in the DSM web UI if you prefer not to use the terminal.

## 2. Configure your environment

```bash
cp .env.example .env
vi .env  # or nano .env
```

Set `ODDS_API_KEY` and enable at least one notification channel. See the main [README](../README.md) for full configuration options.

## 3. Set your timezone

Open `docker-compose.yml` and update the `TZ` value to match your timezone:

```yaml
environment:
  - TZ=America/Los_Angeles  # change to your timezone
```

A full list of valid timezone names is available at [en.wikipedia.org/wiki/List_of_tz_database_time_zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

## 4. Deploy via Container Manager (GUI)

1. Open **Container Manager** in DSM
2. Go to **Project → Create**
3. Set the project name (e.g. `jersey-minders`)
4. Set the path to the folder you cloned in step 1
5. Container Manager will detect `docker-compose.yml` automatically
6. Click **Next** → **Done**

Container Manager will build the image and start the container. The picks database is stored in a named Docker volume (`picks_data`) and persists across container restarts and rebuilds.

## 5. Deploy via SSH (alternative)

If you prefer the command line:

```bash
cd /volume1/jersey-minders
docker compose up -d --build
```

## Updating

To pull the latest code and rebuild:

```bash
cd /volume1/jersey-minders
git pull
docker compose up -d --build
```

In the Container Manager GUI you can also stop the project, then **Build** and **Start** again.

## Checking logs

**Via SSH:**
```bash
docker compose logs -f
```

**Via GUI:** Container Manager → Project → `jersey-minders` → Logs tab.

## Sending a test notification

```bash
docker compose exec jersey-minders python main.py --now
```

## Checking your win rate

```bash
docker compose exec jersey-minders python main.py --stats
```
