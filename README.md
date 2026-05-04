# WhipFlash

Built this small tool to generate flashcards for Anki from my textbooks using Gemini. Got tired of copy and pasting into ChatGPT and then formatting manually, and tools already available on Anki use models that are not so great.

If you slack on your reviews, this add-on will ping you in the tray to do your due cards, and tracks your daily streak in the toolbar to keep you motivated.

## What It Does
- Scrapes text or reads PDFs and directly injects Basic, Cloze, or Mixed flashcards into Anki.
- Uploads this to Gemini by opening up a browser in the background (**MAKE SURE YOU ARE LOGGED IN TO GOOGLE GEMINI BEFORE USING**) and then automatically adds to Anki.
- Provides a clean markdown window to explain a topic if you just want to understand something.
- Hooks into Anki's close function so it minimizes to your system tray.
- Counts your daily streak (`🔥 X`) and puts it on the main screen.
- Cross-platform autostart hook so it opens on system boot.

## Setup 1
Download from AnkiWeb addons:
https://ankiweb.net/shared/info/1549373528?cb=1777909267751
## Setup 2
1. Clone / download this repo into your Anki `addons21` folder. You might need to rename the folder if Anki throws a fit.
2. Restart Anki.
3. Check the top bar next to "Tools" and open WhipFlash.
4. Click **Check Dependencies**. This fires up pip inside Anki's environment to install pyPDF2, Playwright, and Chromium. It might take a minute depending on your internet. Note: If pip throws permission errors, just open Anki as Admin/sudo once.

## Usage Notes
- Make sure you actually have **Chrome, Edge, Brave, or Opera** already installed on your PC. Playwright tries to hook into your default setup.
- **Firefox is NOT supported by default** using this technique. Use chromium-based browsers.
- If it says "Failed to attach debugger", you probably have a browser window already open natively. You MUST fully close out all Chrome/Edge processes so the background script can re-launch it with dev-ports active (`--remote-debugging-port=9222`).
- Settings for toggling the tray, boot, and spam notifications are in the WhipFlash UI directly.

## Common Bugs & Workarounds
- **Playwright Missing after Check Dependencies:** If Anki fails to install pip packages, try opening Anki via administrator/sudo temporarily, click the button again, wait, then restart normally.
- **Anki closes instead of minimizing to tray:** Open WhipFlash -> Settings, toggle "Minimize to Tray" off and on again to forcefully save the config file. Then press save settings.
- **Streak doesn't show:** If your `🔥` toolbar icon vanishes, check "Show Streak" in the WhipFlash settings. You can also manually adjust your streak count offset if you feel you were robbed of a day. Then press save settings.
