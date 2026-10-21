"""Main application window for py-readme-fetcher."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QPoint, QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.gitlab.client import GitLabClient, GitLabProject
from src.ui.theme import apply_theme
from src.workers.download_worker import DownloadWorker
from src.workers.preview_worker import PreviewWorker
from src.workers.scan_worker import ProjectBranchWorker, ScanWorker


class MainWindow(QMainWindow):
    """Primary GUI window managing user input, worker lifecycle, and display."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py-readme-fetcher — GitLab README Downloader")
        self.resize(1150, 780)

        self.settings = QSettings("py-readme-fetcher", "py-readme-fetcher")
        self.dark_mode: bool = True
        self.projects: list[GitLabProject] = []
        self.active_worker: ScanWorker | DownloadWorker | None = None
        self.preview_worker: PreviewWorker | None = None
        self._branch_workers: list[ProjectBranchWorker] = []

        self._setup_ui()
        self._setup_shortcuts()
        self._load_settings()
        self._apply_current_theme()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top bar: Title & Theme Toggle
        top_bar = QHBoxLayout()
        title_label = QLabel("<h2>🦊 py-readme-fetcher</h2>")
        title_label.setTextFormat(Qt.TextFormat.RichText)
        top_bar.addWidget(title_label)
        top_bar.addStretch()

        self.fullscreen_btn = QPushButton("⛶ Vollbild (F11)")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        top_bar.addWidget(self.fullscreen_btn)

        self.theme_btn = QPushButton("🌙 Dunkel")
        self.theme_btn.clicked.connect(self._toggle_theme)
        top_bar.addWidget(self.theme_btn)

        main_layout.addLayout(top_bar)

        # 2. Configuration GroupBox
        config_group = QGroupBox("GitLab Konfiguration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(8)

        # Row 1: URL and Token
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("GitLab URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://gitlab.com oder eigene Instanz-URL")
        row1.addWidget(self.url_input, stretch=2)

        row1.addWidget(QLabel("Access Token:"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("GitLab Access Token (read_api)")
        row1.addWidget(self.token_input, stretch=2)

        self.toggle_token_btn = QPushButton("👁️")
        self.toggle_token_btn.setToolTip("Token anzeigen/verbergen")
        self.toggle_token_btn.setFixedWidth(40)
        self.toggle_token_btn.clicked.connect(self._toggle_token_visibility)
        row1.addWidget(self.toggle_token_btn)

        self.save_token_cb = QCheckBox("Token speichern")
        self.save_token_cb.setToolTip(
            "Speichert das Token verschlüsselt in den Anwendungseinstellungen"
        )
        row1.addWidget(self.save_token_cb)

        self.ssl_verify_cb = QCheckBox("SSL prüfen")
        self.ssl_verify_cb.setChecked(True)
        self.ssl_verify_cb.setToolTip(
            "SSL-Zertifikate verifizieren. Deaktivieren bei internen Firmen-Servern mit selbstsignierten Zertifikaten."
        )
        row1.addWidget(self.ssl_verify_cb)

        config_layout.addLayout(row1)

        # Row 2: Group ID, Subgroups and Output Dir
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Gruppen-ID / Pfad:"))
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("z. B. 12345678 oder mein-team/untergruppe")
        row2.addWidget(self.group_input, stretch=2)

        self.subgroups_cb = QCheckBox("Untergruppen einbeziehen")
        self.subgroups_cb.setChecked(True)
        row2.addWidget(self.subgroups_cb)

        row2.addWidget(QLabel("Zielordner:"))
        self.output_dir_input = QLineEdit()
        default_output = str(Path.cwd() / "readmes")
        self.output_dir_input.setText(default_output)
        row2.addWidget(self.output_dir_input, stretch=2)

        browse_btn = QPushButton("Durchsuchen...")
        browse_btn.clicked.connect(self._browse_output_dir)
        row2.addWidget(browse_btn)

        config_layout.addLayout(row2)

        # Row 3: Subfolder and Download Mode Options
        row3 = QHBoxLayout()
        self.search_subfolders_cb = QCheckBox("In Unterordnern nach READMEs suchen")
        self.search_subfolders_cb.setChecked(True)
        self.search_subfolders_cb.setToolTip(
            "Durchsucht Repositories rekursiv bis max. 5 Unterordner nach README-Dateien (z. B. data-chat/web/README.md)."
        )
        row3.addWidget(self.search_subfolders_cb)

        self.download_all_cb = QCheckBox("Alle READMEs rekursiv laden")
        self.download_all_cb.setChecked(False)
        self.download_all_cb.setToolTip(
            "Lädt alle gefundenen READMEs eines Projekts herunter statt nur der Haupt-README (mit automatischem Fallback)."
        )
        row3.addWidget(self.download_all_cb)

        row3.addSpacing(16)
        row3.addWidget(QLabel("Branch-Override:"))
        self.branch_override_input = QLineEdit()
        self.branch_override_input.setPlaceholderText(
            "Optional: z. B. develop (Standard: Repo-Branch)"
        )
        self.branch_override_input.setToolTip(
            "Optionaler Branch für alle Projekte. Wenn leer, wird der Standard-Branch des jeweiligen Repositories verwendet."
        )
        row3.addWidget(self.branch_override_input, stretch=1)

        config_layout.addLayout(row3)
        main_layout.addWidget(config_group)

        # 3. Action Buttons Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.scan_btn = QPushButton("🔍 1. Projekte scannen")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.clicked.connect(self._start_scanning)
        action_bar.addWidget(self.scan_btn)

        self.download_btn = QPushButton("⬇️ 2. Ausgewählte herunterladen")
        self.download_btn.setObjectName("successButton")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._start_downloading)
        action_bar.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("⏹️ Abbrechen")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_active_worker)
        action_bar.addWidget(self.cancel_btn)

        action_bar.addStretch()

        self.open_dir_btn = QPushButton("📁 Zielordner öffnen")
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        action_bar.addWidget(self.open_dir_btn)

        main_layout.addLayout(action_bar)

        # 4. Central Splitter: Left (Project Table) & Right (Markdown Preview)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Container
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Filter and selection bar
        filter_bar = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("🔎 Projekte filtern (z. B. nach Name oder Pfad)...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.filter_input)

        select_all_btn = QPushButton("Alle")
        select_all_btn.setToolTip("Alle sichtbaren Projekte auswählen")
        select_all_btn.clicked.connect(lambda: self._set_all_selected(True))
        filter_bar.addWidget(select_all_btn)

        select_none_btn = QPushButton("Keine")
        select_none_btn.setToolTip("Auswahl aufheben")
        select_none_btn.clicked.connect(lambda: self._set_all_selected(False))
        filter_bar.addWidget(select_none_btn)

        left_layout.addLayout(filter_bar)

        # Project Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                "Auswahl",
                "Projektpfad",
                "Branch",
                "Status",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemChanged.connect(self._on_table_item_changed)
        left_layout.addWidget(self.table)

        self.table_count_label = QLabel("Keine Projekte geladen.")
        left_layout.addWidget(self.table_count_label)
        splitter.addWidget(left_widget)

        # Right Container: Markdown Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_header = QHBoxLayout()
        self.preview_title = QLabel("<b>README Vorschau</b>")
        self.preview_title.setTextFormat(Qt.TextFormat.RichText)
        preview_header.addWidget(self.preview_title)
        preview_header.addStretch()

        self.branch_label = QLabel("Branch:")
        self.branch_label.setVisible(False)
        preview_header.addWidget(self.branch_label)

        self.branch_input = QLineEdit()
        self.branch_input.setFixedWidth(110)
        self.branch_input.setPlaceholderText("Branch...")
        self.branch_input.setToolTip("Branch für dieses Projekt anpassen (Enter drücken)")
        self.branch_input.returnPressed.connect(self._on_preview_branch_applied)
        self.branch_input.setVisible(False)
        preview_header.addWidget(self.branch_input)

        self.branch_reload_btn = QPushButton("🔄")
        self.branch_reload_btn.setToolTip("READMEs für diesen Branch neu abrufen")
        self.branch_reload_btn.setFixedWidth(32)
        self.branch_reload_btn.clicked.connect(self._on_preview_branch_applied)
        self.branch_reload_btn.setVisible(False)
        preview_header.addWidget(self.branch_reload_btn)

        self.readme_selector_label = QLabel("Datei:")
        self.readme_selector_label.setVisible(False)
        preview_header.addWidget(self.readme_selector_label)

        self.readme_selector = QComboBox()
        self.readme_selector.setVisible(False)
        self.readme_selector.setToolTip("README-Datei auswählen")
        self.readme_selector.currentIndexChanged.connect(self._on_readme_selector_changed)
        preview_header.addWidget(self.readme_selector)

        self.open_web_btn = QPushButton("🌐 In GitLab öffnen")
        self.open_web_btn.setEnabled(False)
        self.open_web_btn.clicked.connect(self._open_project_in_browser)
        preview_header.addWidget(self.open_web_btn)

        right_layout.addLayout(preview_header)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setPlaceholderText(
            "Wähle ein Projekt in der Tabelle aus, um dessen README hier vorab anzuzeigen."
        )
        right_layout.addWidget(self.preview_browser)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, stretch=1)

        # 5. Bottom Progress and Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel(
            "Bereit. Gib GitLab URL und Gruppe ein und klicke auf 'Projekte scannen'."
        )
        self.statusBar().addWidget(self.status_label, 1)

    def _setup_shortcuts(self) -> None:
        shortcut_f11 = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        shortcut_f11.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("⛶ Vollbild (F11)")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("🗗 Fenstermodus (F11)")

    def _toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self._apply_current_theme()

    def _apply_current_theme(self) -> None:
        apply_theme(self, dark_mode=self.dark_mode)
        self.theme_btn.setText("🌙 Dunkel" if self.dark_mode else "☀️ Hell")

    def _toggle_token_visibility(self) -> None:
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_token_btn.setText("🔒")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_token_btn.setText("👁️")

    def _browse_output_dir(self) -> None:
        current_dir = self.output_dir_input.text().strip() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Zielordner für READMEs auswählen",
            current_dir,
        )
        if selected:
            self.output_dir_input.setText(selected)

    def _open_output_dir(self) -> None:
        path = Path(self.output_dir_input.text().strip()).resolve()
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_project_in_browser(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.projects):
            project = self.projects[row]
            if project.web_url:
                QDesktopServices.openUrl(QUrl(project.web_url))

    def _load_settings(self) -> None:
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)

        if self.settings.value("is_maximized", False, type=bool):
            self.showMaximized()

        self.dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.url_input.setText(self.settings.value("gitlab_url", "https://gitlab.com", type=str))
        self.group_input.setText(self.settings.value("group_id", "", type=str))
        self.subgroups_cb.setChecked(self.settings.value("include_subgroups", True, type=bool))

        saved_dir = self.settings.value("output_dir", "", type=str)
        if saved_dir:
            self.output_dir_input.setText(saved_dir)

        save_token = self.settings.value("save_token", False, type=bool)
        self.save_token_cb.setChecked(save_token)
        if save_token:
            self.token_input.setText(self.settings.value("private_token", "", type=str))

        self.ssl_verify_cb.setChecked(self.settings.value("verify_ssl", True, type=bool))
        self.search_subfolders_cb.setChecked(
            self.settings.value("search_subfolders", True, type=bool)
        )
        self.download_all_cb.setChecked(
            self.settings.value("download_all_readmes", False, type=bool)
        )
        self.branch_override_input.setText(self.settings.value("branch_override", "", type=str))

    def _save_settings(self) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("is_maximized", self.isMaximized())
        self.settings.setValue("dark_mode", self.dark_mode)
        self.settings.setValue("gitlab_url", self.url_input.text().strip())
        self.settings.setValue("group_id", self.group_input.text().strip())
        self.settings.setValue("output_dir", self.output_dir_input.text().strip())
        self.settings.setValue("include_subgroups", self.subgroups_cb.isChecked())
        self.settings.setValue("search_subfolders", self.search_subfolders_cb.isChecked())
        self.settings.setValue("download_all_readmes", self.download_all_cb.isChecked())
        self.settings.setValue("branch_override", self.branch_override_input.text().strip())
        self.settings.setValue("save_token", self.save_token_cb.isChecked())
        self.settings.setValue("verify_ssl", self.ssl_verify_cb.isChecked())

        if self.save_token_cb.isChecked():
            self.settings.setValue("private_token", self.token_input.text().strip())
        else:
            self.settings.remove("private_token")

    def _get_client(self) -> GitLabClient:
        return GitLabClient(
            base_url=self.url_input.text().strip() or "https://gitlab.com",
            private_token=self.token_input.text().strip(),
            verify_ssl=self.ssl_verify_cb.isChecked(),
        )

    def _start_scanning(self) -> None:
        group_id = self.group_input.text().strip()
        if not group_id:
            QMessageBox.warning(
                self,
                "Eingabe erforderlich",
                "Bitte gib eine GitLab Gruppen-ID oder einen Gruppenpfad an.",
            )
            return

        self._save_settings()
        self.scan_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate

        client = self._get_client()
        self.active_worker = ScanWorker(
            client=client,
            group_id=group_id,
            include_subgroups=self.subgroups_cb.isChecked(),
            search_subfolders=self.search_subfolders_cb.isChecked(),
            branch_override=self.branch_override_input.text().strip() or None,
            parent=self,
        )
        self.active_worker.progress.connect(self._on_scan_progress)
        self.active_worker.finished.connect(self._on_scan_finished)
        self.active_worker.error.connect(self._on_worker_error)
        self.active_worker.start()

    def _on_scan_progress(self, current: int, total: int, msg: str) -> None:
        self.status_label.setText(msg)
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)

    def _on_scan_finished(self, projects: list[GitLabProject]) -> None:
        self.projects = projects
        self._populate_table()

        self.scan_btn.setEnabled(True)
        self.download_btn.setEnabled(len(projects) > 0)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        count = len(projects)
        total_readmes = sum(len(p.readme_files) for p in projects)
        if self.search_subfolders_cb.isChecked():
            self.status_label.setText(
                f"Scan abgeschlossen. {count} Projekte gefunden, {total_readmes} README-Dateien entdeckt."
            )
        else:
            self.status_label.setText(f"Scan abgeschlossen. {count} Projekte gefunden.")

    def _populate_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.projects))

        for row, proj in enumerate(self.projects):
            # Column 0: Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            # Default check if project has default branch
            check_item.setCheckState(
                Qt.CheckState.Checked if proj.has_default_branch else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, 0, check_item)

            # Column 1: Path
            path_item = QTableWidgetItem(proj.path_with_namespace)
            path_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, path_item)

            # Column 2: Branch (editable)
            branch_text = proj.default_branch or ""
            branch_item = QTableWidgetItem(branch_text)
            branch_item.setToolTip("Doppelklick zum Ändern des Branches")
            branch_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(row, 2, branch_item)

            # Column 3: Status
            if not proj.has_default_branch or proj.empty_repo:
                status_text = "Leeres Repo"
            elif proj.readme_files:
                if len(proj.readme_files) == 1:
                    status_text = f"✓ 1 README ({proj.readme_files[0]})"
                else:
                    status_text = f"✓ {len(proj.readme_files)} READMEs gefunden"
            else:
                status_text = (
                    "Bereit"
                    if not self.search_subfolders_cb.isChecked()
                    else "Keine README gefunden"
                )
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 3, status_item)

        self.table.blockSignals(False)
        self._update_selection_counter()

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            self._update_selection_counter()
        elif item.column() == 2:
            row = item.row()
            if 0 <= row < len(self.projects):
                new_branch = item.text().strip()
                if new_branch and new_branch != self.projects[row].default_branch:
                    self._change_project_branch(row, new_branch)

    def _show_table_context_menu(self, pos: QPoint) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self.projects):
            return
        project = self.projects[row]
        menu = QMenu(self)

        branch_action = menu.addAction(f"Branch ändern für '{project.name}'...")
        open_action = menu.addAction("🌐 In GitLab öffnen") if project.web_url else None

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == branch_action:
            new_branch, ok = QInputDialog.getText(
                self,
                "Branch ändern",
                f"Branch für Projekt '{project.name}' ({project.path_with_namespace}):",
                QLineEdit.EchoMode.Normal,
                project.default_branch or "main",
            )
            if ok and new_branch.strip():
                self._change_project_branch(row, new_branch.strip())
        elif open_action and chosen == open_action:
            QDesktopServices.openUrl(QUrl(project.web_url))

    def _on_preview_branch_applied(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.projects):
            return
        new_branch = self.branch_input.text().strip()
        if new_branch:
            self._change_project_branch(row, new_branch)

    def _change_project_branch(self, row: int, new_branch: str) -> None:
        if row < 0 or row >= len(self.projects):
            return
        proj = self.projects[row]
        if proj.default_branch == new_branch and proj.readme_files:
            return

        # Update local project representation
        updated_proj = replace(proj, default_branch=new_branch, readme_files=())
        self.projects[row] = updated_proj

        # Update table display
        self.table.blockSignals(True)
        branch_item = self.table.item(row, 2)
        if branch_item and branch_item.text() != new_branch:
            branch_item.setText(new_branch)
        status_item = self.table.item(row, 3)
        if status_item:
            status_item.setText(f"Lade '{new_branch}'...")
        self.table.blockSignals(False)

        # Update preview branch input if currently selected
        if self.table.currentRow() == row:
            self.branch_input.blockSignals(True)
            self.branch_input.setText(new_branch)
            self.branch_input.blockSignals(False)

        self.status_label.setText(
            f"Lade READMEs für '{proj.path_with_namespace}' auf Branch '{new_branch}'..."
        )

        client = self._get_client()
        worker = ProjectBranchWorker(
            client=client, project=updated_proj, branch=new_branch, parent=self
        )
        worker.finished.connect(
            lambda p, r, r_idx=row: self._on_single_project_branch_finished(r_idx, p, r)
        )
        worker.error.connect(
            lambda p, err, r_idx=row: self._on_single_project_branch_error(r_idx, p, err)
        )
        worker.start()
        self._branch_workers.append(worker)

    def _on_single_project_branch_finished(
        self, row: int, project: GitLabProject, readmes: list[str]
    ) -> None:
        if 0 <= row < len(self.projects) and self.projects[row].id == project.id:
            updated = replace(project, readme_files=tuple(readmes))
            self.projects[row] = updated

            self.table.blockSignals(True)
            status_item = self.table.item(row, 3)
            if status_item:
                if readmes:
                    status_text = (
                        f"✓ 1 README ({readmes[0]})"
                        if len(readmes) == 1
                        else f"✓ {len(readmes)} READMEs gefunden"
                    )
                else:
                    status_text = f"Keine README auf '{project.default_branch}'"
                status_item.setText(status_text)
            self.table.blockSignals(False)

            if self.table.currentRow() == row:
                self._update_preview_for_project(updated)

            self.status_label.setText(
                f"Branch für '{project.path_with_namespace}' auf '{project.default_branch}' gewechselt: {len(readmes)} READMEs gefunden."
            )

    def _on_single_project_branch_error(
        self, row: int, project: GitLabProject, error_msg: str
    ) -> None:
        if 0 <= row < len(self.projects) and self.projects[row].id == project.id:
            self.table.blockSignals(True)
            status_item = self.table.item(row, 3)
            if status_item:
                status_item.setText("Fehler beim Branch-Scan")
            self.table.blockSignals(False)
            self.status_label.setText(f"Fehler bei {project.path_with_namespace}: {error_msg}")

    def _update_selection_counter(self) -> None:
        total = self.table.rowCount()
        selected = sum(
            1
            for row in range(total)
            if self.table.item(row, 0)
            and self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        )
        self.table_count_label.setText(f"{selected} von {total} Projekten ausgewählt.")

    def _set_all_selected(self, select: bool) -> None:
        state = Qt.CheckState.Checked if select else Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item = self.table.item(row, 0)
                if item:
                    item.setCheckState(state)
        self.table.blockSignals(False)
        self._update_selection_counter()

    def _apply_filter(self, query: str) -> None:
        search = query.strip().lower()
        for row in range(self.table.rowCount()):
            path_item = self.table.item(row, 1)
            if path_item:
                matches = search in path_item.text().lower()
                self.table.setRowHidden(row, not matches)

    def _update_preview_for_project(self, project: GitLabProject) -> None:
        self.readme_selector.blockSignals(True)
        self.readme_selector.clear()
        if project.readme_files:
            for rf in project.readme_files:
                self.readme_selector.addItem(rf, rf)
            has_multiple = len(project.readme_files) > 1
            self.readme_selector_label.setVisible(has_multiple)
            self.readme_selector.setVisible(has_multiple)
        else:
            self.readme_selector_label.setVisible(False)
            self.readme_selector.setVisible(False)
        self.readme_selector.blockSignals(False)

        selected_file = (
            self.readme_selector.currentData() if self.readme_selector.count() > 0 else None
        )
        self._load_readme_preview(project, selected_file)

    def _on_table_selection_changed(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.projects):
            self.preview_title.setText("<b>README Vorschau</b>")
            self.open_web_btn.setEnabled(False)
            self.branch_label.setVisible(False)
            self.branch_input.setVisible(False)
            self.branch_reload_btn.setVisible(False)
            self.readme_selector_label.setVisible(False)
            self.readme_selector.setVisible(False)
            self.preview_browser.clear()
            return

        project = self.projects[row]
        self.preview_title.setText(f"<b>README Vorschau:</b> {project.path_with_namespace}")
        self.open_web_btn.setEnabled(bool(project.web_url))

        # Show and populate branch controls
        self.branch_label.setVisible(True)
        self.branch_input.setVisible(True)
        self.branch_reload_btn.setVisible(True)
        self.branch_input.blockSignals(True)
        self.branch_input.setText(project.default_branch or "")
        self.branch_input.blockSignals(False)

        self._update_preview_for_project(project)

    def _on_readme_selector_changed(self, index: int) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.projects):
            project = self.projects[row]
            selected_file = self.readme_selector.itemData(index)
            self._load_readme_preview(project, selected_file)

    def _load_readme_preview(self, project: GitLabProject, file_path: str | None = None) -> None:
        out_dir_str = self.output_dir_input.text().strip()
        output_dir = Path(out_dir_str) if out_dir_str else Path.cwd() / "readmes"

        # Check local cache (both hierarchical directory and flat legacy paths)
        candidates_to_check: list[Path] = []
        if file_path:
            candidates_to_check.append(output_dir / project.get_relative_target_path(file_path))
            candidates_to_check.append(output_dir / project.get_safe_filename(file_path))
        if project.readme_files:
            for rf in project.readme_files:
                candidates_to_check.append(output_dir / project.get_relative_target_path(rf))
                candidates_to_check.append(output_dir / project.get_safe_filename(rf))
        for c in GitLabClient.DEFAULT_README_CANDIDATES:
            candidates_to_check.append(output_dir / project.get_relative_target_path(c))
            candidates_to_check.append(output_dir / project.get_safe_filename(c))

        for local_file in candidates_to_check:
            if local_file.is_file():
                try:
                    content = local_file.read_text(encoding="utf-8", errors="replace")
                    self.preview_browser.setMarkdown(content)
                    display_name = local_file.name
                    try:
                        display_name = str(local_file.relative_to(output_dir))
                    except ValueError:
                        pass
                    self.status_label.setText(f"README aus lokalem Cache geladen: {display_name}")
                    return
                except OSError:
                    continue

        # Otherwise, fetch via PreviewWorker
        self.preview_browser.setPlaceholderText("Lade README aus GitLab...")
        self.preview_browser.clear()

        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_worker.requestInterruption()
            self.preview_worker.wait(500)

        client = self._get_client()
        self.preview_worker = PreviewWorker(
            client=client, project=project, file_path=file_path, parent=self
        )
        self.preview_worker.loaded.connect(self._on_preview_loaded)
        self.preview_worker.failed.connect(self._on_preview_failed)
        self.preview_worker.start()

    def _on_preview_loaded(self, project: GitLabProject, filename: str, content: str) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.projects) and self.projects[row].id == project.id:
            self.preview_browser.setMarkdown(content)
            self.status_label.setText(f"README geladen: {project.path_with_namespace} ({filename})")

    def _on_preview_failed(self, project: GitLabProject, error_msg: str) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.projects) and self.projects[row].id == project.id:
            self.preview_browser.setPlainText(f"Keine README verfügbar.\n\n{error_msg}")

    def _start_downloading(self) -> None:
        selected_projects: list[GitLabProject] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_projects.append(self.projects[row])

        if not selected_projects:
            QMessageBox.information(
                self,
                "Keine Auswahl",
                "Bitte wähle mindestens ein Projekt zum Herunterladen aus.",
            )
            return

        out_dir_str = self.output_dir_input.text().strip()
        if not out_dir_str:
            QMessageBox.warning(
                self,
                "Ungültiger Zielordner",
                "Bitte gib einen gültigen Zielordner an.",
            )
            return

        output_dir = Path(out_dir_str)
        output_dir.mkdir(parents=True, exist_ok=True)

        self._save_settings()
        self.scan_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(selected_projects))
        self.progress_bar.setValue(0)

        client = self._get_client()
        self.active_worker = DownloadWorker(
            client=client,
            projects=selected_projects,
            output_dir=output_dir,
            download_all_readmes=self.download_all_cb.isChecked(),
            parent=self,
        )
        self.active_worker.progress.connect(self._on_download_progress)
        self.active_worker.item_completed.connect(self._on_download_item_completed)
        self.active_worker.finished.connect(self._on_download_finished)
        self.active_worker.error.connect(self._on_worker_error)
        self.active_worker.start()

    def _on_download_progress(self, current: int, total: int, project_path: str) -> None:
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Lade herunter ({current}/{total}): {project_path}")

    def _on_download_item_completed(
        self,
        project: GitLabProject,
        filename: str,
        success: bool,
        message: str,
    ) -> None:
        for row in range(self.table.rowCount()):
            if row < len(self.projects) and self.projects[row].id == project.id:
                status_item = self.table.item(row, 3)
                if status_item:
                    status_item.setText("✓ Geladen" if success else f"✗ {message}")
                break

    def _on_download_finished(self, success_count: int, failed_count: int) -> None:
        self.scan_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        msg = (
            f"Download abgeschlossen! {success_count} erfolgreich heruntergeladen, "
            f"{failed_count} übersprungen / ohne README."
        )
        self.status_label.setText(msg)

        # Refresh preview if current selected item was downloaded
        self._on_table_selection_changed()

        QMessageBox.information(self, "Download abgeschlossen", msg)

    def _cancel_active_worker(self) -> None:
        if self.active_worker and self.active_worker.isRunning():
            self.status_label.setText("Abbruch angefordert...")
            self.active_worker.requestInterruption()
            self.cancel_btn.setEnabled(False)

    def _on_worker_error(self, error_msg: str) -> None:
        self.scan_btn.setEnabled(True)
        self.download_btn.setEnabled(len(self.projects) > 0)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        hint = ""
        if "403" in error_msg or "Forbidden" in error_msg:
            hint = (
                "\n\n💡 Mögliche Ursachen für '403 Forbidden':\n"
                "1. Token-Scope: Dein Access Token benötigt zwingend die Berechtigung (Scope) 'read_api' (oder 'api'). Falls beim Erstellen nur 'read_repository' angehakt war, blockiert GitLab den Gruppen-Endpunkt.\n"
                "2. Berechtigung auf die Gruppe: Prüfe, ob dein GitLab-Konto mindestens Leserechte (Reporter / Developer) auf diese Gruppe hat.\n"
                "3. Untergruppen: Deaktiviere testweise 'Untergruppen einbeziehen'."
            )
        elif "certificate verify failed" in error_msg or "SSLError" in error_msg:
            hint = (
                "\n\n💡 Tipp: Dieser GitLab-Server verwendet ein selbstsigniertes oder internes Unternehmenszertifikat.\n"
                "Deaktiviere die Option 'SSL prüfen' oben in der Konfiguration und starte den Scan erneut."
            )
        elif "401" in error_msg or "Unauthorized" in error_msg:
            hint = "\n\n💡 Tipp: Das angegebene Access Token ist ungültig oder abgelaufen."
        elif "404" in error_msg or "Not Found" in error_msg:
            hint = "\n\n💡 Tipp: Die angegebene Gruppe oder der Pfad wurde auf diesem GitLab-Server nicht gefunden."

        self.status_label.setText(f"Fehler: {error_msg}")
        QMessageBox.critical(
            self,
            "Fehler aufgetreten",
            f"Ein Fehler ist aufgetreten:\n\n{error_msg}{hint}",
        )

    def closeEvent(self, event) -> None:
        """Handle clean shutdown on window close."""
        self._save_settings()

        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.requestInterruption()
            self.active_worker.wait(1000)

        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_worker.requestInterruption()
            self.preview_worker.wait(500)

        for bw in self._branch_workers:
            if bw.isRunning():
                bw.requestInterruption()
                bw.wait(300)

        super().closeEvent(event)
