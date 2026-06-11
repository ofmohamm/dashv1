# Calendar Dashboard

A simple full-screen wall/desk display that shows the time, local weather, and your upcoming calendar events. It reads your calendar from a published Outlook calendar link and runs as a small local web page — nothing is exposed to the internet.

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

3. Click the ✎ (edit) button in the top-right and follow the steps to connect
   your Outlook calendar. You can also set your weather location and pick a
   background there.

Press `F11` (or the fullscreen button, top-right) for a clean display.

## Run it in the background (Windows)

So the dashboard keeps running after you close the terminal and starts itself
when you log in:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

This registers a Scheduled Task that runs the server windowlessly with
`pythonw`, restarts it if it ever stops, and launches it at every log on. Then
just open `http://127.0.0.1:5173/` (tip: make a browser shortcut to that URL,
or open it with `--kiosk` for a dedicated display).

To remove it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
```

## Notes

- Settings are saved to `config.json` in this folder. Your calendar link is
  private — keep that file out of git (it's already in `.gitignore`).
- If nothing shows up, open `http://127.0.0.1:5173/api/events` to see the raw
  data or error.
