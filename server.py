#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.json"

PLACEHOLDER_URLS = {"", "PASTE_ICS_LINK_HERE"}

WINDOWS_TZ = {
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "Pacific Standard Time": "America/Los_Angeles",
    "UTC": "UTC",
}

MEETING_DOMAIN_PRIORITY = (
    "teams.microsoft.com",
    "zoom.us",
    "meet.google.com",
    "webex.com",
    "gotomeeting.com",
    "bluejeans.com",
    "chime.aws",
)

TEXT_FIELDS_FOR_LINKS = ("URL", "LOCATION", "DESCRIPTION", "X-ALT-DESC")


def load_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def configured_url(config: dict) -> str:
    url = str(config.get("ics_url", "")).strip()
    return "" if url in PLACEHOLDER_URLS else url


def get_zone(config: dict) -> ZoneInfo:
    return ZoneInfo(config.get("timezone", "America/New_York"))


def fetch_ics(ics_url: str) -> str:
    req = urllib.request.Request(
        ics_url,
        headers={
            "User-Agent": "local-outlook-dashboard/1.0",
            "Accept": "text/calendar,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset, errors="replace")


def unfold_ics_lines(raw: str) -> list[str]:
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def split_property(line: str) -> tuple[str, dict[str, str], str] | None:
    if ":" not in line:
        return None
    left, value = line.split(":", 1)
    parts = left.split(";")
    name = parts[0].upper()
    params: dict[str, str] = {}
    for part in parts[1:]:
        if "=" in part:
            key, val = part.split("=", 1)
            params[key.upper()] = val.strip('"')
    return name, params, value


def parse_ics(raw: str) -> list[dict[str, list[tuple[dict[str, str], str]]]]:
    events = []
    current: dict[str, list[tuple[dict[str, str], str]]] | None = None

    for line in unfold_ics_lines(raw):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
            continue
        if current is None:
            continue

        parsed = split_property(line)
        if not parsed:
            continue
        name, params, value = parsed
        current.setdefault(name, []).append((params, value))

    return events


def first_prop(event: dict, name: str) -> tuple[dict[str, str], str] | None:
    values = event.get(name.upper()) or []
    return values[0] if values else None


def text_prop(event: dict, name: str) -> str:
    prop = first_prop(event, name)
    return unescape_ics_text(prop[1]) if prop else ""


def unescape_ics_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def parse_dt(prop: tuple[dict[str, str], str] | None, default_zone: ZoneInfo) -> tuple[datetime | None, bool]:
    if not prop:
        return None, False

    params, raw_value = prop
    value = raw_value.strip()
    is_date_only = params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", value) is not None

    if is_date_only:
        parsed_date = datetime.strptime(value[:8], "%Y%m%d").date()
        return datetime.combine(parsed_date, time.min, default_zone), True

    tzid = params.get("TZID")
    zone_name = WINDOWS_TZ.get(tzid or "", tzid or "")
    event_zone = ZoneInfo(zone_name) if zone_name else default_zone

    if value.endswith("Z"):
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(default_zone), False

    fmt = "%Y%m%dT%H%M%S" if len(value) >= 15 else "%Y%m%dT%H%M"
    dt = datetime.strptime(value[:15] if fmt.endswith("%S") else value[:13], fmt).replace(tzinfo=event_zone)
    return dt.astimezone(default_zone), False


def parse_duration(value: str) -> timedelta | None:
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", value)
    if not match:
        return None
    days, hours, minutes, seconds = (int(x or 0) for x in match.groups())
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def parse_end(event: dict, start: datetime, all_day: bool, default_zone: ZoneInfo) -> datetime:
    parsed_end, _ = parse_dt(first_prop(event, "DTEND"), default_zone)
    if parsed_end:
        return parsed_end

    duration_prop = first_prop(event, "DURATION")
    if duration_prop:
        duration = parse_duration(duration_prop[1].strip())
        if duration:
            return start + duration

    return start + (timedelta(days=1) if all_day else timedelta(hours=1))


def parse_rrule(value: str) -> dict[str, str]:
    rule = {}
    for part in value.split(";"):
        if "=" in part:
            key, val = part.split("=", 1)
            rule[key.upper()] = val
    return rule


def parse_exdates(event: dict, default_zone: ZoneInfo) -> set[date]:
    excluded = set()
    for params, value in event.get("EXDATE", []):
        for raw_dt in value.split(","):
            dt, _ = parse_dt((params, raw_dt), default_zone)
            if dt:
                excluded.add(dt.date())
    return excluded


def weekday_code(d: date) -> str:
    return ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[d.weekday()]


def parse_until(rule: dict[str, str], default_zone: ZoneInfo) -> date | None:
    until = rule.get("UNTIL")
    if not until:
        return None
    dt, _ = parse_dt(({}, until), default_zone)
    return dt.date() if dt else None


def recurring_occurs_on(rule: dict[str, str], start_date: date, target_date: date, default_zone: ZoneInfo) -> bool:
    if target_date < start_date:
        return False

    until = parse_until(rule, default_zone)
    if until and target_date > until:
        return False

    count = int(rule.get("COUNT", "0") or "0")
    interval = max(1, int(rule.get("INTERVAL", "1") or "1"))
    freq = rule.get("FREQ", "").upper()
    days_since_start = (target_date - start_date).days

    if freq == "DAILY":
        if days_since_start % interval != 0:
            return False
        occurrence_index = days_since_start // interval + 1
        return not count or occurrence_index <= count

    if freq == "WEEKLY":
        bydays = {d[-2:] for d in rule.get("BYDAY", weekday_code(start_date)).split(",") if d}
        if weekday_code(target_date) not in bydays:
            return False
        weeks_since_start = days_since_start // 7
        if weeks_since_start % interval != 0:
            return False
        if not count:
            return True
        matching_days = 0
        current = start_date
        while current <= target_date:
            if weekday_code(current) in bydays and ((current - start_date).days // 7) % interval == 0:
                matching_days += 1
            current += timedelta(days=1)
        return matching_days <= count

    return False


def expand_event_for_day(event: dict, day: date, default_zone: ZoneInfo) -> list[dict]:
    start, all_day = parse_dt(first_prop(event, "DTSTART"), default_zone)
    if not start:
        return []

    end = parse_end(event, start, all_day, default_zone)
    day_start = datetime.combine(day, time.min, default_zone)
    day_end = day_start + timedelta(days=1)

    base = {
        "subject": text_prop(event, "SUMMARY") or "Untitled",
        "location": text_prop(event, "LOCATION"),
        "description": text_prop(event, "DESCRIPTION"),
        "url": text_prop(event, "URL"),
        "isAllDay": all_day,
    }

    def make_item(item_start: datetime, item_end: datetime) -> dict:
        item = dict(base)
        item.update(
            {
                "start": item_start.isoformat(),
                "end": item_end.isoformat(),
                "meetingUrl": find_meeting_url(event),
            }
        )
        return item

    if start < day_end and end > day_start:
        return [make_item(start, end)]

    rrule_prop = first_prop(event, "RRULE")
    if not rrule_prop:
        return []

    rule = parse_rrule(rrule_prop[1])
    excluded_dates = parse_exdates(event, default_zone)
    if day in excluded_dates or not recurring_occurs_on(rule, start.date(), day, default_zone):
        return []

    duration = end - start
    occurrence_start = datetime.combine(day, start.timetz(), default_zone)
    occurrence_end = occurrence_start + duration
    return [make_item(occurrence_start, occurrence_end)]


def find_meeting_url(event: dict) -> str:
    text_parts = []
    for field in TEXT_FIELDS_FOR_LINKS:
        for _, value in event.get(field, []):
            text_parts.append(unescape_ics_text(value))

    text_blob = html.unescape("\n".join(text_parts))
    urls = re.findall(r"https?://[^\s<>\"']+", text_blob)
    cleaned_urls = [u.rstrip(".,;)]}>") for u in urls]

    for domain in MEETING_DOMAIN_PRIORITY:
        for url in cleaned_urls:
            if domain in urllib.parse.urlparse(url).netloc.lower():
                return url
    return cleaned_urls[0] if cleaned_urls else ""


def today_events(config: dict) -> dict:
    zone = get_zone(config)
    ics_url = configured_url(config)
    if not ics_url:
        return {
            "status": "sample mode",
            "configured": False,
            "message": "Paste your Outlook ICS link into config.json.",
            "events": sample_events(zone),
        }

    raw_ics = fetch_ics(ics_url)
    requested_day = datetime.now(zone).date()
    events = []
    for event in parse_ics(raw_ics):
        events.extend(expand_event_for_day(event, requested_day, zone))

    events.sort(key=lambda e: e["start"])
    return {
        "status": "live ICS",
        "configured": True,
        "message": "",
        "events": events,
    }


def sample_events(zone: ZoneInfo) -> list[dict]:
    today = datetime.now(zone).date()

    def item(subject: str, h1: int, m1: int, h2: int, m2: int, location: str = "", link: str = "") -> dict:
        start = datetime.combine(today, time(h1, m1), zone)
        end = datetime.combine(today, time(h2, m2), zone)
        return {
            "subject": subject,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "location": location,
            "isAllDay": False,
            "meetingUrl": link,
        }

    return [
        item("Work / Internship", 7, 0, 16, 0, "Liverpool, NY"),
        item("Lunch + HDLBits", 12, 0, 13, 0),
        item("Research meeting", 21, 0, 21, 30, "Teams", "https://teams.microsoft.com/"),
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/events":
            self.handle_events()
            return
        if parsed.path in {"/", "/index.html"}:
            self.serve_file(ROOT / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_events(self) -> None:
        try:
            payload = today_events(load_config())
            self.send_json(payload)
        except Exception as error:
            self.send_json(
                {
                    "status": "error",
                    "configured": bool(configured_url(load_config())),
                    "message": str(error),
                    "events": [],
                },
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def serve_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("DASHBOARD_DEBUG") == "1":
            super().log_message(fmt, *args)


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "5173"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Dashboard running at http://{host}:{port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
