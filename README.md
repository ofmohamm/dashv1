# Calendar Dashboard

A full-screen desk display that shows the time, local weather, and your
upcoming Outlook calendar events — with the current or next event highlighted
and a live countdown. Runs as a small local web page; nothing is exposed to
the internet.

<!-- Add a screenshot here -->
<!-- ![Dashboard screenshot](docs/screenshot.png) -->

## Setup

1. Start the server from this folder:

   ```bash
   python3 server.py      # Mac/Linux
   py server.py           # Windows
   ```

2. Open the dashboard in your browser:

   ```text
   http://127.0.0.1:5173/
   ```

3. Click the ✎ (edit) button in the top-right. The settings panel walks you
   through connecting your Outlook calendar (it links you straight to
   Outlook's publish page and checks the link you paste), and also lets you
   set your weather city and pick a background.

Press `F11` (or the fullscreen button, top-right) for a clean display.

## What it does

- **Agenda** — today's upcoming events, rolling into the next days when today
  is quiet ("No more events today"). Past events drop off automatically;
  anything that doesn't fit shows as "+N more".
- **Next up** — the current or next event is marked with an accent rail and a
  live label: "Now", "Starts in 24 min", or "Next".
- **Click to join** — events with a Teams/Zoom/Meet link open it directly.
- **Always fresh** — refreshes every minute (and instantly when the screen
  wakes). If the network drops, the last agenda stays up with an
  "Offline · updated Nm ago" note.

## Run it in the background (Windows)

So the dashboard keeps running after you close the terminal and starts itself
when you log in:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

This registers a Scheduled Task that runs the server windowlessly with
`pythonw`, restarts it if it ever stops, and launches it at every log on.
Then make a browser shortcut to `http://127.0.0.1:5173/` (or open it with
`--kiosk` for a dedicated display).

To remove it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
```

## Notes

- Settings are saved to `config.json` in this folder. Your calendar link is
  private — keep that file out of git (it's already in `.gitignore`).
- Outlook regenerates published calendar feeds on its own schedule, so a
  brand-new event can take a while to appear no matter how often the
  dashboard polls.
- If nothing shows up, open `http://127.0.0.1:5173/api/events` to see the raw
  data or error.
