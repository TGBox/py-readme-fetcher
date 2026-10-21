# py-readme-fetcher

Eine moderne Python Desktop-Anwendung (PySide6 / Qt 6) zum Durchsuchen, Vorab-Prüfen und Herunterladen aller `README.md`-Dateien aus einer GitLab-Gruppe inklusive aller Untergruppen.

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![GUI Framework](https://img.shields.io/badge/GUI-PySide6-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## ✨ Features

- **Zwei-Stufen-Workflow:**
  1. *Scannen:* Ruft alle Projekte einer Gruppe (inkl. aller Untergruppen und Paginierung) über die GitLab REST API v4 ab.
  2. *Auswahl & Filter:* Interaktive Tabelle mit Suchleiste (Echtzeitfilter nach Pfad oder Name) und Schnellauswahl-Buttons.
  3. *Herunterladen:* Asynchroner Download der gewählten README-Dateien mit Fortschrittsanzeige und Abbruch-Option.
- **Integrierte Markdown-Vorschau:**
  - Klicke auf ein beliebiges Projekt, um dessen README direkt in der Anwendung gerendert zu lesen (über nativen Rich-Text-Viewer).
  - Direktes Öffnen des Projekts im Browser per Knopfdruck.
- **Smarte Dateierkennung & Unterordner-Suche:**
  - Erkennt `README.md`, `readme.md`, `README.markdown`, `README.rst`, `README.txt` sowie in GitLab hinterlegte Standard-READMEs.
  - **Rekursive Suche in Unterordnern:** Findet README-Dateien auch dann, wenn sie nicht im Root-Verzeichnis liegen (z. B. `data-chat/client/README.md`).
  - **Multi-README-Vorschau:** Enthält ein Repository mehrere Dokumentationsdateien, kann in der Vorschau über ein Dropdown-Menü direkt zwischen ihnen gewechselt werden.
  - **Intelligente Ordner-Filterung:** Abhängigkeits- und Build-Ordner wie `node_modules`, `vendor`, `.git`, `.venv`, `dist` oder `build` werden automatisch ignoriert.
- **Hierarchische & kollisionsfreie Dateiablage:**
  - Speichert heruntergeladene Dateien in projektbezogenen Verzeichnissen mit Spiegelung der Repository-Unterpfade: `{zielordner}/{gruppe_projekt}/{relativer_pfad}`.
  - Ermöglicht den Download der primären README (mit automatischem Fallback auf Unterordner) oder optional aller gefundenen README-Dateien eines Projekts.
- **Benutzerkomfort & Ergonomie:**
  - **Dark- & Light-Themes:** Hochkontrastierende, moderne Themes umschaltbar per Klick.
  - **Vollbildmodus:** Nahtloser Wechsel zwischen Fenster- und Vollbildansicht (Taste **F11**).
  - **Persistenz (`QSettings`):** GitLab-URL, Gruppen-ID, Zielordner, Such- und Download-Optionen, Fenstergröße/-position und optional das Token werden sitzungsübergreifend gespeichert.
  - **Thread-Sicherheit:** Alle Netzwerkanfragen laufen in dedizierten `QThread`-Workern; die Benutzeroberfläche bleibt jederzeit 100% flüssig.

---

## 🚀 Voraussetzungen & Installation

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (empfohlen für schnelles Paketmanagement)

Abhängigkeiten synchronisieren:

```bash
uv sync
```

---

## 💻 Ausführung

### GUI starten

```bash
uv run py-readme-fetcher
# oder:
uv run main
```

### Tests ausführen

```bash
uv run pytest
```

### Code formatieren & linter ausführen

```bash
uv run ruff format .
uv run ruff check .
```

### Standalone-Executable bauen (PyInstaller)

```bash
uv run build
```

---

## 📁 Projektstruktur

```text
py-readme-fetcher/
├── docs/
│   └── ideas/
│       └── py-readme-fetcher.md      # Architektur- & Konzeptspezifikation
├── src/
│   ├── gitlab/
│   │   ├── __init__.py
│   │   └── client.py                 # GitLab REST API Client & Datenmodelle
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py            # Hauptfenster mit Split-View & Tabellensteuerung
│   │   └── theme.py                  # Stylesheets für Dark- und Light-Themes
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── download_worker.py        # Asynchroner README-Downloader (QThread)
│   │   ├── preview_worker.py         # Asynchroner README-Vorschau-Worker (QThread)
│   │   └── scan_worker.py            # Asynchroner Gruppen-Scanner (QThread)
│   ├── build.py                      # PyInstaller Build-Skript
│   ├── main.py                       # Anwendungsstartpunkt
│   └── tools.py                      # Hilfsskripte (Format & Lint)
├── tests/
│   ├── test_gitlab_client.py         # Unit-Tests für API-Client & Dateinamen
│   ├── test_main.py                  # Entrypoint-Tests
│   ├── test_ui.py                    # GUI- & Interaktionstests mit pytest-qt
│   └── test_workers.py               # Worker- & Signal-Tests mit pytest-qt
├── pyproject.toml
└── README.md
```
