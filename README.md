# Calendar Dashboard

A simple full-screen wall/desk display that shows the time, local weather, and your upcoming calendar events. It reads your calendar from an Outlook **ICS link** and runs as a small local web page — nothing is exposed to the internet.

<!-- Add a screenshot here -->
<!-- ![Dashboard screenshot](docs/screenshot.png) -->

## Setup

1. Open `config.json` and paste your Outlook ICS link between the quotes:

   ```json
   "ics_url": "https://outlook.office365.com/owa/calendar/.../calendar.ics"
   ```

2. Start the server from this folder:

   ```bash
   python3 server.py      # Mac/Linux
   py server.py           # Windows
   ```

3. Open the dashboard in your browser:

   ```text
   http://127.0.0.1:5173/
   ```

Press `F11` (or the **Fullscreen** button, top-right) for a clean display.

## Notes

- Your ICS link is private — keep `config.json` out of git (it's already in `.gitignore`).
- After editing `config.json`, restart `server.py`.
- If nothing shows up, open `http://127.0.0.1:5173/api/events` to see the raw data or error. If your link starts with `webcal://`, change it to `https://`.
