# Finance Pi — Setup Walkthrough (Pi with display)

This guide takes you from a freshly-imaged Raspberry Pi 5 to a working dashboard that
auto-launches on boot. Throughout, I'll tell you **where** each command runs, **what**
output to expect, and **why** the step exists, so when something looks off you'll know.

**Where each command runs is labelled with an icon:**
- 🥧 = type this on the **Pi**, in a terminal window on its desktop
- 🐳 = type this on the **Pi**, but it runs *inside the Docker app container*
- 💻 = do this on your **PC** (e.g. visit a website in a browser)

---

## Phase 1: Prepare the Pi

### 1.1 Install Raspberry Pi OS (with desktop)

You want the **full Raspberry Pi OS (64-bit, Bookworm)**, not Lite — you need a desktop
environment for the dashboard auto-launch.

In **Raspberry Pi Imager** on your PC:
- Device: Raspberry Pi 5
- OS: Raspberry Pi OS (64-bit) — the one *with desktop*, not Lite
- Storage: your SD card or NVMe
- Click the gear icon and pre-configure:
  - Hostname: `finance-pi`
  - Username: `pi`, password: a good one (write it down)
  - Wi-Fi if you're not using Ethernet
  - Locale: Europe/Amsterdam, NL keyboard
  - Enable SSH (handy for copy-pasting commands from your PC)

Flash, eject, plug into the Pi, connect monitor/keyboard/mouse, power on.

**Expected:** Pi boots into the Raspberry Pi OS desktop. First boot takes ~2 minutes.

### 1.2 First-time desktop setup

When the welcome wizard appears, click through it (or skip it). Make sure:
- Your timezone is **Amsterdam**
- Wi-Fi is connected (icon top-right)
- You can open Chromium and reach a website

**Why this matters:** the dashboard will auto-launch in this user session, so this
must be a desktop session that logs in automatically. We'll wire up auto-login in
Phase 6.

### 1.3 Update the system

Open a terminal (the black icon in the taskbar, or `Ctrl+Alt+T`):

🥧
```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git curl
```

**Expected output:** lots of "Reading package lists...", then a list of packages,
ending in something like "0 upgraded, 0 newly installed" (if already up to date) or
a longer install log.

**Why:** start from a known-good baseline; install git so we can pull your repo.

---

## Phase 2: Get the code

### 2.1 Clone your GitHub repo

🥧
```bash
cd ~
git clone https://github.com/YOUR-USERNAME/finance-pi.git
cd finance-pi
ls
```

**Expected output:**
```
README.md  CLAUDE.md  app  compose  data  design  docs  scripts  secrets
```

If your repo is private, git will prompt for a username + token (use a GitHub
Personal Access Token, not your account password — that hasn't worked since 2021).

**Why this lives in your home directory:** the systemd timer we set up later expects
the repo at `/home/pi/finance-pi`. If you put it elsewhere, you'll need to edit
`scripts/finance-sync.service` to match.

---

## Phase 3: Install Docker

### 3.1 Install Docker Engine

🥧
```bash
curl -fsSL https://get.docker.com | sh
```

This downloads and runs Docker's official install script. It takes a couple of
minutes.

**Expected output:** ends with something like *"To run docker as a non-root user...
WARNING: deprecated legacy Docker..."* — that's fine, we'll handle the non-root part next.

### 3.2 Let your user run Docker without sudo

🥧
```bash
sudo usermod -aG docker $USER
```

**No output is normal.** Now log out (Pi menu → Logout) and log back in for the
group change to take effect. Or just reboot:

🥧
```bash
sudo reboot
```

After it comes back, verify Docker works without sudo:

🥧
```bash
docker run --rm hello-world
```

**Expected output:** A "Hello from Docker!" message. If you instead get a
"permission denied" error, the group change hasn't applied — log out fully and back
in again.

**Why:** Docker needs root-equivalent privileges; adding your user to the `docker`
group avoids typing `sudo` for every command, which would also leak permissions
into files Docker creates.

---

## Phase 4: Configure secrets

### 4.1 Make a real `.env` from the template

🥧
```bash
cd ~/finance-pi
cp secrets/.env.example secrets/.env
```

**No output is normal.**

### 4.2 Generate strong passwords for Postgres and Grafana

🥧
```bash
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo "GRAFANA_PASSWORD=$(openssl rand -base64 32)"
```

**Expected output:** two lines with random-looking strings, e.g.:
```
POSTGRES_PASSWORD=K9j2L+m...long-random-string...=
GRAFANA_PASSWORD=xPq8wRv...different-random-string...=
```

Copy these strings into the `.env` file. Open it in the editor of your choice — the
GUI text editor (`Files` → `secrets` folder → right-click `.env` → Open with Text
Editor) is easiest if you've got a mouse:

🥧
```bash
nano secrets/.env
```

In nano, paste your generated passwords. Leave the other fields blank for now;
we'll fill in `EB_APP_ID`, `TELEGRAM_*`, and `PYTR_*` later in this guide.

Save with `Ctrl+O`, `Enter`, exit with `Ctrl+X`.

**Why we don't generate Telegram/EB creds yet:** those need external accounts to
exist first. We'll do them at the points where you need them, not upfront in a big
checklist.

### 4.3 Set the `EB_REDIRECT_URL`

Since you have a display, the simplest redirect URL for Enable Banking is just your
local Pi:

In your `.env`:
```
EB_REDIRECT_URL=http://localhost:8501/auth/callback
```

**Why:** PSD2 banks redirect you back to a configured URL after auth. With a
headless setup you'd need Tailscale and HTTPS; with a screen, the Pi's own browser
can handle the redirect locally and you can read the code off the URL bar.

---

## Phase 5: Bring up the basic stack

We'll do this in stages so you can verify each layer before adding the next.

### 5.1 Start just Postgres

🥧
```bash
cd ~/finance-pi
docker compose -f compose/docker-compose.yml up -d postgres
```

The `-d` means "detached" — runs in the background.

**Expected output:**
```
[+] Running 1/1
 ✓ Container finance-postgres  Started
```

The first time, Docker has to download the Postgres image (~80 MB), so it'll take
30–60 seconds. Subsequent starts are instant.

### 5.2 Wait for Postgres to be healthy and verify

🥧
```bash
docker compose -f compose/docker-compose.yml ps
```

**Expected output:**
```
NAME                IMAGE                  STATUS                   PORTS
finance-postgres    postgres:16-alpine     Up X seconds (healthy)   127.0.0.1:5432->5432/tcp
```

Wait until you see `(healthy)`. If it says `(starting)`, wait 10 seconds and run
again. If it says `(unhealthy)` or `Exited`, check the logs:

🥧
```bash
docker compose -f compose/docker-compose.yml logs postgres
```

A common first-run issue is a leftover `data/postgres/` directory from a previous
attempt — if so, `docker compose down` then `sudo rm -rf data/postgres` and retry.

**Why we wait for healthy:** the schema apply step in 5.3 will fail if Postgres
isn't accepting connections yet.

### 5.3 Apply the database schema

🥧
```bash
docker compose -f compose/docker-compose.yml exec -T postgres \
    psql -U finance -d finance < app/sql/001_init.sql
```

**Expected output:** a long stream of `CREATE TABLE`, `CREATE INDEX`, and `INSERT 0
N` messages. The last few lines should look like:
```
CREATE TABLE
CREATE VIEW
CREATE TABLE
CREATE TABLE
```

If you see any `ERROR` lines, copy them and stop — something's wrong with the
schema for your specific Postgres version. Most likely fix is checking Postgres is
really `16-alpine` (`docker compose ps` shows the image).

Then load the seed rules:

🥧
```bash
docker compose -f compose/docker-compose.yml exec -T postgres \
    psql -U finance -d finance < app/sql/002_seed_rules.sql
```

**Expected output:** many `INSERT 0 1` lines and one `UPDATE 1` at the end.

### 5.4 Sanity-check the schema

🥧
```bash
docker compose -f compose/docker-compose.yml exec postgres \
    psql -U finance -d finance -c "\dt"
```

**Expected output:** a table listing accounts, balances, car_expenses, categories,
consents, holdings, instruments, manual_assets, odometer_readings, prices, rules,
sync_runs, transactions, vehicles. Fourteen tables.

```
 Schema |        Name        | Type  |  Owner
--------+--------------------+-------+---------
 public | accounts           | table | finance
 public | balances           | table | finance
 ...
```

**Why this check:** if any tables are missing here, no later step will work
properly. It's worth catching now.

### 5.5 Build and start the app container

🥧
```bash
docker compose -f compose/docker-compose.yml up -d --build app
```

**Expected:** Docker will build the image (this takes 3–5 minutes the first time —
it's installing Python dependencies). You'll see lots of `pip install` output.

When it finishes:
```
[+] Running 1/1
 ✓ Container finance-app  Started
```

Check it's running:

🥧
```bash
docker compose -f compose/docker-compose.yml ps
```

You should now see both `finance-postgres (healthy)` and `finance-app (running)`.

### 5.6 First look at the dashboard

Open Chromium on the Pi and go to:

```
http://localhost:8501
```

**Expected:** the Finance Pi dashboard loads, showing six tabs (Overview, Transactions,
Categories, Investments, 🚗 Car, Manual assets). All the cards will be empty or zero
— that's correct, you haven't connected any data sources yet.

If the page doesn't load:

🥧
```bash
docker compose -f compose/docker-compose.yml logs app
```

Look for Python errors. Most common at this stage: `DATABASE_URL` typo in `.env`,
or `EB_KEY_PATH` referencing a file that doesn't exist yet (it doesn't need to
exist for the dashboard to render — but if you see import errors complaining about
it, the app container loaded `enable_banking.py` at startup).

### 5.7 Start Grafana

🥧
```bash
docker compose -f compose/docker-compose.yml up -d grafana
```

After it boots (~15 seconds), open `http://localhost:3000` in Chromium. Log in with
`admin` / *your `GRAFANA_PASSWORD` from `.env`*. You'll get prompted to change it
on first login.

**Why start Grafana later:** the dashboard alone is enough to use the system. Grafana
is for pretty time-series charts, which only become interesting once you have weeks
of data.

---

## Phase 6: Auto-launch the dashboard on boot

Now we make the Pi behave like an appliance: power on → desktop → dashboard fullscreen.

### 6.1 Enable auto-login to the desktop

🥧
```bash
sudo raspi-config
```

This opens a blue text-mode menu. Navigate with arrow keys:

1. **System Options** → press Enter
2. **Boot / Auto Login** → press Enter
3. **Desktop Autologin** → press Enter
4. Press Tab → Tab → Enter on `<Finish>`
5. When asked to reboot, choose `<No>` — we have more to set up first.

**Why:** without auto-login, the Pi will sit at the login screen on boot and the
dashboard won't open.

### 6.2 Create a wait-for-dashboard script

The Streamlit dashboard takes 10–30 seconds to come up after the Pi boots, because
Docker has to start the containers first. We need a script that waits for it before
launching Chromium, otherwise the browser opens to "connection refused".

🥧
```bash
mkdir -p ~/.config/autostart
nano ~/finance-pi/scripts/launch-dashboard.sh
```

Paste this into nano:

```bash
#!/bin/bash
# Wait for the Streamlit dashboard to be ready, then launch Chromium fullscreen.

# Hide the mouse cursor when idle (optional, makes it feel more appliance-y)
# unclutter -idle 3 &

# Poll until the dashboard responds
until curl -sf http://localhost:8501 > /dev/null; do
    sleep 2
done

# Small extra delay so Streamlit fully initialises its UI
sleep 3

# Launch Chromium in fullscreen, pointed at the dashboard.
# --start-fullscreen lets you press F11 to exit; --kiosk would lock you in.
chromium-browser \
    --start-fullscreen \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --check-for-update-interval=31536000 \
    http://localhost:8501
```

Save (`Ctrl+O`, Enter, `Ctrl+X`), then make it executable:

🥧
```bash
chmod +x ~/finance-pi/scripts/launch-dashboard.sh
```

**Why `--start-fullscreen` instead of `--kiosk`:** kiosk mode disables right-click,
ctrl-T (new tab), and exit. Fullscreen is the same look but you can press F11 to
exit, alt-tab to other apps, or open a terminal when you need to. Easier to
maintain.

### 6.3 Register it as a desktop autostart entry

🥧
```bash
nano ~/.config/autostart/finance-dashboard.desktop
```

Paste this:

```ini
[Desktop Entry]
Type=Application
Name=Finance Pi Dashboard
Comment=Auto-launch the dashboard in Chromium fullscreen
Exec=/home/pi/finance-pi/scripts/launch-dashboard.sh
X-GNOME-Autostart-enabled=true
NoDisplay=false
```

Save and exit.

**Why this file:** the desktop environment (whatever Pi OS Bookworm uses — Wayfire
on Pi 5) scans `~/.config/autostart/*.desktop` for things to run on session start.
This is the most portable way to add startup apps and survives OS upgrades better
than tweaking compositor-specific config files.

### 6.4 Reboot and verify

🥧
```bash
sudo reboot
```

**Expected sequence after reboot:**
1. Pi boots (~30 seconds)
2. Desktop loads, no login prompt
3. ~30 seconds of "blank desktop" while Docker starts and the script polls
4. Chromium opens fullscreen on the dashboard

If Chromium doesn't open, drop to a terminal (`Ctrl+Alt+T`) and run the script
manually to see what's failing:

🥧
```bash
~/finance-pi/scripts/launch-dashboard.sh
```

If it just sits at the `until curl` loop forever, your app container isn't running.
Check with `docker compose -f compose/docker-compose.yml ps`.

---

## Phase 7: Wire up the data sources

The dashboard is alive but empty. Time to feed it.

### 7.1 Register your Enable Banking application

This part is browser-only, no terminal needed.

💻 (you can do this in Chromium on the Pi itself, doesn't have to be your PC):

1. Visit **https://enablebanking.com**
2. Sign up → verify email
3. Control Panel → Applications → **New Application**
4. Application type: **Personal** (free tier)
5. Country: **Netherlands**
6. Redirect URL: paste exactly `http://localhost:8501/auth/callback`
7. You'll need to upload a public key — we generate that next.

Leave that tab open; you'll come back to it in 7.3.

### 7.2 Generate the Enable Banking key pair

🥧
```bash
cd ~/finance-pi/secrets
openssl genrsa -out enable_banking.pem 2048
openssl rsa -in enable_banking.pem -pubout -out enable_banking_public.pem
chmod 600 enable_banking.pem
ls -la
```

**Expected output:** you should see `enable_banking.pem` (the private key, kept
secret on the Pi) and `enable_banking_public.pem` (the one you upload). The
private key should show `-rw-------` permissions thanks to the `chmod 600`.

**Why a key pair:** Enable Banking authenticates your app via signed JWT requests
— much more secure than an API key. You sign with the private key, they verify
with the public one.

### 7.3 Upload the public key and grab your App ID

Back in the Enable Banking tab from 7.1:

1. Upload `~/finance-pi/secrets/enable_banking_public.pem` (use the file picker —
   show hidden files if needed: `Ctrl+H` in the dialog)
2. Submit the form
3. They'll show you an **Application ID** that looks like
   `abc12345-6789-...-fedcba987654`. Copy it.

🥧 Open `~/finance-pi/secrets/.env` in nano and paste it on the `EB_APP_ID=` line:
```
EB_APP_ID=abc12345-6789-...-fedcba987654
```

Save and exit.

🥧 Restart the app container so it picks up the new env value:
```bash
cd ~/finance-pi
docker compose -f compose/docker-compose.yml restart app
```

### 7.4 Bootstrap your 90-day Rabobank consent

This is the only "interactive" step in the whole setup. You'll run a command that
prints a URL, you open the URL on your phone where the Rabo Bankieren app lives,
you approve, and your phone redirects to a URL containing a `code=` parameter that
you paste back.

🥧
```bash
cd ~/finance-pi
docker compose -f compose/docker-compose.yml run --rm -it app python -m src.bootstrap_eb
```

🐳 (You're now talking to the script inside the container.)

**Expected prompts:**
```
Redirect URL: [type http://localhost:8501/auth/callback and Enter]

Open this URL on the phone where Rabo Bankieren is installed:

  https://psd2.rabobank.nl/oauth2/authorize?...

After approving, the bank will redirect to:
  http://localhost:8501/auth/callback?code=XXXX&state=...

Paste the 'code' parameter from the redirect URL:
```

Steps:
1. Type the URL it prints into your phone's browser (or scan a QR code if you
   make one — `qrencode` works for this).
2. Rabobank's app handles the approval flow.
3. After approval, the bank redirects your phone to `localhost:8501/auth/callback?code=...`.
   Your phone will show an error page because `localhost` on your phone isn't your
   Pi — **that's fine**, you just need the URL from the address bar.
4. Look at the address bar on your phone and find the `code=` parameter. It's the
   long string after `code=` and before `&state=`.
5. Type/paste that code into the terminal prompt and press Enter.

**Expected final output:**
```
✓ Active session: <some session id>
Your Rabobank accounts have been added to the database.
```

If you check the dashboard now, the Accounts row in the Overview tab should
populate with your Rabobank accounts (Betaalrekening, Spaarrekening, Credit Card).
Balances might be zero until the first sync runs.

**Why this is good for 90 days:** PSD2 caps consent at 90 days, after which
you'll get a Telegram alert and have to repeat this dance. Two minutes, four
times a year.

### 7.5 Bootstrap Trade Republic

🥧 First, add your TR credentials to `.env`:
```bash
nano ~/finance-pi/secrets/.env
```

Fill in:
```
PYTR_PHONE=+31612345678   # your TR-registered phone, international format
PYTR_PIN=1234              # your TR 4-digit PIN
```

Save and exit.

🥧 Now log in with pytr:
```bash
cd ~/finance-pi
docker compose -f compose/docker-compose.yml run --rm -it \
    -e PYTR_PHONE="$PYTR_PHONE" -e PYTR_PIN="$PYTR_PIN" \
    app pytr login --phone_no "$PYTR_PHONE" --pin "$PYTR_PIN"
```

**Expected:** pytr prints something like "Enter the verification token sent to
your device". Your TR app will get a push notification — approve it.

**Expected final output:** something like `web login was successful, see ~/.pytr/credentials`.

The keyfile is now persisted in `~/finance-pi/secrets/pytr/` and will be reused on
every sync.

### 7.6 (Optional) Set up the Telegram bot

This gives you push notifications when syncs succeed or fail.

On your phone, message **@BotFather** in Telegram:
1. Send `/newbot`
2. Pick a name and a username for your bot
3. BotFather replies with your bot **token** — copy it

Now find your chat ID. Message your new bot once (anything will do), then on the
Pi:

🥧
```bash
TOKEN="paste-your-bot-token-here"
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates" | grep -o '"id":[0-9]*' | head -1
```

**Expected output:** something like `"id":123456789` — that number is your chat ID.

🥧 Put both into `.env`:
```
TELEGRAM_BOT_TOKEN=<the long token>
TELEGRAM_CHAT_ID=<the chat id>
```

Test it:

🥧
```bash
cd ~/finance-pi
docker compose -f compose/docker-compose.yml run --rm app python -c \
    "from src.notifier import notify; notify('Hello from Finance Pi 👋')"
```

You should get the message on your phone in Telegram within a few seconds.

**Why optional:** the system works fine without Telegram; you'll just need to
check the dashboard's sync log manually. But the 90-day consent expiry warning is
a really nice thing to have pushed to your phone.

---

## Phase 8: First real sync

Run the orchestrator once manually so you can see the output and verify everything
works before scheduling it.

🥧
```bash
cd ~/finance-pi
docker compose -f compose/docker-compose.yml run --rm app python -m src.orchestrator
```

**Expected output:** roughly one block per step:
```
✓ Rabobank synced
✓ Trade Republic: 47 new, 0 skipped
✓ Updated 8 instrument prices
✓ Categorized 41 new transactions
```

If you get Telegram notifications too, even better.

If a step fails, you'll see a Python traceback. Most common at this point:
- **Rabobank fails with 401 / "no active session"** → consent didn't save properly,
  redo step 7.4.
- **Trade Republic fails with auth error** → pytr keyfile got lost; redo 7.5.

Now refresh `http://localhost:8501` in Chromium. You should see your transactions,
balances, and accounts populated.

---

## Phase 9: Automate the daily sync

Until now you've been running syncs by hand. Let's automate.

### 9.1 Install the systemd service and timer

🥧
```bash
sudo cp ~/finance-pi/scripts/finance-sync.service /etc/systemd/system/
sudo cp ~/finance-pi/scripts/finance-sync.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finance-sync.timer
```

**Expected output:**
```
Created symlink /etc/systemd/system/timers.target.wants/finance-sync.timer
  → /etc/systemd/system/finance-sync.timer.
```

### 9.2 Verify the timer is scheduled

🥧
```bash
systemctl list-timers finance-sync.timer
```

**Expected output:**
```
NEXT                         LEFT          LAST  PASSED  UNIT                 ACTIVATES
Wed 2026-05-22 06:00:00 CEST  18h left      n/a   n/a     finance-sync.timer   finance-sync.service
```

That `NEXT` column tells you when the next sync will run.

### 9.3 Optional: test the service manually

🥧
```bash
sudo systemctl start finance-sync.service
journalctl -u finance-sync.service -f
```

**Expected:** you'll see live logs of the sync running. Press `Ctrl+C` to stop
watching (the service keeps running until done).

**Why systemd over cron:** systemd timers handle "what if the Pi was off when the
sync should have run" elegantly via `Persistent=true` in the timer file — when the
Pi comes back online, it runs the missed sync.

---

## Phase 10: Daily life

### What you do regularly

- **Open the dashboard** — it's always there when you turn the Pi on.
- **Tag uncategorized transactions** — every week or two, check the Transactions
  tab for ones the auto-categorizer missed. As you tag, add rules for next time.
- **Add odometer readings** for your car — once a month is plenty.
- **Add manual car expenses** as they happen — APK, tires, garage repairs paid in
  cash.
- **Update manual assets** when their value changes — yearly for jewelry, monthly
  for cash, etc.
- **Drop CSVs** from GBI Sparen and Rabo Beleggen into `data/imports/gbi/` and
  `data/imports/rabo_invest/` monthly. The next sync picks them up.

### Every ~90 days

You'll get a Telegram alert (if you set it up) saying the Rabobank consent is
about to expire. Repeat step 7.4 — takes two minutes.

### When you change code on your PC and want to deploy

💻 (on your PC):
```bash
git add . && git commit -m "describe change" && git push
```

🥧 (on the Pi):
```bash
cd ~/finance-pi
git pull
docker compose -f compose/docker-compose.yml up -d --build
```

That's your deploy cycle.

### Where to look when things break

🥧
```bash
# Recent sync runs (status + row counts)
docker compose -f compose/docker-compose.yml exec postgres \
    psql -U finance -d finance -c \
    "SELECT started_at, provider, status, rows_inserted, error_message FROM sync_runs ORDER BY started_at DESC LIMIT 10;"

# Live app logs
docker compose -f compose/docker-compose.yml logs -f app

# What did the daily timer do?
journalctl -u finance-sync.service --since "yesterday"

# Is everything actually running?
docker compose -f compose/docker-compose.yml ps
```

### Exiting fullscreen / accessing the desktop

Press **F11** to exit Chromium fullscreen. Use the taskbar to open a terminal,
file manager, or anything else. Press F11 again to go back fullscreen.

If you want to permanently turn off the auto-launch (e.g. for maintenance):

🥧
```bash
mv ~/.config/autostart/finance-dashboard.desktop ~/.config/autostart/finance-dashboard.desktop.disabled
sudo reboot
```

And to re-enable:

🥧
```bash
mv ~/.config/autostart/finance-dashboard.desktop.disabled ~/.config/autostart/finance-dashboard.desktop
```

---

## Phase 11: Backups (do this once, then forget)

Postgres is the only thing on the Pi you can't easily replace. Set up a backup
schedule so a dying SD card doesn't lose your finance history.

🥧
```bash
chmod +x ~/finance-pi/scripts/backup.sh
crontab -e
```

If this is your first crontab, it'll ask which editor — pick `nano` (option 1).

Add this line at the bottom:
```
0 3 * * * /home/pi/finance-pi/scripts/backup.sh >> /home/pi/finance-pi/backups/backup.log 2>&1
```

Save and exit.

**Expected output after saving:** `crontab: installing new crontab` and you're
back at the prompt.

**What this does:** runs `backup.sh` every day at 03:00. The script dumps Postgres,
gzips it, writes to `~/finance-pi/backups/finance-YYYYMMDD-HHMMSS.sql.gz`, and
keeps the last 30 days.

**Want offsite?** Edit `scripts/backup.sh` and uncomment the `rclone copy` line,
after running `rclone config` on the Pi to set up a free Backblaze B2 bucket or
Google Drive folder.

---

## Done

After all this, your Pi:
- Boots into the dashboard automatically
- Syncs every morning at 06:00 from Rabobank, Trade Republic, and any CSVs you've
  dropped in
- Auto-categorizes new transactions
- Notifies you on Telegram when something goes wrong
- Backs up to disk nightly at 03:00
- Reminds you to renew Rabobank consent two weeks before expiry

The only thing you actively need to do is tag uncategorized transactions weekly
and add manual entries when relevant. Everything else runs itself.
