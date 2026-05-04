import os
import sys
from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip
import platform

ADDON_NAME = __name__.split(".")[0]

class TrayManager:
    def __init__(self):
        self.tray_icon = None
        self.timer = None
        self.original_close_event = None
        
    def setup(self):
        config = mw.addonManager.getConfig(ADDON_NAME) or {}
        
        # 1. Handle Minimize to Tray (close event hook)
        if config.get("minimize_to_tray", True):
            if not self.original_close_event:
                self.original_close_event = mw.closeEvent
                mw.closeEvent = self._custom_close_event
        else:
            if self.original_close_event:
                mw.closeEvent = self.original_close_event
                self.original_close_event = None
                
        # 2. Always setup tray icon (needed for notifications anyway)
        self._init_tray()
        
        # 3. Handle Timers for spam
        self._setup_timer()
        
    def _init_tray(self):
        if self.tray_icon is None:
            self.tray_icon = QSystemTrayIcon(mw)
            # Use Anki's window icon
            self.tray_icon.setIcon(mw.windowIcon())
            
            menu = QMenu()
            show_action = menu.addAction("Show Anki")
            show_action.triggered.connect(self._show_window)
            
            quit_action = menu.addAction("Quit Anki")
            quit_action.triggered.connect(self._quit_app)
            
            self.tray_icon.setContextMenu(menu)
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick or \
           reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        mw.showNormal()
        mw.activateWindow()

    def _quit_app(self):
        # Restore original close event so Anki can shut down properly
        mw.closeEvent = self.original_close_event
        mw.close()

    def _custom_close_event(self, event):
        config = mw.addonManager.getConfig(ADDON_NAME) or {}
        if config.get("minimize_to_tray", True):
            event.ignore()
            mw.hide()
            self.tray_icon.showMessage(
                "Anki (WhipFlash)",
                "Anki is still running in the background to remind you about reviews.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.original_close_event(event)

    def _setup_timer(self):
        if self.timer is None:
            self.timer = QTimer(mw)
            self.timer.timeout.connect(self._check_reviews)
            
        config = mw.addonManager.getConfig(ADDON_NAME) or {}
        freq_mins = config.get("notification_frequency", 30)
        
        # start timer
        if config.get("enable_spam", True):
            self.timer.start(freq_mins * 60 * 1000)
        else:
            self.timer.stop()

    def _check_reviews(self):
        if not mw.col:
            return
            
        try:
            # Count due cards
            due_count = len(mw.col.find_cards("is:due"))
            if due_count > 0:
                self.tray_icon.showMessage(
                    "WhipFlash Reminder!",
                    f"Stop slacking! You have {due_count} due cards waiting for you.",
                    QSystemTrayIcon.MessageIcon.Warning,
                    5000
                )
        except Exception:
            pass

    def test_notification(self):
        if self.tray_icon:
            self.tray_icon.showMessage(
                "WhipFlash Test",
                "This is a test notification! Get back to studying.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def apply_autostart(self, enable):
        """Cross-platform autostart configuration."""
        if platform.system() == "Windows":
            self._windows_autostart(enable)
        elif platform.system() == "Darwin":
            self._mac_autostart(enable)
        elif platform.system() == "Linux":
            self._linux_autostart(enable)

    def _windows_autostart(self, enable):
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
        try:
            if enable:
                winreg.SetValueEx(key, "Anki_WhipFlash", 0, winreg.REG_SZ, sys.executable)
            else:
                winreg.DeleteValue(key, "Anki_WhipFlash")
        except FileNotFoundError:
            pass # Already removed
        finally:
            winreg.CloseKey(key)

    def _mac_autostart(self, enable):
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.whipflash.anki.plist")
        if enable:
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.whipflash.anki</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Anki.app/Contents/MacOS/Anki</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            with open(plist_path, "w") as f:
                f.write(plist_content)
        else:
            if os.path.exists(plist_path):
                os.remove(plist_path)

    def _linux_autostart(self, enable):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "anki-whipflash.desktop")
        
        if enable:
            os.makedirs(autostart_dir, exist_ok=True)
            content = """[Desktop Entry]
Type=Application
Exec=anki
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Anki
Comment=Start Anki on login
"""
            with open(desktop_file, "w") as f:
                f.write(content)
        else:
            if os.path.exists(desktop_file):
                os.remove(desktop_file)

tray_manager = TrayManager()
