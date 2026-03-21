"""Export / import application settings and statistics (PyQt6)."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from storage import dispose_engine, ensure_engine, stats_database_path
from utils.config import config

BACKUP_FORMAT = "video-encoder-backup"
BACKUP_VERSION = 1


def _build_manifest() -> dict:
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "created": datetime.now(timezone.utc).isoformat(),
    }


def _add_tree_to_zip(z: zipfile.ZipFile, directory: Path, arc_prefix: str) -> None:
    if not directory.is_dir():
        return
    for path in directory.rglob("*"):
        if path.is_file():
            rel = path.relative_to(directory)
            arc = f"{arc_prefix}/{rel.as_posix()}" if arc_prefix else rel.as_posix()
            z.write(path, arc)


class BackupTab(QWidget):
    main_window: Optional[Any] = None

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "<p>Export or restore <b>config.json</b>, the <b>presets</b> folder, "
                "and <b>stats.db</b> (lifetime encoding statistics).</p>"
            )
        )
        root.addWidget(
            QLabel(
                "<p>Logs are not included. After restore, tool paths and the file list "
                "reload from the imported config.</p>"
            )
        )
        exp = QPushButton("Export backup…")
        exp.clicked.connect(self._export_backup)
        root.addWidget(exp)
        imp = QPushButton("Import backup…")
        imp.clicked.connect(self._import_backup)
        root.addWidget(imp)
        root.addStretch()

    def _export_backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export backup",
            "video-encoder-backup.zip",
            "Zip archives (*.zip)",
        )
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", json.dumps(_build_manifest(), indent=2))
                if config.config_file.is_file():
                    z.write(config.config_file, "config.json")
                db = stats_database_path()
                if db.is_file():
                    z.write(db, "stats.db")
                _add_tree_to_zip(z, config.config_dir / "presets", "presets")
            QMessageBox.information(self, "Backup", f"Exported to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export failed", str(e))

    def _import_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import backup",
            "",
            "Zip archives (*.zip)",
        )
        if not path:
            return
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tdir = Path(tmp)
                with zipfile.ZipFile(path, "r") as z:
                    z.extractall(tdir)
                manifest_path = tdir / "manifest.json"
                if not manifest_path.is_file():
                    QMessageBox.warning(self, "Invalid backup", "Missing manifest.json.")
                    return
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("format") != BACKUP_FORMAT:
                    QMessageBox.warning(self, "Invalid backup", "Unrecognized backup format.")
                    return
                mv = manifest.get("version")
                if not isinstance(mv, int) or mv > BACKUP_VERSION:
                    QMessageBox.warning(
                        self,
                        "Invalid backup",
                        "Backup version is newer than this application supports.",
                    )
                    return
                cfg_src = tdir / "config.json"
                if not cfg_src.is_file():
                    QMessageBox.warning(self, "Invalid backup", "Missing config.json.")
                    return

                r = QMessageBox.question(
                    self,
                    "Restore backup",
                    "Replace settings, presets folder, and statistics database with this backup?\n"
                    "Current data will be overwritten.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if r != QMessageBox.StandardButton.Yes:
                    return

                config.flush()
                dispose_engine()

                config.config_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cfg_src, config.config_file)

                presets_src = tdir / "presets"
                presets_dest = config.config_dir / "presets"
                if presets_src.is_dir():
                    if presets_dest.exists():
                        shutil.rmtree(presets_dest)
                    shutil.copytree(presets_src, presets_dest)

                db_src = tdir / "stats.db"
                if db_src.is_file():
                    shutil.copy2(db_src, stats_database_path())

                config.reload()
                ensure_engine()

                mw = self.main_window
                if mw is not None:
                    if hasattr(mw, "stats_tab"):
                        mw.stats_tab.reload_from_db()
                    if hasattr(mw, "refresh_encoder_clients"):
                        mw.refresh_encoder_clients()
                    if hasattr(mw, "files_tab"):
                        mw.files_tab.reload_from_config()
                    if hasattr(mw, "settings_tab"):
                        mw.settings_tab.reload_from_config()
                    if hasattr(mw, "handbrake_tab") and hasattr(mw.handbrake_tab, "on_files_changed"):
                        mw.handbrake_tab.on_files_changed()
                    if hasattr(mw, "ffmpeg_tab") and hasattr(mw.ffmpeg_tab, "on_files_changed"):
                        mw.ffmpeg_tab.on_files_changed()

                QMessageBox.information(
                    self,
                    "Restore complete",
                    "Backup restored. Verify executable paths under Settings if needed.",
                )
        except Exception as e:
            try:
                ensure_engine()
            except Exception:
                pass
            QMessageBox.warning(self, "Import failed", str(e))
