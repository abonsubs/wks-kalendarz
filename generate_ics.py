#!/usr/bin/env python3
"""Generuje plik .ics z terminarzem wybranej drużyny na podstawie danych z plk.pl.

Skrypt pobiera stronę terminarza PGE PLK (https://plk.pl/terminarz), wyciąga z niej
dane meczów (wbudowane w stronę jako JSON) i zapisuje kalendarz w formacie iCalendar.

Nie wymaga żadnych zewnętrznych bibliotek — korzysta wyłącznie z biblioteki
standardowej Pythona, dzięki czemu działa w GitHub Actions bez instalacji zależności.

Konfiguracja przez zmienne środowiskowe (wszystkie opcjonalne):
    TEAM        — fragment nazwy drużyny do filtrowania (domyślnie "Śląsk Wrocław")
    OUTPUT      — ścieżka pliku wyjściowego (domyślnie "wks-slask-wroclaw.ics")
    CALNAME     — nazwa kalendarza widoczna w aplikacji
    SOURCE_URL  — adres strony terminarza (domyślnie https://plk.pl/terminarz)
    DURATION_H  — długość wydarzenia w godzinach (domyślnie 2)
"""

import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

SOURCE_URL = os.environ.get("SOURCE_URL", "https://plk.pl/terminarz")
TEAM = os.environ.get("TEAM", "Śląsk Wrocław")
OUTPUT = os.environ.get("OUTPUT", "wks-slask-wroclaw.ics")
CALNAME = os.environ.get("CALNAME", "WKS Śląsk Wrocław — PGE PLK")
DURATION_H = float(os.environ.get("DURATION_H", "2"))

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

# Dane meczów są osadzone w stronie jako JSON (payload Next.js). Każdy mecz to
# obiekt z polami w stałej kolejności — wyciągamy je jednym, zakotwiczonym wyrażeniem.
GAME_RE = re.compile(
    r'\{"id":"(?P<id>\d{5,7})","seasonId":"\d+",'
    r'"league":\{"id":\d+,"name":"(?P<league>[^"]*)","shortName":"[^"]*"\},'
    r'"round":\{"id":\d+,"name":"(?P<round>[^"]*)","shortName":"[^"]*"\},'
    r'"queue":\{"id":\d+,"name":"(?P<queue>[^"]*)"\},'
    r'"gameNo":"[^"]*","slug":"(?P<slug>[^"]*)",'
    r'"homeTeamName":"(?P<home>[^"]*)","guestTeamName":"(?P<guest>[^"]*)",'
    r'"isFinished":(?:true|false),"date":"(?P<date>[^"]*)"'
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_games(html):
    # W payloadzie cudzysłowy są poprzedzone backslashem (\") — rozkodowujemy je.
    text = html.replace('\\"', '"')
    games = {}
    for m in GAME_RE.finditer(text):
        g = m.groupdict()
        games[g["id"]] = g  # dedup po ID meczu
    return list(games.values())


def parse_utc(iso):
    # Format: 2026-10-24T17:30:00.000Z
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def ics_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")


def fold(line):
    """Zawija linie dłuższe niż 75 oktetów zgodnie z RFC 5545.

    Cięcie odbywa się na granicy znaków (nie bajtów), żeby nie rozdzielić
    wielobajtowych znaków UTF-8 (np. ó, ł, ś).
    """
    if len(line.encode("utf-8")) <= 75:
        return line
    segments = []
    cur = ""
    cur_bytes = 0
    limit = 75  # pierwsza linia; kolejne mają 74 (wiodąca spacja zajmuje 1 oktet)
    for ch in line:
        clen = len(ch.encode("utf-8"))
        if cur_bytes + clen > limit:
            segments.append(cur)
            cur = ch
            cur_bytes = clen
            limit = 74
        else:
            cur += ch
            cur_bytes += clen
    segments.append(cur)
    return ("\r\n ").join(segments)


def esc(text):
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_ics(games):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "PRODID:-//wks-kalendarz//plk//PL",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(CALNAME)}",
    ]
    for g in sorted(games, key=lambda x: x["date"]):
        start = parse_utc(g["date"])
        end = start + timedelta(hours=DURATION_H)
        summary = f"{g['home']} vs {g['guest']}"
        url = f"https://plk.pl/mecz/{g['id']}/{g['slug']}"
        desc = (
            f"Liga: {g['league']}\n"
            f"Runda: {g['round']}\n"
            f"Kolejka: {g['queue']}\n"
            f"Szczegóły meczu: {url}"
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{g['id']}@new-plk",
            # DTSTAMP deterministyczny (= data meczu), żeby plik zmieniał się tylko
            # wtedy, gdy realnie zmienią się szczegóły meczu.
            f"DTSTAMP:{ics_dt(start)}",
            f"DTSTART:{ics_dt(start)}",
            f"DTEND:{ics_dt(end)}",
            f"SUMMARY:{esc(summary)}",
            f"LOCATION:{esc(g['home'])}",
            f"DESCRIPTION:{esc(desc)}",
            f"URL:{url}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(ln) for ln in lines) + "\r\n"


def main():
    print(f"Pobieram: {SOURCE_URL}")
    html = fetch(SOURCE_URL)
    games = extract_games(html)
    print(f"Znaleziono meczów w terminarzu: {len(games)}")

    team = [g for g in games if TEAM in g["home"] or TEAM in g["guest"]]
    print(f"Meczów drużyny '{TEAM}': {len(team)}")

    if not team:
        print(
            "BŁĄD: nie znaleziono żadnego meczu. Strona źródłowa mogła zmienić "
            "format danych. Nie nadpisuję pliku wyjściowego.",
            file=sys.stderr,
        )
        return 1

    ics = build_ics(team)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print(f"Zapisano {len(team)} meczów do: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
