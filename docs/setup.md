# Setup walkthrough

This is the step-by-step for getting Finance Pi running on a fresh Raspberry Pi 5.

If you'd rather just skim, see [README.md](../README.md). This doc has the details.

---

## 0. Prerequisites

- Raspberry Pi 5 (4 GB or 8 GB)
- 32+ GB SD card, or (recommended) NVMe via the Pi 5 HAT
- Active cooling — the Pi 5 throttles hard without it
- Ethernet cable for stable headless operation
- A laptop for the initial flashing

## 1. Flash the OS

Use **Raspberry Pi Imager** (raspberrypi.com).

- OS: Raspberry Pi OS Lite (64-bit)
- Hostname: `finance-pi`
- Enable SSH (we'll switch to key-based shortly)
- Username `pi`, strong password
- Locale: Europe/Amsterdam, NL keyboard

Flash, insert, plug in Ethernet and power. Wait two minutes.

```bash
ssh pi@finance-pi.local
```

## 2. Clone the repo and run setup

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/<your-username>/finance-pi.git
cd finance-pi

# Copy and edit secrets
cp secrets/.env.example secrets/.env
nano secrets/.env

# Run the idempotent setup script — it will install Docker, Tailscale,
# set up the firewall, generate keys, start the stack, and apply the schema.
./scripts/setup-pi.sh
```

If the script tells you to log out and back in (after installing Docker), do so
and re-run it. The script is idempotent — run as many times as you want.

## 3. Register your Enable Banking application

This step needs a browser, so do it from your laptop:

1. Sign up at **https://enablebanking.com**
2. Verify email → Control Panel → Applications → New Application
3. Application type: **Personal** (free tier)
4. Country: **Netherlands**
5. Redirect URL: e.g. `https://finance-pi.<your-tailnet>.ts.net/auth/callback`
   - For local testing: `http://localhost:8501/auth/callback`
6. Upload the public key file the setup script generated (`secrets/enable_banking_public.pem`)
7. Copy the **Application ID** Enable Banking returns into `secrets/.env` as `EB_APP_ID`

## 4. Bootstrap the 90-day consent (Rabobank)

```bash
docker compose -f compose/docker-compose.yml run --rm -it app python -m src.bootstrap_eb
```

Follow the prompts. You'll get a URL → open it in your phone where the
Rabo Bankieren app is installed → authenticate → bank redirects you to your
configured redirect URL with `?code=XXXX&state=YYYY` → paste the `code` value
back into the prompt.

After this you've got a session token good for 90 days, and your Rabobank
accounts (current, savings, credit card) are in the database.

## 5. Bootstrap Trade Republic

```bash
docker compose -f compose/docker-compose.yml run --rm -it app pytr login \
    --phone_no "$PYTR_PHONE" --pin "$PYTR_PIN"
```

Approve on your TR app when prompted. The keyfile is saved to
`secrets/pytr/keyfile.pem` (mounted into the container).

## 6. First sync

Run the orchestrator manually to confirm everything works:

```bash
docker compose -f compose/docker-compose.yml run --rm app python -m src.orchestrator
```

You should see Telegram notifications (if configured) and rows appear in the
`transactions` table.

## 7. GBI Sparen — first manual import

GBI Sparen has no API. Once a month:

1. Open the GBI Sparen mobile app
2. Statements → Download CSV (or PDF if CSV unavailable)
3. Email or AirDrop the file to your laptop
4. SCP it to the Pi:
   ```bash
   scp gbi-statement-2026-05.csv pi@finance-pi.local:~/finance-pi/data/imports/gbi/
   ```
   Or, easier: upload via the Streamlit dashboard's "Manual import" widget.
5. Next sync run picks it up.

## 8. Enable the daily timer

```bash
sudo cp scripts/finance-sync.service /etc/systemd/system/
sudo cp scripts/finance-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finance-sync.timer
systemctl list-timers finance-sync.timer
```

## 9. Add your vehicle

Open the dashboard → 🚗 Car tab → fill in the form. For the Swift Sport 2021:

- Name: Swift Sport
- Make: Suzuki, Model: Swift Sport 1.4 Hybrid Boosterjet
- Year: 2021
- Purchase odometer: whatever the dashboard read on the day you bought it
- Purchase price: what you paid

Then add an odometer reading every month or so. The cost-per-km will start
populating after the first reading + a few synced fuel transactions.

## 10. Add investments and assets

In the dashboard:

- **Investments tab** → click "Seed common instruments" to register VWCE, IWDA,
  BTC, ETH, gold, silver. Then add individual holdings via the form.
- **Manual assets tab** → add cash in wallet, jewelry, anything else valuable.

## You're done

The system will now sync daily at 06:00. Spend a weekend tagging your first
month of transactions and adding rules in the Transactions tab. After that,
auto-categorization will handle 80–90%+ and you'll only intervene on edge cases.
