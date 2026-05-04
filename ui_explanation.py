from aqt.qt import *

class ExplanationDialog(QDialog):
    def __init__(self, markdown_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WhipFlash - AI Explanation")
        self.resize(800, 600)
        
        # Try to parse markdown if the module is installed
        try:
            import markdown
            html_content = markdown.markdown(
                markdown_text, 
                extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists']
            )
        except ImportError:
            # Fallback to plain text if markdown module is missing
            html_content = f"<pre style='font-family: inherit; font-size: 14px; white-space: pre-wrap;'>{markdown_text}</pre>"
            
        layout = QVBoxLayout()
        
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setHtml(html_content)
        
        # Set some base styling for the QTextBrowser
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                padding: 15px;
            }
        """)
        
        layout.addWidget(self.text_browser)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.setLayout(layout)
