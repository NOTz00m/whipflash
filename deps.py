import os
import sys
import subprocess
from threading import Thread
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, tooltip

def check_dependencies():
    missing = []
    try:
        import PyPDF2
    except ImportError:
        missing.append("PyPDF2")
        
    try:
        import playwright
    except ImportError:
        missing.append("playwright")
        
    try:
        import markdown
    except ImportError:
        missing.append("markdown")
        
    return missing

class DependencyInstallerDialog(QDialog):
    def __init__(self, missing_deps, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WhipFlash - Installing Dependencies")
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.missing_deps = missing_deps
        
        layout = QVBoxLayout()
        self.label = QLabel(f"Installing missing dependencies for WhipFlash:\n{', '.join(missing_deps)}\n\nThis may take a few minutes (especially for Playwright/Chromium)...")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate
        layout.addWidget(self.progress)
        
        self.setLayout(layout)
        
    def start_install(self):
        self.thread = Thread(target=self._install_worker)
        self.thread.start()
        
    def _install_worker(self):
        try:
            # Install python packages
            subprocess.run([sys.executable, "-m", "pip", "install"] + self.missing_deps, check=True, capture_output=True)
            
            # If playwright is in the missing deps, we need to install the browsers
            if "playwright" in self.missing_deps:
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
                
            # Use QTimer to safely close dialog from main thread
            QMetaObject.invokeMethod(self, "accept", Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            def show_error():
                showInfo(f"Failed to install dependencies.\nError: {e}")
                self.reject()
            # Invoke error dialog in main thread
            QMetaObject.invokeMethod(self, "reject", Qt.ConnectionType.QueuedConnection)

def ensure_dependencies():
    missing = check_dependencies()
    if missing:
        dialog = DependencyInstallerDialog(missing, mw)
        dialog.show()
        dialog.start_install()
        dialog.exec()
        
        # Re-check after install
        if check_dependencies():
            showInfo("Some dependencies are still missing. WhipFlash may not work correctly.")
            return False
    return True
