import json
import os
import sys
import re
import time
import subprocess
import socket
import random

# Core Anki imports
from aqt import mw
from aqt import gui_hooks
from aqt.qt import *
from aqt.utils import showInfo, tooltip, qconnect
from anki.notes import Note

# Import our custom modules
from .deps import ensure_dependencies, check_dependencies
from .streak import setup_streak
from .tray_manager import tray_manager
from .ui_explanation import ExplanationDialog

ADDON_NAME = __name__.split(".")[0]

class WhipFlashDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WhipFlash Automation")
        self.resize(850, 750)
        self.setStyleSheet("""
            QPushButton { padding: 5px 10px; border-radius: 4px; }
            QGroupBox { padding-top: 10px; }
            QComboBox, QSpinBox { padding: 3px; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        config = mw.addonManager.getConfig(ADDON_NAME) or {}
        
        # Tools row (Settings, Dependencies)
        top_layout = QHBoxLayout()
        self.btn_deps = QPushButton("Check Dependencies")
        self.btn_deps.clicked.connect(self._check_and_install_deps)
        top_layout.addWidget(self.btn_deps)
        
        self.btn_test_notif = QPushButton("Test Notification")
        self.btn_test_notif.clicked.connect(tray_manager.test_notification)
        top_layout.addWidget(self.btn_test_notif)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 1. Main Text Area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Enter your study text here, or upload a PDF...")
        layout.addWidget(self.text_area)

        # 2. Controls Layout
        controls_layout = QHBoxLayout()

        self.btn_upload_pdf = QPushButton("Upload PDF")
        self.btn_upload_pdf.clicked.connect(self._on_upload_pdf)
        controls_layout.addWidget(self.btn_upload_pdf)

        self.card_type_combo = QComboBox()
        self.card_type_combo.addItems(["Basic", "Cloze", "Mixed"])
        controls_layout.addWidget(self.card_type_combo)

        self.detail_combo = QComboBox()
        self.detail_combo.addItems(["Concise", "Standard", "In-depth"])
        controls_layout.addWidget(self.detail_combo)

        layout.addLayout(controls_layout)
        
        # Curriculum Settings Group
        curr_group = QGroupBox("Curriculum Context")
        curr_layout = QGridLayout()
        
        self.grade_combo = QComboBox()
        self.grade_combo.setEditable(True)
        self.grade_combo.addItems(["GCSE", "A-Level", "IB", "AP", "Undergraduate", "Postgraduate", "Middle School", "High School", "General/None"])
        self.grade_combo.setCurrentText(config.get("grade", "General/None"))
        curr_layout.addWidget(QLabel("Grade:"), 0, 0)
        curr_layout.addWidget(self.grade_combo, 0, 1)
        
        self.subject_combo = QComboBox()
        self.subject_combo.setEditable(True)
        self.subject_combo.addItems(["Biology", "Chemistry", "Physics", "Maths", "History", "Geography", "English", "Computer Science", "Medicine", "Law", "General/None"])
        self.subject_combo.setCurrentText(config.get("subject", "General/None"))
        curr_layout.addWidget(QLabel("Subject:"), 0, 2)
        curr_layout.addWidget(self.subject_combo, 0, 3)
        
        self.board_combo = QComboBox()
        self.board_combo.setEditable(True)
        self.board_combo.addItems(["AQA", "Edexcel", "OCR", "CIE", "College Board", "General/None"])
        self.board_combo.setCurrentText(config.get("board", "General/None"))
        curr_layout.addWidget(QLabel("Board:"), 0, 4)
        curr_layout.addWidget(self.board_combo, 0, 5)
        
        curr_group.setLayout(curr_layout)
        layout.addWidget(curr_group)
        
        # Additional Options Row
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("Deck:"))
        self.deck_combo = QComboBox()
        self.deck_combo.setEditable(True)
        if mw.col:
            self.deck_combo.addItems(mw.col.decks.all_names())
            if "Default" in mw.col.decks.all_names():
                self.deck_combo.setCurrentText("Default")
        options_layout.addWidget(self.deck_combo)

        options_layout.addWidget(QLabel("Amount:"))
        self.amount_combo = QComboBox()
        self.amount_combo.setEditable(True)
        self.amount_combo.setToolTip("Select an estimate or type a specific number (e.g., 20)")
        self.amount_combo.addItems(["Few (~5 cards)", "Normal (~15 cards)", "Many (30+ cards)"])
        self.amount_combo.setCurrentIndex(1)
        options_layout.addWidget(self.amount_combo)

        layout.addLayout(options_layout)

        # Settings Group
        settings_group = QGroupBox("WhipFlash Settings")
        settings_layout = QVBoxLayout()
        
        self.stealth_cb = QCheckBox("Enable Experimental Anti-Bot Stealth (Slower)")
        settings_layout.addWidget(self.stealth_cb)
        
        # Notifications / Auto / Streak Toggles
        sys_layout = QVBoxLayout()
        
        row1 = QHBoxLayout()
        self.tray_cb = QCheckBox("Minimize to Tray")
        self.tray_cb.setChecked(config.get("minimize_to_tray", True))
        row1.addWidget(self.tray_cb)
        
        self.autostart_cb = QCheckBox("Launch on Boot")
        self.autostart_cb.setChecked(config.get("autostart", False))
        row1.addWidget(self.autostart_cb)
        
        self.show_streak_cb = QCheckBox("Show Streak")
        self.show_streak_cb.setChecked(config.get("show_streak", True))
        row1.addWidget(self.show_streak_cb)
        row1.addStretch()
        
        row2 = QHBoxLayout()
        self.spam_cb = QCheckBox("Enable Notifications")
        self.spam_cb.setChecked(config.get("enable_spam", True))
        row2.addWidget(self.spam_cb)
        
        row2.addWidget(QLabel("Interval (mins):"))
        self.spam_interval = QSpinBox()
        self.spam_interval.setRange(1, 1440)
        self.spam_interval.setValue(config.get("notification_frequency", 30))
        row2.addWidget(self.spam_interval)
        
        self.btn_set_streak = QPushButton("Set Streak Offset")
        self.btn_set_streak.clicked.connect(self._set_streak_offset)
        row2.addWidget(self.btn_set_streak)
        row2.addStretch()
        
        sys_layout.addLayout(row1)
        sys_layout.addLayout(row2)

        # Add an explicit Save Settings button here
        self.btn_save_settings = QPushButton("Save Settings")
        self.btn_save_settings.clicked.connect(self._on_save_settings_clicked)
        sys_layout.addWidget(self.btn_save_settings)

        settings_layout.addLayout(sys_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # 3. Action Buttons
        actions_layout = QHBoxLayout()

        self.btn_explain = QPushButton("Generate Topic Explanation")
        self.btn_explain.clicked.connect(self._on_generate_explanation)
        actions_layout.addWidget(self.btn_explain)

        self.btn_generate = QPushButton("Generate Flashcards")
        self.btn_generate.clicked.connect(self._on_generate_cards)
        actions_layout.addWidget(self.btn_generate)

        layout.addLayout(actions_layout)
        self.setLayout(layout)
        
    def _set_streak_offset(self):
        config = mw.addonManager.getConfig(ADDON_NAME) or {}
        current_offset = config.get("streak_offset", 0)
        new_val, ok = QInputDialog.getInt(self, "Streak Offset", "Add or subtract from your real streak:", current_offset, -9999, 9999)
        if ok:
            config["streak_offset"] = new_val
            mw.addonManager.writeConfig(ADDON_NAME, config)
            # Apply to UI if currently on deckbrowser
            mw.reset()
            tooltip("Streak offset updated!")
        
    def _on_save_settings_clicked(self):
        self._save_settings()
        mw.reset()
        tooltip("Settings saved!")

    def _save_settings(self):
        config = mw.addonManager.getConfig(ADDON_NAME) or {}
        config["minimize_to_tray"] = self.tray_cb.isChecked()
        config["enable_spam"] = self.spam_cb.isChecked()
        config["notification_frequency"] = self.spam_interval.value()
        config["show_streak"] = self.show_streak_cb.isChecked()
        
        config["grade"] = self.grade_combo.currentText()
        config["subject"] = self.subject_combo.currentText()
        config["board"] = self.board_combo.currentText()
        
        was_autostart = config.get("autostart", False)
        is_autostart = self.autostart_cb.isChecked()
        config["autostart"] = is_autostart
        
        mw.addonManager.writeConfig(ADDON_NAME, config)
        
        if was_autostart != is_autostart:
            tray_manager.apply_autostart(is_autostart)
            
        tray_manager.setup()
        
    def _check_and_install_deps(self):
        if ensure_dependencies():
            showInfo("Dependencies are ready.")

    def _on_upload_pdf(self):
        try:
            import PyPDF2
        except ImportError:
            showInfo("PyPDF2 is not installed. Please click 'Check Dependencies' at the top.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            extracted_text = ""
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except Exception:
                        pass
                for page in reader.pages:
                    extracted_text += page.extract_text() + "\n"
            
            self.text_area.setPlainText(extracted_text)
            tooltip("PDF text extracted successfully!")
        except Exception as e:
            showInfo(f"Error reading PDF:\n{str(e)}")

    def _get_curriculum_prompt(self):
        grade = self.grade_combo.currentText()
        subject = self.subject_combo.currentText()
        board = self.board_combo.currentText()
        
        prompt = ""
        if grade != "General/None" or subject != "General/None" or board != "General/None":
            prompt = f"Act as an expert examiner for {grade} {subject}, specifically following the {board} specification. Limit your scope, terminology, and depth strictly to what is required for this specific syllabus. Do not include out-of-scope advanced knowledge, and use the exact terminology expected. "
        return prompt

    def _on_generate_explanation(self):
        user_text = self.text_area.toPlainText().strip()
        if not user_text:
            tooltip("Please enter or upload some text first.")
            return

        detail_mode = self.detail_combo.currentText()
        if detail_mode == "Concise":
            detail_instruction = "Keep your explanation extremely concise, brief, and to the point. Focus only on the highest-yield facts."
        elif detail_mode == "In-depth":
            detail_instruction = "Explain it in exhaustive, comprehensive detail. Provide deep dives into the nuances, examples, and edge cases."
        else:
            detail_instruction = "Provide a standard, clear explanation that breaks down the concept so it is easily understandable."

        curr_prompt = self._get_curriculum_prompt()
        instruction = (
            f"{curr_prompt}{detail_instruction} "
            "Do not generate flashcards, just provide the explanation text."
        )
        self._trigger_automation(instruction, user_text, mode="explanation")

    def _on_generate_cards(self):
        user_text = self.text_area.toPlainText().strip()
        if not user_text:
            tooltip("Please enter or upload some text first.")
            return

        card_type = self.card_type_combo.currentText()
        detail_mode = self.detail_combo.currentText()
        amount_mode = self.amount_combo.currentText()
        deck_name = self.deck_combo.currentText()
        
        detail_instruction = "Extract the key facts."
        if detail_mode == "Concise":
            detail_instruction = "Extract only the absolute most essential, concise facts."
        elif detail_mode == "In-depth":
            detail_instruction = "Extract exhaustive, granular details to heavily cover all nuances."

        amount_instruction = "Generate a standard number of flashcards (around 15)."
        if amount_mode.isdigit():
            amount_instruction = f"Generate exactly {amount_mode} flashcards."
        elif "Few" in amount_mode:
            amount_instruction = "Generate a small number of flashcards (around 5)."
        elif "Many" in amount_mode:
            amount_instruction = "Generate a large number of flashcards (30+)."

        curr_prompt = self._get_curriculum_prompt()

        if card_type == "Basic":
            instruction = (
                f"{curr_prompt}You are an expert tutor. I will provide a block of text. {detail_instruction} {amount_instruction} Generate flashcards. "
                "RULES: 1. Output ONLY valid JSON. No conversational filler, no markdown blocks. "
                "2. The JSON must be an array of objects. 3. Each object must have exactly two keys: 'front' and 'back'."
            )
        elif card_type == "Cloze":
            instruction = (
                f"{curr_prompt}You are an expert tutor. I will provide a block of text. {detail_instruction} {amount_instruction} Generate Anki Cloze deletion flashcards. "
                "RULES: 1. Output ONLY valid JSON. No conversational filler, no markdown blocks. "
                "2. The JSON must be an array of objects. 3. Each object must have exactly one key: 'text'. "
                "4. The value of 'text' must be a sentence with the key concept hidden using Anki's cloze format: {{c1::hidden text}}."
            )
        else: # Mixed
            instruction = (
                f"{curr_prompt}You are an expert tutor. I will provide a block of text. {detail_instruction} {amount_instruction} Generate a mix of Basic and Cloze deletion flashcards. "
                "RULES: 1. Output ONLY valid JSON. No conversational filler, no markdown blocks. "
                "2. The JSON must be an array of objects. "
                "3. For Basic cards, the object must have exactly two keys: 'front' and 'back'. "
                "4. For Cloze cards, the object must have exactly one key: 'text', with the value containing Anki's cloze format: {{c1::hidden text}}."
            )

        self._trigger_automation(instruction, user_text, mode="cards", card_type=card_type, deck=deck_name)

    def _auto_start_chromium(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            # If port is open, assume debugging browser is already running
            if s.connect_ex(('127.0.0.1', 9222)) == 0:
                return True
                
        # Common Chrome, Brave, Edge, and Opera install locations on Windows
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        browsers = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        if local_app_data:
            browsers.extend([
                os.path.join(local_app_data, r"Programs\Opera\launcher.exe"),
                os.path.join(local_app_data, r"Programs\Opera GX\opera.exe")
            ])
        
        browser_exe = next((p for p in browsers if os.path.exists(p)), None)
        if not browser_exe:
            showInfo("Could not find Chrome, Brave, Edge, or Opera installed in default locations.\nPlease manually launch a Chromium browser with --remote-debugging-port=9222.")
            return False
            
        try:
            # Launch detached process using the user's default browser profile
            subprocess.Popen([
                browser_exe,
                "--remote-debugging-port=9222",
                "https://gemini.google.com/app"
            ], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            
            # Wait a few seconds for it to bind the port
            time.sleep(3)
            
            # Check if port is open. If not, Chrome was probably already running normally.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_check:
                s_check.settimeout(0.5)
                if s_check.connect_ex(('127.0.0.1', 9222)) != 0:
                    showInfo("Failed to attach debugger to browser.\n\nIMPORTANT: If Chrome/Brave/Edge is already open normally, you MUST close all browser windows completely before running this so it can restart with remote debugging enabled.")
                    return False
                
            return True
        except Exception as e:
            showInfo(f"Error launching browser: {e}")
            return False

    def _trigger_automation(self, instruction, user_text, mode, card_type=None, deck=None):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            showInfo("Playwright missing. Click 'Check Dependencies'.")
            return

        if not self._auto_start_chromium():
            return

        stealth_enabled = self.stealth_cb.isChecked()
        self.btn_generate.setEnabled(False)
        self.btn_explain.setEnabled(False)
        tooltip("WhipFlash is working...")

        mw.taskman.run_in_background(
            lambda: self._run_automation_task(instruction, user_text, mode, card_type, deck, stealth_enabled),
            self._on_automation_done
        )

    def _run_automation_task(self, instruction, user_text, mode, card_type, deck, stealth_enabled):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                
                page = next((p for p in context.pages if "gemini.google.com" in p.url), None)
                if not page:
                    page = context.new_page()
                    page.goto("https://gemini.google.com/app")
                else:
                    page.bring_to_front()

                if stealth_enabled:
                    page.wait_for_timeout(random.randint(500, 1500))

                page.goto("https://gemini.google.com/app")
                page.wait_for_selector("div.ql-editor", timeout=10000)
                page.locator("div.ql-editor").click()
                
                if stealth_enabled:
                    page.keyboard.type(instruction, delay=random.randint(5, 15))
                    page.wait_for_timeout(random.randint(500, 1000))
                    page.keyboard.insert_text(f"\n\nTEXT:\n{user_text}")
                else:
                    page.keyboard.insert_text(f"{instruction}\n\nTEXT:\n{user_text}")
                
                page.wait_for_timeout(500)
                page.locator("button[aria-label='Send message']").click()

                page.wait_for_selector("message-content", state="visible", timeout=90000)
                page.wait_for_timeout(15000) 

                bubbles = page.query_selector_all("message-content")
                return {"success": True, "data": bubbles[-1].inner_text(), "mode": mode, "card_type": card_type, "deck": deck}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _on_automation_done(self, future):
        self.btn_generate.setEnabled(True)
        self.btn_explain.setEnabled(True)

        try:
            result = future.result()
        except Exception as e:
            showInfo(f"WhipFlash Exception:\n{str(e)}")
            return

        if not result["success"]:
            showInfo(f"Automation Error:\n{result['error']}")
            return

        if result["mode"] == "explanation":
            dialog = ExplanationDialog(result['data'], self)
            dialog.exec()
            return

        raw_text = re.sub(r"```json\s*", "", result["data"])
        raw_text = re.sub(r"```\s*", "", raw_text).strip()

        try:
            self._create_anki_notes(json.loads(raw_text), result["card_type"], result.get("deck", "Default"))
        except json.JSONDecodeError:
            showInfo(f"Parsing failed. Raw:\n{raw_text}")

    def _create_anki_notes(self, data_list, card_type, deck_name):
        deck_id = mw.col.decks.id(deck_name)
        added_cards = 0
        
        for item in data_list:
            c_type = "Basic" if "front" in item and "back" in item else "Cloze" if "text" in item else None
            if not c_type: continue
            
            model = mw.col.models.by_name(c_type)
            if not model: continue

            mw.col.models.set_current(model)
            model['did'] = deck_id
            note = Note(mw.col, model)
            
            if c_type == "Basic":
                note["Front"] = item["front"]
                note["Back"] = item["back"]
            elif c_type == "Cloze":
                if "Text" in note.keys(): note["Text"] = item["text"]
                else: note[note.keys()[0]] = item["text"]

            note.model()['did'] = deck_id
            mw.col.addNote(note)
            added_cards += 1

        tooltip(f"WhipFlash added {added_cards} cards to '{deck_name}'")


# -- Hooks and Initialization --
_dialog_instance = None

def open_whipflash():
    global _dialog_instance
    if not _dialog_instance:
        _dialog_instance = WhipFlashDialog(mw)
    _dialog_instance.show()
    _dialog_instance.raise_()
    _dialog_instance.activateWindow()

def on_profile_loaded():
    # Setup background functionality on profile load
    setup_streak()
    tray_manager.setup()

# Top-level Menu Injection
def setup_menu():
    # Directly inject into the Anki Top Menu bar, alongside File, Edit, Tools...
    whipflash_menu = mw.form.menubar.addMenu("&WhipFlash")
    
    action_open = QAction("Open WhipFlash", mw)
    qconnect(action_open.triggered, open_whipflash)
    whipflash_menu.addAction(action_open)

setup_menu()
gui_hooks.profile_did_open.append(on_profile_loaded)
