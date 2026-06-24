#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import sys
import time as time_module
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

DEFAULT_CONFIG = {
    "ics_url": "",
    "timezone": "America/New_York",
    "display_city": "Syracuse",
    "weather": {"latitude": 43.0481, "longitude": -76.1474},
}

PLACEHOLDER_URLS = {"", "PASTE_ICS_LINK_HERE"}

# Outlook stamps events with Windows time-zone names; Python's zoneinfo only
# understands IANA names. This is the standard CLDR windowsZones mapping
# (default territory). Anything not listed falls back to the configured zone
# in resolve_zone() rather than crashing the feed.
WINDOWS_TZ = {
    "Dateline Standard Time": "Etc/GMT+12",
    "UTC-11": "Etc/GMT+11",
    "Aleutian Standard Time": "America/Adak",
    "Hawaiian Standard Time": "Pacific/Honolulu",
    "Marquesas Standard Time": "Pacific/Marquesas",
    "Alaskan Standard Time": "America/Anchorage",
    "UTC-09": "Etc/GMT+9",
    "Pacific Standard Time (Mexico)": "America/Tijuana",
    "UTC-08": "Etc/GMT+8",
    "Pacific Standard Time": "America/Los_Angeles",
    "US Mountain Standard Time": "America/Phoenix",
    "Mountain Standard Time (Mexico)": "America/Mazatlan",
    "Mountain Standard Time": "America/Denver",
    "Central America Standard Time": "America/Guatemala",
    "Central Standard Time": "America/Chicago",
    "Easter Island Standard Time": "Pacific/Easter",
    "Central Standard Time (Mexico)": "America/Mexico_City",
    "Canada Central Standard Time": "America/Regina",
    "SA Pacific Standard Time": "America/Bogota",
    "Eastern Standard Time (Mexico)": "America/Cancun",
    "Eastern Standard Time": "America/New_York",
    "Haiti Standard Time": "America/Port-au-Prince",
    "Cuba Standard Time": "America/Havana",
    "US Eastern Standard Time": "America/Indiana/Indianapolis",
    "Turks And Caicos Standard Time": "America/Grand_Turk",
    "Paraguay Standard Time": "America/Asuncion",
    "Atlantic Standard Time": "America/Halifax",
    "Venezuela Standard Time": "America/Caracas",
    "Central Brazilian Standard Time": "America/Cuiaba",
    "SA Western Standard Time": "America/La_Paz",
    "Pacific SA Standard Time": "America/Santiago",
    "Newfoundland Standard Time": "America/St_Johns",
    "Tocantins Standard Time": "America/Araguaina",
    "E. South America Standard Time": "America/Sao_Paulo",
    "SA Eastern Standard Time": "America/Cayenne",
    "Argentina Standard Time": "America/Argentina/Buenos_Aires",
    "Greenland Standard Time": "America/Godthab",
    "Montevideo Standard Time": "America/Montevideo",
    "Magallanes Standard Time": "America/Punta_Arenas",
    "Saint Pierre Standard Time": "America/Miquelon",
    "Bahia Standard Time": "America/Bahia",
    "UTC-02": "Etc/GMT+2",
    "Mid-Atlantic Standard Time": "Etc/GMT+2",
    "Azores Standard Time": "Atlantic/Azores",
    "Cape Verde Standard Time": "Atlantic/Cape_Verde",
    "UTC": "Etc/UTC",
    "GMT Standard Time": "Europe/London",
    "Greenwich Standard Time": "Atlantic/Reykjavik",
    "Sao Tome Standard Time": "Africa/Sao_Tome",
    "Morocco Standard Time": "Africa/Casablanca",
    "W. Europe Standard Time": "Europe/Berlin",
    "Central Europe Standard Time": "Europe/Budapest",
    "Romance Standard Time": "Europe/Paris",
    "Central European Standard Time": "Europe/Warsaw",
    "W. Central Africa Standard Time": "Africa/Lagos",
    "Jordan Standard Time": "Asia/Amman",
    "GTB Standard Time": "Europe/Bucharest",
    "Middle East Standard Time": "Asia/Beirut",
    "Egypt Standard Time": "Africa/Cairo",
    "E. Europe Standard Time": "Europe/Chisinau",
    "Syria Standard Time": "Asia/Damascus",
    "West Bank Standard Time": "Asia/Hebron",
    "South Africa Standard Time": "Africa/Johannesburg",
    "FLE Standard Time": "Europe/Kiev",
    "Israel Standard Time": "Asia/Jerusalem",
    "Kaliningrad Standard Time": "Europe/Kaliningrad",
    "Sudan Standard Time": "Africa/Khartoum",
    "Libya Standard Time": "Africa/Tripoli",
    "Namibia Standard Time": "Africa/Windhoek",
    "Arabic Standard Time": "Asia/Baghdad",
    "Turkey Standard Time": "Europe/Istanbul",
    "Arab Standard Time": "Asia/Riyadh",
    "Belarus Standard Time": "Europe/Minsk",
    "Russian Standard Time": "Europe/Moscow",
    "E. Africa Standard Time": "Africa/Nairobi",
    "Iran Standard Time": "Asia/Tehran",
    "Arabian Standard Time": "Asia/Dubai",
    "Astrakhan Standard Time": "Europe/Astrakhan",
    "Azerbaijan Standard Time": "Asia/Baku",
    "Russia Time Zone 3": "Europe/Samara",
    "Mauritius Standard Time": "Indian/Mauritius",
    "Saratov Standard Time": "Europe/Saratov",
    "Georgian Standard Time": "Asia/Tbilisi",
    "Volgograd Standard Time": "Europe/Volgograd",
    "Caucasus Standard Time": "Asia/Yerevan",
    "Afghanistan Standard Time": "Asia/Kabul",
    "West Asia Standard Time": "Asia/Tashkent",
    "Ekaterinburg Standard Time": "Asia/Yekaterinburg",
    "Pakistan Standard Time": "Asia/Karachi",
    "India Standard Time": "Asia/Kolkata",
    "Sri Lanka Standard Time": "Asia/Colombo",
    "Nepal Standard Time": "Asia/Kathmandu",
    "Central Asia Standard Time": "Asia/Almaty",
    "Bangladesh Standard Time": "Asia/Dhaka",
    "Omsk Standard Time": "Asia/Omsk",
    "Myanmar Standard Time": "Asia/Yangon",
    "SE Asia Standard Time": "Asia/Bangkok",
    "Altai Standard Time": "Asia/Barnaul",
    "W. Mongolia Standard Time": "Asia/Hovd",
    "North Asia Standard Time": "Asia/Krasnoyarsk",
    "N. Central Asia Standard Time": "Asia/Novosibirsk",
    "Tomsk Standard Time": "Asia/Tomsk",
    "China Standard Time": "Asia/Shanghai",
    "North Asia East Standard Time": "Asia/Irkutsk",
    "Singapore Standard Time": "Asia/Singapore",
    "W. Australia Standard Time": "Australia/Perth",
    "Taipei Standard Time": "Asia/Taipei",
    "Ulaanbaatar Standard Time": "Asia/Ulaanbaatar",
    "Aus Central W. Standard Time": "Australia/Eucla",
    "Transbaikal Standard Time": "Asia/Chita",
    "Tokyo Standard Time": "Asia/Tokyo",
    "North Korea Standard Time": "Asia/Pyongyang",
    "Korea Standard Time": "Asia/Seoul",
    "Yakutsk Standard Time": "Asia/Yakutsk",
    "Cen. Australia Standard Time": "Australia/Adelaide",
    "AUS Central Standard Time": "Australia/Darwin",
    "E. Australia Standard Time": "Australia/Brisbane",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "West Pacific Standard Time": "Pacific/Port_Moresby",
    "Tasmania Standard Time": "Australia/Hobart",
    "Vladivostok Standard Time": "Asia/Vladivostok",
    "Lord Howe Standard Time": "Australia/Lord_Howe",
    "Bougainville Standard Time": "Pacific/Bougainville",
    "Russia Time Zone 10": "Asia/Srednekolymsk",
    "Magadan Standard Time": "Asia/Magadan",
    "Norfolk Standard Time": "Pacific/Norfolk",
    "Sakhalin Standard Time": "Asia/Sakhalin",
    "Central Pacific Standard Time": "Pacific/Guadalcanal",
    "Russia Time Zone 11": "Asia/Kamchatka",
    "New Zealand Standard Time": "Pacific/Auckland",
    "UTC+12": "Etc/GMT-12",
    "Fiji Standard Time": "Pacific/Fiji",
    "Kamchatka Standard Time": "Asia/Kamchatka",
    "Chatham Islands Standard Time": "Pacific/Chatham",
    "UTC+13": "Etc/GMT-13",
    "Tonga Standard Time": "Pacific/Tongatapu",
    "Samoa Standard Time": "Pacific/Apia",
    "Line Islands Standard Time": "Pacific/Kiritimati",
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

# Apple-style agenda fill: when the current day is sparse, keep pulling in
# upcoming days (up to MAX_LOOKAHEAD_DAYS ahead) until we have at least
# MIN_AGENDA_EVENTS to show.
MIN_AGENDA_EVENTS = 3
MAX_LOOKAHEAD_DAYS = 7


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def configured_url(config: dict) -> str:
    url = str(config.get("ics_url", "")).strip()
    if url in PLACEHOLDER_URLS:
        return ""
    # Normalize at read time too, so a hand-edited config.json with a
    # webcal:// or .html link works the same as one saved through the UI.
    return normalize_ics_url(url)


def normalize_ics_url(url: str) -> str:
    """Accept whatever the user pasted and coerce it into a fetchable ICS URL.

    Handles webcal:// links, the published calendar's HTML variant, and stray
    quotes/whitespace, so users don't need to know what an "ICS link" is.
    """
    url = url.strip().strip("\"'").strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    if url.lower().endswith("calendar.html"):
        url = url[: -len("calendar.html")] + "calendar.ics"
    return url


def resolve_zone(tzid: str | None, default_zone: ZoneInfo) -> ZoneInfo:
    """Turn an ICS TZID into a ZoneInfo, tolerating Windows names and junk.

    Falls back to the configured zone for anything we can't resolve, so one
    unknown timezone on a single event never crashes the whole feed.
    """
    if not tzid:
        return default_zone
    name = WINDOWS_TZ.get(tzid, tzid)
    try:
        return ZoneInfo(name)
    except Exception:
        return default_zone


def get_zone(config: dict) -> ZoneInfo:
    tz = config.get("timezone") or "America/New_York"
    return resolve_zone(tz, ZoneInfo("UTC"))


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


# Single-slot TTL cache so the dashboard's 1-minute poll doesn't hammer the
# feed host with a fresh download on every request. validate_ics bypasses it
# deliberately — a user testing a pasted link should get a live answer.
ICS_CACHE_TTL_SECONDS = 55
_ics_cache: dict = {"url": None, "fetched_at": 0.0, "raw": ""}


def fetch_ics_cached(ics_url: str) -> str:
    now = time_module.monotonic()
    if _ics_cache["url"] == ics_url and now - _ics_cache["fetched_at"] < ICS_CACHE_TTL_SECONDS:
        return _ics_cache["raw"]
    raw = fetch_ics(ics_url)
    _ics_cache.update(url=ics_url, fetched_at=now, raw=raw)
    return raw


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

    event_zone = resolve_zone(params.get("TZID"), default_zone)

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


def events_for_day(parsed_events: list[dict], day: date, zone: ZoneInfo) -> list[dict]:
    items: list[dict] = []
    for event in parsed_events:
        items.extend(expand_event_for_day(event, day, zone))
    items.sort(key=lambda e: e["start"])
    for item in items:
        item["date"] = day.isoformat()
    return items


def today_events(config: dict) -> dict:
    zone = get_zone(config)
    ics_url = configured_url(config)
    # "today" is computed in the configured timezone and sent to the client,
    # so day labels and countdowns don't depend on the browser's OS clock.
    base_day = datetime.now(zone).date()
    if not ics_url:
        return {
            "status": "sample mode",
            "configured": False,
            "message": "Connect your Outlook calendar to replace this sample data.",
            "today": base_day.isoformat(),
            "events": sample_events(zone),
        }

    raw_ics = fetch_ics_cached(ics_url)
    parsed_events = parse_ics(raw_ics)
    now = datetime.now(zone)

    def upcoming_count(items: list[dict]) -> int:
        return sum(1 for e in items if datetime.fromisoformat(e["end"]) > now)

    # Fill the agenda until there are enough *upcoming* events to show. Counting
    # upcoming (not total) means a day full of finished meetings still rolls the
    # view forward into tomorrow, matching the "hide past events" behavior.
    events = events_for_day(parsed_events, base_day, zone)
    offset = 1
    while upcoming_count(events) < MIN_AGENDA_EVENTS and offset <= MAX_LOOKAHEAD_DAYS:
        events.extend(events_for_day(parsed_events, base_day + timedelta(days=offset), zone))
        offset += 1

    return {
        "status": "live ICS",
        "configured": True,
        "message": "",
        "today": base_day.isoformat(),
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
            "date": today.isoformat(),
        }

    return [
        item("Work / Internship", 7, 0, 16, 0, "Liverpool, NY"),
        item("Lunch + HDLBits", 12, 0, 13, 0),
        item("Research meeting", 21, 0, 21, 30, "Teams", "https://teams.microsoft.com/"),
    ]


# Settings the dashboard's edit panel is allowed to change.
EDITABLE_CONFIG_KEYS = {"ics_url", "display_city", "weather", "background"}


def public_config(config: dict) -> dict:
    return {
        "ics_url": configured_url(config),
        "display_city": config.get("display_city", DEFAULT_CONFIG["display_city"]),
        "weather": config.get("weather", DEFAULT_CONFIG["weather"]),
        "background": config.get("background", ""),
    }


def save_config(updates: dict) -> dict:
    config = load_config()
    for key in EDITABLE_CONFIG_KEYS & updates.keys():
        config[key] = updates[key]
    if "ics_url" in updates:
        config["ics_url"] = normalize_ics_url(str(updates["ics_url"]))
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    return config


def validate_ics(url: str) -> dict:
    """Try a pasted link and report back in plain English."""
    normalized = normalize_ics_url(url)
    if not normalized:
        return {"ok": False, "message": "Paste the link Outlook gave you."}
    if not normalized.lower().startswith(("https://", "http://")):
        return {"ok": False, "message": "That doesn't look like a web link. It should start with https:// or webcal://."}

    try:
        raw = fetch_ics(normalized)
    except Exception:
        return {"ok": False, "message": "Couldn't reach that link. Double-check you copied the whole ICS link from Outlook."}

    if "BEGIN:VCALENDAR" not in raw:
        return {"ok": False, "message": "That link doesn't point to a calendar. In Outlook, copy the ICS link (not the HTML one)."}

    config = load_config()
    zone = get_zone(config)
    parsed = parse_ics(raw)
    today = datetime.now(zone).date()
    upcoming = sum(
        len(expand_event_for_day(event, today + timedelta(days=offset), zone))
        for event in parsed
        for offset in range(7)
    )
    return {"ok": True, "url": normalized, "total": len(parsed), "upcoming": upcoming}


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/events":
            self.handle_events()
            return
        if parsed.path == "/api/config":
            self.send_json(public_config(load_config()))
            return
        if parsed.path in {"/", "/index.html"}:
            self.serve_file(ROOT / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/config", "/api/validate-ics"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object.")
            if parsed.path == "/api/validate-ics":
                self.send_json(validate_ics(str(body.get("url", ""))))
            else:
                config = save_config(body)
                self.send_json(public_config(config))
        except Exception as error:
            self.send_json({"message": str(error)}, status=HTTPStatus.BAD_REQUEST)

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
