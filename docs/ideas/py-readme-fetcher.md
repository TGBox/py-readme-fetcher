# py-readme-fetcher: Konzept & Architektur-Spezifikation

## Problem Statement

Wie können wir eine intuitive, responsive Desktop-Anwendung schaffen, mit der Entwickler und Projektleiter README-Dokumentationen aus beliebig tief verschachtelten GitLab-Gruppen mühelos entdecken, filtern, in einer integrierten Vorschau lesen und strukturiert herunterladen können?

## Recommended Direction

Eine moderne PySide6 Desktop-Anwendung mit sauberer Trennung zwischen Geschäftslogik (GitLab API Client / Fetcher Service) und Benutzeroberfläche:

- **Zwei-Stufen-Workflow:**
  1. *Schritt 1 (Scannen):* Abfrage aller Projekte der GitLab-Gruppe inklusive Untergruppen (`include_subgroups=true`, Paginierung). Auflistung in einer interaktiven Tabelle mit Such- und Filterfeld, Statusanzeige (z. B. README vorhanden, Standardbranch) sowie Checkboxen für die Projektauswahl.
  2. *Schritt 2 (Herunterladen):* Asynchrones Herunterladen der ausgewählten Projekt-READMEs in einen frei wählbaren Zielordner mit Live-Fortschrittsbalken und Log-Ausgabe.
- **Integrierte Markdown-Vorschau:**
  - Split-View / Detailansicht: Beim Anklicken eines Projekts in der Tabelle kann dessen README direkt im integrierten Rich-Text-Viewer gelesen werden (gerendertes Markdown).
- **Flache Dateiablage:**
  - Speicherung der Dateien nach dem bewährten Schema `{safe_name}_README.md` (z. B. `group_subgroup_project_README.md`), um Namenskollisionen zu verhindern und einfache Weiterverarbeitung zu garantieren.
- **Smarte Dateierkennung:**
  - Berücksichtigung von `readme_url` der GitLab API sowie Fallback auf gängige Schreibweisen (`README.md`, `readme.md`, `README.markdown`, `README.rst`).
- **Benutzerkomfort & Konventionen (Qt / PySide6):**
  - Asynchrone Abarbeitung via `QThread` und Signale (UI bleibt jederzeit 100% flüssig, Abbruch jederzeit möglich).
  - Persistente Speicherung von GitLab-URL, Gruppen-ID, Zielordner, Fenstergeometrie und optional Access-Token via `QSettings`.
  - Vollbild-Toggle (F11) sowie modernes Theme mit Dark- und Light-Mode Umschaltung.
  - Deutsche UI-Texte, englischer Code und Tests.

## Key Assumptions to Validate

- [x] GitLab REST API v4 unterstützt `include_subgroups=true` und liefert Projekt-Metadaten inkl. Default-Branch und `readme_url`.
- [x] PySide6 `QTextBrowser` bzw. `QTextDocument.setMarkdown()` rendert Markdown inklusive Überschriften, Code-Blöcken, Listen und Tabellen nativ ohne externe WebEngine-Abhängigkeit.
- [x] Netzwerk-Aufrufe mit `requests` (oder `httpx`) lassen sich in einem `QThread` sauber über `isInterruptionRequested()` abbrechen.

## MVP Scope

1. **GitLab Client & Worker:**
   - Robuster API-Client für Gruppen-Projekte (mit Paginierung) und Raw-File-Download.
   - Fallback-Mechanismus für README-Dateinamen.
   - Asynchroner Qt-Worker (`QThread`) mit Fortschrittssignalen (`started`, `progress`, `finished`, `error`, `project_discovered`).
2. **GUI (PySide6):**
   - Konfigurationsbereich: GitLab URL, Token (Passwortfeld mit Sichtbarkeits-Toggle), Gruppen-ID/Pfad, Zielordner-Auswahl (via `QFileDialog`), "Token speichern"-Checkbox.
   - Hauptbereich (Split-View):
     - Links: Tabelle der gescannten Repositories mit Spalten (Auswahl, Projektpfad, Branch, README-Status), Such-/Filterleiste, "Alle auswählen / Keine auswählen"-Buttons.
     - Rechts: Markdown-Vorschau (`QTextBrowser`) für das aktuell markierte Repository.
   - Aktions- & Statusleiste:
     - Buttons "Projekte scannen", "Ausgewählte herunterladen", "Abbrechen", "Zielordner öffnen".
     - Fortschrittsbalken und detaillierte Statusanzeige / Log.
3. **Themes & Fenstersteuerung:**
   - Dark Mode und Light Mode Umschaltung.
   - F11 Vollbild-Umschaltung.
   - Fenstergröße, Position und Formulareinstellungen persistent via `QSettings`.
4. **Testabdeckung & Code-Qualität:**
   - Unit- und Integrationstests für GitLab Client, Namensbereinigung, Fehlerbehandlung und Qt-Signals via `pytest` / `pytest-qt`.
   - Linter- und Formatierungs-Konformität via `ruff`.

## Not Doing (and Why)

- **GitLab GraphQL API:** REST API v4 reicht vollkommen aus und ist stabiler und einfacher zu warten.
- **Git Clone / Git LFS:** Das Klonen ganzer Repositories wäre extrem bandbreiten- und zeitintensiv. Der Download der Raw-Datei über die Repository Files API ist blitzschnell.
- **Hierarchische Verzeichnis-Verschachtelung:** Nutzer hat sich für flache Namensgebung mit Namespace-Präfix entschieden, was die Dateiablage einfach und kollisionsfrei hält.
- **PySide6 WebEngine für Markdown:** Zu schwerfällig (mehrere hundert MB zusätzliche Binaries). Wir nutzen PySide6's natives Markdown-Rendering in `QTextBrowser`.
- **System-Keyring:** Benutzer bevorzugt komfortable Speicherung via `QSettings` mit optionaler Checkbox.

## Open Questions & Verification

- Alle Kernfragen wurden über `/grill-me` geklärt.
