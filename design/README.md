# Finance Pi — Design System

This folder is the source of truth for how the dashboard looks. When using
Claude Design (or any other LLM tool), point it at this folder for context.

## Files

- `tokens.css` — color, spacing, typography, radius variables (the *only* place
  these are defined). All Streamlit-injected CSS reads from here.
- `mockups.md` — written specifications and ASCII mockups for every widget.
- `palette.md` — color tokens, the rationale behind each, and accessibility notes.

## Design principles

1. **Data-first.** Numbers should be the loudest thing on the page. Chrome stays muted.
2. **Glanceability.** The Overview tab must answer "am I OK?" in 2 seconds. Total wealth at the top, current month's net cashflow trend below.
3. **No fake precision.** Show 2 decimals for EUR amounts above €100, 0 decimals above €10k. Don't show €1,234.5673921.
4. **Negative numbers in red, positive in green** — but desaturate, not fluorescent. The eye should rest, not strobe.
5. **NL conventions.** € symbol on the left with a space (`€ 1.234,56` rendered, but stored as `1234.56`). Dates in `YYYY-MM-DD` for sortability.

## How to change the design

When you (or Claude Design) modify the dashboard:

1. **Update `mockups.md` first** with the new widget spec.
2. **If introducing new visual primitives** (a new color, a new font), add tokens to `tokens.css`.
3. **Update `app/src/dashboard.py`** to render the change.
4. **Test on mobile** — the dashboard is also viewed on phones via Tailscale.

## Layout grid

Streamlit's default 12-column layout is used, with these conventions:

- **Overview top row:** 4 equal metric cards (`st.columns(4)` with `st.metric`)
- **Account row:** dynamic columns, up to 4 per row, wrap below
- **Charts:** full width unless paired (`use_container_width=True`)
- **Forms:** 2-column inside a single `st.form()`

## Typography

- Numbers: tabular-nums (set in `tokens.css`) — so columns of euros line up
- Labels: weight 500
- Body: default Streamlit (Source Sans Pro)

## Inspiration / non-goals

- Inspired by Monarch Money, YNAB, and Beancount's Fava.
- **Not** trying to look like a bank app. This is a personal tool — clarity over polish.
