"""Check GitHub releases and apply updates (frozen) or show source instructions."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from utils.app_update import (
    GitHubRelease,
    apply_installer_windows,
    compare_to_local,
    download_asset,
    fetch_release_safe,
    launch_portable_replace_after_exit,
    open_mac_artifact,
    pick_asset_safe,
)
from utils.app_version import effective_update_channel, get_app_version, is_frozen
from utils.repo_root import find_git_repo_root, git_on_path, run_git_pull


class _FetchWorker(QThread):
    finished = pyqtSignal(object, object)

    def run(self):
        rel, err = fetch_release_safe()
        self.finished.emit(rel, err)


class _DownloadWorker(QThread):
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url: str, dest: Path):
        super().__init__()
        self._url = url
        self._dest = dest

    def run(self):
        try:
            download_asset(self._url, self._dest)
            self.finished_ok.emit(str(self._dest))
        except Exception as e:
            self.failed.emit(str(e))


class UpdateCheckDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check for updates")
        self.resize(560, 460)
        self._release: GitHubRelease | None = None
        self._fetch_worker: _FetchWorker | None = None
        self._download_worker: _DownloadWorker | None = None
        self._local = get_app_version()
        self._channel = effective_update_channel()
        self._repo_root: Path | None = None

        v = QVBoxLayout(self)
        self._status = QLabel("Checking GitHub…")
        self._status.setWordWrap(True)
        v.addWidget(self._status)

        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setMaximumHeight(160)
        self._detail.hide()
        v.addWidget(self._detail)

        self._source_box = QTextEdit()
        self._source_box.setReadOnly(True)
        self._source_box.setMaximumHeight(110)
        self._source_box.hide()
        v.addWidget(self._source_box)

        row = QHBoxLayout()
        self._btn_refresh = QPushButton("Check again")
        self._btn_refresh.clicked.connect(self._start_fetch)
        row.addWidget(self._btn_refresh)
        self._btn_release = QPushButton("Open release page")
        self._btn_release.clicked.connect(self._open_release)
        self._btn_release.setEnabled(False)
        row.addWidget(self._btn_release)
        self._btn_apply = QPushButton("Download and install…")
        self._btn_apply.clicked.connect(self._on_download_apply)
        self._btn_apply.setEnabled(False)
        row.addWidget(self._btn_apply)
        self._btn_git = QPushButton("Run git pull")
        self._btn_git.clicked.connect(self._on_git_pull)
        self._btn_git.hide()
        row.addStretch()
        v.addLayout(row)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bbox.rejected.connect(self.reject)
        v.addWidget(bbox)

        self._wire_source_git()
        self._start_fetch()

    def _wire_source_git(self) -> None:
        if is_frozen():
            return
        root = find_git_repo_root()
        self._repo_root = root
        if root and git_on_path():
            self._btn_git.show()

    def _source_command_text(self) -> str:
        root = find_git_repo_root()
        lines: list[str] = []
        if root:
            lines.append(f"cd {root}")
        lines.append("git pull")
        req = (root or Path.cwd()) / "requirements.txt"
        if root and (root / "requirements.txt").is_file():
            lines.append("pip install -r requirements.txt")
        elif req.is_file():
            lines.append(f"pip install -r {req}")
        else:
            lines.append("pip install -r requirements.txt")
        return "\n".join(lines)

    def _start_fetch(self) -> None:
        self._status.setText("Checking GitHub…")
        self._btn_refresh.setEnabled(False)
        self._release = None
        self._detail.hide()
        self._source_box.hide()
        self._btn_release.setEnabled(False)
        self._btn_apply.setEnabled(False)
        if self._fetch_worker and self._fetch_worker.isRunning():
            return
        self._fetch_worker = _FetchWorker()
        self._fetch_worker.finished.connect(self._on_fetched)
        self._fetch_worker.start()

    def _on_fetched(self, release_obj, err) -> None:
        self._btn_refresh.setEnabled(True)
        if err:
            self._status.setText(str(err))
            return
        release: GitHubRelease = release_obj
        self._release = release
        cmp = compare_to_local(release.tag_name, self._local)
        if cmp == "newer":
            self._status.setText(
                f"A newer release is available: {release.version_normalized} "
                f"(you have {self._local})."
            )
        elif cmp == "older_or_equal":
            self._status.setText(
                f"You are up to date. Latest release is {release.version_normalized} "
                f"(local {self._local})."
            )
        else:
            self._status.setText(
                f"Latest release: {release.version_normalized}. "
                f"Local version {self._local!r} could not be compared automatically."
            )
        if release.body.strip():
            self._detail.setPlainText(release.body.strip()[:8000])
            self._detail.show()
        else:
            self._detail.hide()
        self._btn_release.setEnabled(bool(release.html_url))

        asset = pick_asset_safe(release, self._channel)
        if is_frozen() and asset and cmp != "older_or_equal":
            self._btn_apply.setEnabled(True)
        elif is_frozen() and asset and cmp == "older_or_equal":
            self._btn_apply.setEnabled(False)
        else:
            self._btn_apply.setEnabled(False)

        if not is_frozen():
            self._source_box.setPlainText(self._source_command_text())
            self._source_box.show()

    def _on_download_apply(self) -> None:
        if not self._release:
            return
        asset = pick_asset_safe(self._release, self._channel)
        if not asset:
            QMessageBox.warning(
                self,
                "Update",
                "No suitable download file was found for this platform.",
            )
            return
        url = str(asset.get("browser_download_url") or "")
        name = str(asset.get("name") or "download")
        if not url:
            return
        dest = Path(tempfile.gettempdir()) / name
        self._btn_apply.setEnabled(False)
        self._status.setText("Downloading…")
        self._download_worker = _DownloadWorker(url, dest)
        self._download_worker.finished_ok.connect(self._on_downloaded)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _on_download_failed(self, msg: str) -> None:
        self._btn_apply.setEnabled(True)
        self._status.setText("Download failed.")
        QMessageBox.critical(self, "Download failed", msg)

    def _on_downloaded(self, path_str: str) -> None:
        path = Path(path_str)
        try:
            if sys.platform == "win32":
                ch = self._channel
                if path.suffix.lower() == ".exe" and (
                    ch == "inno" or ch == "unknown"
                ):
                    apply_installer_windows(path)
                    QMessageBox.information(
                        self,
                        "Installer started",
                        "Complete the installer in the other window. "
                        "This app will now close.",
                    )
                    QApplication.instance().quit()
                    return
                if path.suffix.lower() == ".zip" and (
                    ch == "portable" or ch == "unknown"
                ):
                    launch_portable_replace_after_exit(path)
                    QMessageBox.information(
                        self,
                        "Updating",
                        "This app will close. Files will be replaced, "
                        "then the app will start again.",
                    )
                    QApplication.instance().quit()
                    return
            if sys.platform == "darwin" and path.suffix.lower() in (
                ".dmg",
                ".zip",
            ):
                open_mac_artifact(path)
                QMessageBox.information(
                    self,
                    "Download complete",
                    "The file was opened. Quit this app, install or replace "
                    "the application, then launch it again.",
                )
                return
            QMessageBox.information(
                self,
                "Download complete",
                f"Saved to:\n{path}\n\nInstall or extract this file manually.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Update", str(e))
        finally:
            self._btn_apply.setEnabled(True)
            self._status.setText("Ready.")

    def _open_release(self) -> None:
        if self._release and self._release.html_url:
            QDesktopServices.openUrl(QUrl(self._release.html_url))

    def _on_git_pull(self) -> None:
        root = self._repo_root or find_git_repo_root()
        if not root:
            QMessageBox.warning(
                self,
                "git pull",
                "Could not find a git repository root.",
            )
            return
        code, out, err = run_git_pull(root)
        msg = (out + "\n" + err).strip() or "(no output)"
        if code == 0:
            QMessageBox.information(self, "git pull", msg)
        else:
            QMessageBox.warning(self, "git pull", msg)


def show_update_dialog(parent=None) -> None:
    dlg = UpdateCheckDialog(parent)
    dlg.exec()
