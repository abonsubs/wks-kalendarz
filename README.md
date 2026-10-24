# Samoaktualizujący się kalendarz WKS Śląsk Wrocław (PGE PLK)

Ten projekt generuje plik kalendarza `.ics` z terminarzem WKS Śląsk Wrocław na
podstawie danych z [plk.pl](https://plk.pl/terminarz) i **sam go aktualizuje**
przez GitHub Actions. Po jednorazowym podpięciu w Google Calendar zmiany w
terminarzu (przełożone mecze, zmiany godzin) pojawiają się automatycznie.

## Jak to działa

1. `generate_ics.py` pobiera terminarz z plk.pl, wyłapuje mecze Śląska i zapisuje
   plik `wks-slask-wroclaw.ics`.
2. GitHub Actions (`.github/workflows/update-calendar.yml`) uruchamia skrypt
   **codziennie** i — jeśli coś się zmieniło — commituje nową wersję pliku.
3. Google Calendar subskrybuje stały adres URL tego pliku i odświeża go sam.

> **Import ≠ subskrypcja.** Zaimportowanie pliku `.ics` to jednorazowa kopia,
> która się nie aktualizuje. Żeby kalendarz żył, trzeba go **zasubskrybować przez
> adres URL** (patrz krok 3 poniżej).

## Konfiguracja (jednorazowo)

### 1. Utwórz publiczne repozytorium na GitHub

Wrzuć do niego wszystkie pliki z tego folderu:

```
generate_ics.py
wks-slask-wroclaw.ics
.github/workflows/update-calendar.yml
README.md
```

Najprościej z terminala (będąc w tym folderze):

```bash
git init
git add .
git commit -m "Kalendarz WKS Śląsk Wrocław"
git branch -M main
git remote add origin https://github.com/TWOJA_NAZWA/wks-kalendarz.git
git push -u origin main
```

(Repozytorium `wks-kalendarz` utwórz wcześniej na github.com. Musi być **publiczne**,
żeby Google mógł pobierać plik bez logowania.)

### 2. Włącz zapis dla GitHub Actions

W repozytorium: **Settings → Actions → General → Workflow permissions** →
zaznacz **„Read and write permissions"** → **Save**.

Dzięki temu workflow może commitować zaktualizowany plik. Możesz go odpalić od razu
ręcznie: zakładka **Actions → „Aktualizacja kalendarza WKS Śląsk" → Run workflow**.

### 3. Podepnij kalendarz w Google Calendar

Adres Twojego pliku (podmień `TWOJA_NAZWA`):

```
https://raw.githubusercontent.com/TWOJA_NAZWA/wks-kalendarz/main/wks-slask-wroclaw.ics
```

W [Google Calendar](https://calendar.google.com) (wersja na komputerze):

1. Po lewej, przy **„Inne kalendarze"**, kliknij **+**.
2. Wybierz **„Z adresu URL"**.
3. Wklej adres powyżej i kliknij **„Dodaj kalendarz"**.

Gotowe. Mecze pojawią się w kalendarzu, a Google będzie sam odświeżał plik.

## Ważne uwagi

- **Opóźnienie odświeżania:** Google odświeża subskrybowane kalendarze z własnym
  rytmem — zwykle co kilka–kilkanaście godzin, czasem do doby. To nie jest
  aktualizacja „na żywo", ale do terminarza rozgrywek w zupełności wystarcza.
- **Godziny meczów** są brane z pola `date` z plk.pl (czas UTC) i same przeliczają
  się na Twoją strefę w kalendarzu. Każdy mecz trwa domyślnie 2 godziny.
- **Inna drużyna / inne ustawienia:** skrypt przyjmuje zmienne środowiskowe —
  `TEAM` (fragment nazwy drużyny), `OUTPUT`, `CALNAME`, `DURATION_H`, `SOURCE_URL`.
  Np. `TEAM="Zastal" OUTPUT=zastal.ics python generate_ics.py`.
- **Jeśli plk.pl zmieni format strony**, skrypt nie znajdzie meczów, zgłosi błąd i
  **nie nadpisze** istniejącego pliku (workflow w Actions pokaże się wtedy jako
  nieudany). Trzeba będzie zaktualizować wzorzec w `generate_ics.py`.

## Uruchomienie lokalne

```bash
python3 generate_ics.py
```

Nie wymaga żadnych zewnętrznych bibliotek — tylko Pythona 3.
