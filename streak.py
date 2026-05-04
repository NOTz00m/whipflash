from aqt import mw
from aqt import gui_hooks
from anki.utils import intTime
import time

ADDON_NAME = __name__.split(".")[0]

def get_current_streak():
    if not mw.col:
        return 0
        
    # Anki's day rollover
    rollover = mw.col.conf.get("rollover", 4)
    
    # Calculate today's cutoff in ms
    now = time.time()
    # Adjust for rollover to get local "days"
    # To find the start of Anki today:
    # 1. Get current time in local timezone
    # 2. Subtract rollover hours
    # 3. Floor to start of day
    
    from datetime import datetime, timedelta
    
    dt_now = datetime.now()
    dt_adjusted = dt_now - timedelta(hours=rollover)
    dt_start_of_today_adjusted = dt_adjusted.replace(hour=0, minute=0, second=0, microsecond=0)
    
    streak = 0
    
    while True:
        # Define the 24-hour window for the day we are checking
        start_of_day = dt_start_of_today_adjusted - timedelta(days=streak)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Add back rollover to get actual timestamp windows
        actual_start = start_of_day + timedelta(hours=rollover)
        actual_end = end_of_day + timedelta(hours=rollover)
        
        start_ms = int(actual_start.timestamp() * 1000)
        end_ms = int(actual_end.timestamp() * 1000)
        
        # Query revlog for any reviews in this window
        count = mw.col.db.scalar(
            "select count() from revlog where id >= ? and id < ?",
            start_ms, end_ms
        )
        
        if count > 0:
            streak += 1
        else:
            # If counting today (streak == 0) and today has no reviews, it's not broken until tomorrow.
            # So, we check yesterday.
            if streak == 0:
                # Check yesterday before breaking
                start_of_yesterday = start_of_day - timedelta(days=1)
                end_of_yesterday = start_of_day
                actual_start_y = start_of_yesterday + timedelta(hours=rollover)
                actual_end_y = end_of_yesterday + timedelta(hours=rollover)
                
                count_y = mw.col.db.scalar(
                    "select count() from revlog where id >= ? and id < ?",
                    int(actual_start_y.timestamp() * 1000), 
                    int(actual_end_y.timestamp() * 1000)
                )
                if count_y > 0:
                    streak += 1 # They missed today so far, but yesterday is done, so streak is active but waiting for today.
                    dt_start_of_today_adjusted = dt_start_of_today_adjusted - timedelta(days=1) # Shift perspective to count carefully
                    continue # Keep checking backwards from yesterday
            break
            
    config = mw.addonManager.getConfig(ADDON_NAME) or {}
    offset = config.get("streak_offset", 0)
    return max(0, streak + offset)

def inject_streak(deck_browser, content):
    config = mw.addonManager.getConfig(ADDON_NAME) or {}
    if not config.get("show_streak", True):
        return
        
    streak = get_current_streak()
    
    streak_html = f"""
    <div style="position: absolute; top: 15px; right: 25px; font-weight: bold; font-family: sans-serif; display: inline-flex; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.1); border-radius: 20px; padding: 5px 15px; color: #ff6b6b; z-index: 1000; font-size: 1.2rem;" title="{streak} Day Study Streak!">
        🔥 {streak}
    </div>
    """
    
    # Append the streak to the deck browser content's stats section
    content.stats += streak_html

def setup_streak():
    gui_hooks.deck_browser_will_render_content.append(inject_streak)
