from activity_monitor import ActivityMonitor
from gamification import Gamification
from ui_components import HealthAppUI

if __name__ == "__main__":
    app = HealthAppUI(ActivityMonitor(None), Gamification())
    app.monitor.app = app  # Set the app reference after initialization
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()