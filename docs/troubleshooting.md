# Troubleshooting

## Enable Banking consent expired
`python -m src.bootstrap_eb` to renew. Takes 30 seconds with the Rabobank app.

## pytr fails with auth error
Trade Republic sometimes invalidates the device key. Re-login:
```bash
docker compose -f compose/docker-compose.yml run --rm -it app pytr login
```

## Categorization is wrong
Open the dashboard → Transactions tab → find the misclassified row → fix it.
Then add a rule via SQL or the UI (UI rule editor not yet built — for now,
add to `app/sql/002_seed_rules.sql` and re-run that migration).

## Docker container OOM-killed
Pi 5 8 GB should be plenty. If you're on 4 GB, add swap:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Dashboard not loading
Check the app container logs:
```bash
docker compose -f compose/docker-compose.yml logs -f app
```

## Postgres won't start
Likely a permissions issue on the data volume. Check ownership:
```bash
ls -la data/postgres
sudo chown -R 70:70 data/postgres  # postgres user inside the container
```

## yfinance rate-limited
Yahoo Finance throttles aggressively. The price updater retries on failure.
If you see persistent errors, space out updates: run prices.update_all_prices()
once a week rather than daily.

## CoinGecko rate-limited
Free tier is 10-30 calls/min. With only a handful of crypto holdings this
should never be an issue. If it is, add a coin_id cache.
