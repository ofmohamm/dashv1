# Syracuse ICS Dashboard

A local web dashboard with the same calm Tabliss-style vibe: large clock, Syracuse weather, and a glass Outlook agenda card.

This version uses your Outlook **ICS link**, not Microsoft Graph / Entra.

## Why this version

- No Microsoft app registration.
- No Entra access needed.
- Calendar fetch happens from a local Python server on your own machine.
- The dashboard runs at `127.0.0.1`, so it is not exposed to your Wi-Fi network.
- If an event description/location has a Teams, Zoom, Meet, Webex, or other meeting URL, clicking the event opens that link.

## Setup

1. Open `config.json`.
2. Replace this:

```json
"ics_url": "PASTE_ICS_LINK_HERE"
```

with your Outlook ICS link.

Keep the link inside the quotes.

## Run locally

From the dashboard folder:

### Windows

```bash
py server.py
```

### Mac/Linux

```bash
python3 server.py
```

Then open:

```text
http://127.0.0.1:5173/
```

## Fullscreen

- Click the `Fullscreen` button in the top-right, or
- Press `F11` in Chrome/Edge.

## Make it feel like a dedicated display

In Chrome/Edge, open:

```text
http://127.0.0.1:5173/
```

Then press `F11`.

You can also create a desktop shortcut to that URL and place it on the second display.

## Privacy notes

Your ICS link is a secret URL. Anyone with that link could see whatever calendar detail level you published. Keep `config.json` private and do not upload it to GitHub.

The `.gitignore` file ignores `config.json` so you do not accidentally commit your private link.

## Recurring events

One-off events work. Simple daily and weekly recurring events are also supported. More complex recurrence rules may not display perfectly.

## If events do not show

- Make sure the ICS link is pasted into `config.json`.
- Stop and restart `server.py` after editing `config.json`.
- Open `http://127.0.0.1:5173/api/events` to see the raw event output or error.
- If the ICS link starts with `webcal://`, change it to `https://`.
