import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import time
from pynput import keyboard, mouse
from threading import Thread
import win32gui
import mss
from PIL import Image, ImageChops
import numpy as np
import ctypes
import winsound
import os
import json
import datetime

# Constants
COLORS = {
    "primary": "#2A579A",
    "secondary": "#4CAF50",
    "background": "#FFFFFF",
    "text": "#333333",
    "highlight": "#FF9800",
    "paused": "#607D8B"
}

DEFAULT_WORK_MINUTES = 25
DEFAULT_BREAK_MINUTES = 5
IDLE_THRESHOLD = 30  # Seconds of inactivity to consider user idle
SCREEN_CHECK_INTERVAL = 15  # Seconds between screen checks

class ActivityMonitor:
    def __init__(self, app):
        self.app = app
        self.last_activity_time = time.time()
        self.listener_running = True
        self.last_window = None
        self.last_screenshot = None
        
        # Start all monitoring threads
        self.start_keyboard_listener()
        self.start_mouse_listener()
        self.start_window_monitor()
        self.start_screen_monitor()

    def start_keyboard_listener(self):
        def on_key_press(key):
            print(f"Keyboard activity detected: {key}")
            self.on_activity()
            
        self.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.keyboard_listener.start()

    def start_mouse_listener(self):
        def on_mouse_move(x, y):
            print("Mouse movement detected")
            self.on_activity()
            
        def on_mouse_click(x, y, button, pressed):
            if pressed:
                print(f"Mouse click detected: {button}")
                self.on_activity()
                
        def on_mouse_scroll(x, y, dx, dy):
            print("Mouse scroll detected")
            self.on_activity()
            
        self.mouse_listener = mouse.Listener(
            on_move=on_mouse_move,
            on_click=on_mouse_click,
            on_scroll=on_mouse_scroll
        )
        self.mouse_listener.start()

    def start_window_monitor(self):
        self.window_thread = Thread(target=self.monitor_active_window)
        self.window_thread.daemon = True
        self.window_thread.start()

    def start_screen_monitor(self):
        self.screen_thread = Thread(target=self.monitor_screen_changes)
        self.screen_thread.daemon = True
        self.screen_thread.start()

    def on_activity(self, *args, **kwargs):
        if not self.app.paused:
            self.last_activity_time = time.time()

    def monitor_active_window(self):
        """Track active window changes using pywin32"""
        while self.listener_running:
            try:
                current_window = win32gui.GetForegroundWindow()
                if current_window != self.last_window:
                    self.last_window = current_window
                    window_title = win32gui.GetWindowText(current_window)
                    print(f"Window changed to: {window_title}")
                    self.on_activity()
                time.sleep(1)
            except Exception as e:
                print(f"Window monitoring error: {str(e)}")

    def monitor_screen_changes(self):
        """Detect screen changes using mss and PIL"""
        with mss.mss() as sct:
            last_screenshot = None
            monitor = sct.monitors[1]
            
            while self.listener_running:
                if not self.app.paused:
                    try:
                        screenshot = sct.grab(monitor)
                        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                        img = img.convert("L").resize((32, 32))
                        
                        if last_screenshot is not None:
                            diff = ImageChops.difference(img, last_screenshot)
                            diff_array = np.array(diff)
                            change_score = np.sum(diff_array) / 255
                            
                            if change_score > 100:
                                print(f"Significant screen change detected (score: {change_score:.1f})")
                                self.on_activity()
                        
                        last_screenshot = img
                    except Exception as e:
                        print(f"Screen monitoring error: {str(e)}")
                
                time.sleep(SCREEN_CHECK_INTERVAL)

    def stop(self):
        self.listener_running = False
        self.keyboard_listener.stop()
        self.mouse_listener.stop()







class Gamification:
    def __init__(self):
        self.data = {
            'points': 0,
            'daily_breaks': 0,
            'current_streak': 0,
            'last_break_date': None,
            'challenges': {
                'weekly_points': {'target': 500, 'progress': 0, 'completed': False},
                'weekly_breaks': {'target': 10, 'progress': 0, 'completed': False}
            },
            'last_reset': None
        }
        self.load_data()
        self.check_weekly_reset()

    def load_data(self):
        try:
            with open('gamification.json', 'r') as f:
                loaded_data = json.load(f)
                # Convert string dates to date objects
                for date_field in ['last_break_date', 'last_reset']:
                    if loaded_data.get(date_field):
                        loaded_data[date_field] = datetime.datetime.strptime(
                            loaded_data[date_field], '%Y-%m-%d').date()
                self.data.update(loaded_data)
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_data()

    def save_data(self):
        data_to_save = self.data.copy()
        # Convert date objects to strings
        for date_field in ['last_break_date', 'last_reset']:
            if data_to_save.get(date_field):
                data_to_save[date_field] = data_to_save[date_field].isoformat()
        with open('gamification.json', 'w') as f:
            json.dump(data_to_save, f)

    def check_weekly_reset(self):
        if not self.data['last_reset'] or \
                (datetime.date.today() - self.data['last_reset']).days >= 7:
            self.reset_weekly_challenges()

    def reset_weekly_challenges(self):
        self.data['challenges']['weekly_points']['progress'] = 0
        self.data['challenges']['weekly_points']['completed'] = False
        self.data['challenges']['weekly_breaks']['progress'] = 0
        self.data['challenges']['weekly_breaks']['completed'] = False
        self.data['last_reset'] = datetime.date.today()
        self.save_data()

    def add_points(self, points):
        self.data['points'] += points
        if not self.data['challenges']['weekly_points']['completed']:
            self.data['challenges']['weekly_points']['progress'] += points
            if self.data['challenges']['weekly_points']['progress'] >= \
                    self.data['challenges']['weekly_points']['target']:
                self.data['challenges']['weekly_points']['completed'] = True
                self.data['points'] += 100  # Bonus points
        self.save_data()

    def record_break(self):
        today = datetime.date.today()
        if self.data['last_break_date'] != today:
            # New day, update streak
            if self.data['last_break_date'] and \
                    (today - self.data['last_break_date']).days == 1:
                self.data['current_streak'] += 1
            else:
                self.data['current_streak'] = 1
            self.data['last_break_date'] = today
            self.data['daily_breaks'] = 1
        else:
            self.data['daily_breaks'] += 1

        # Update challenges
        if not self.data['challenges']['weekly_breaks']['completed']:
            self.data['challenges']['weekly_breaks']['progress'] += 1
            if self.data['challenges']['weekly_breaks']['progress'] >= \
                    self.data['challenges']['weekly_breaks']['target']:
                self.data['challenges']['weekly_breaks']['completed'] = True
                self.data['points'] += 50  # Bonus points

        self.save_data()







class HealthAppUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HealthGuard Pro")
        self.geometry("1000x700")
        self.configure(bg=COLORS["background"])

        # Initialize states with proper defaults
        self.paused = False
        self.active_time = 0
        self.app_state = "working"
        self.break_start_time = 0
        self.snooze_until = 0

        # Initialize settings with validated defaults
        self.work_interval = tk.IntVar(value=DEFAULT_WORK_MINUTES)
        self.break_duration = tk.IntVar(value=DEFAULT_BREAK_MINUTES)

        # Initialize previous values tracking
        self.prev_work = DEFAULT_WORK_MINUTES
        self.prev_break = DEFAULT_BREAK_MINUTES

        # Audio files check
        self.break_sound = "break_alert.wav"
        self.continue_sound = "continue_alert.wav"
        self.check_audio_files()

        # Initialize activity monitor FIRST
        self.monitor = ActivityMonitor(self)

        # Setup UI components
        self.setup_styles()
        self.create_widgets()

        # Initialize gamification AFTER UI components
        self.gamification = Gamification()

        # Add gamification tab
        self.gamification_tab = self.create_gamification_tab()
        self.notebook.add(self.gamification_tab, text=" Gamification ")

        # Finish initialization
        self.setup_settings_listeners()
        self.update_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure styles
        style.configure("TNotebook", background=COLORS["background"])
        style.configure("TNotebook.Tab", 
                       font=("Segoe UI", 10, "bold"), 
                       padding=[15, 5])
        style.configure("Primary.TButton", 
                       font=("Segoe UI", 10, "bold"),
                       foreground="white", 
                       background=COLORS["primary"])
        style.configure("Warning.TButton",
                       font=("Segoe UI", 10, "bold"),
                       foreground="white",
                       background=COLORS["highlight"])
        style.configure("Card.TFrame", 
                       background="white", 
                       relief="raised", 
                       borderwidth=1)


    def create_widgets(self):
        # Create notebook FIRST
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Create initial tabs
        self.dashboard_tab = self.create_dashboard()
        self.settings_tab = self.create_settings_tab()

        self.notebook.add(self.dashboard_tab, text=" Dashboard ")
        self.notebook.add(self.settings_tab, text=" Settings ")




    def create_gamification_tab(self):
        tab = ttk.Frame(self.notebook)
        
        # Points Card
        points_frame = ttk.Frame(tab, style="Card.TFrame")
        points_frame.pack(fill="x", padx=20, pady=10, ipadx=10, ipady=10)
        ttk.Label(points_frame, text="Total Points", 
                 font=("Segoe UI", 12)).pack()
        self.points_label = ttk.Label(points_frame, 
                                    text=str(self.gamification.data['points']),
                                    font=("Segoe UI", 24, "bold"),
                                    foreground=COLORS["primary"])
        self.points_label.pack(pady=5)

        # Streak Card
        streak_frame = ttk.Frame(tab, style="Card.TFrame")
        streak_frame.pack(fill="x", padx=20, pady=10, ipadx=10, ipady=10)
        ttk.Label(streak_frame, text="Current Streak", 
                 font=("Segoe UI", 12)).pack()
        self.streak_label = ttk.Label(streak_frame, 
                                     text=f"{self.gamification.data['current_streak']} days",
                                     font=("Segoe UI", 18),
                                     foreground=COLORS["secondary"])
        self.streak_label.pack(pady=5)

        # Challenges
        challenges_frame = ttk.LabelFrame(tab, text="Weekly Challenges")
        challenges_frame.pack(fill="x", padx=20, pady=10)
        
        self.weekly_points_challenge = ttk.Label(challenges_frame,
            text=f"Earn {self.gamification.data['challenges']['weekly_points']['target']} points: "
                 f"{self.gamification.data['challenges']['weekly_points']['progress']}/"
                 f"{self.gamification.data['challenges']['weekly_points']['target']}")
        self.weekly_points_challenge.pack(anchor="w", padx=10, pady=5)
        
        self.weekly_breaks_challenge = ttk.Label(challenges_frame,
            text=f"Take {self.gamification.data['challenges']['weekly_breaks']['target']} breaks: "
                 f"{self.gamification.data['challenges']['weekly_breaks']['progress']}/"
                 f"{self.gamification.data['challenges']['weekly_breaks']['target']}")
        self.weekly_breaks_challenge.pack(anchor="w", padx=10, pady=5)

        return tab
    

    def update_gamification_display(self):
        """Refresh all gamification-related UI elements"""
        # Update points display
        self.points_label.config(text=str(self.gamification.data['points']))
        
        # Update streak display with emoji
        streak_text = f"{self.gamification.data['current_streak']} days "
        streak_text += "🔥" * min(self.gamification.data['current_streak'], 3)
        self.streak_label.config(text=streak_text)
        
        # Update challenges progress
        points_challenge = self.gamification.data['challenges']['weekly_points']
        points_text = f"Earn {points_challenge['target']} points: "
        points_text += f"{points_challenge['progress']}/{points_challenge['target']}"
        if points_challenge['completed']:
            points_text += " ✓"
        self.weekly_points_challenge.config(text=points_text)
        
        breaks_challenge = self.gamification.data['challenges']['weekly_breaks']
        breaks_text = f"Take {breaks_challenge['target']} breaks: "
        breaks_text += f"{breaks_challenge['progress']}/{breaks_challenge['target']}"
        if breaks_challenge['completed']:
            breaks_text += " ✓"
        self.weekly_breaks_challenge.config(text=breaks_text)
        
        # Visual feedback for completed challenges
        if points_challenge['completed']:
            self.weekly_points_challenge.config(foreground=COLORS["secondary"])
        else:
            self.weekly_points_challenge.config(foreground=COLORS["text"])
            
        if breaks_challenge['completed']:
            self.weekly_breaks_challenge.config(foreground=COLORS["secondary"])
        else:
            self.weekly_breaks_challenge.config(foreground=COLORS["text"])




    def create_dashboard(self):
        tab = ttk.Frame(self.notebook)
    
        # Header
        header = ttk.Frame(tab, style="Card.TFrame")
        header.pack(fill="x", padx=20, pady=10)
        
        # Left side: Title
        title_frame = ttk.Frame(header)
        title_frame.pack(side="left", padx=10)
        ttk.Label(title_frame, text="HealthGuard Pro", 
                font=("Segoe UI", 18, "bold"),
                foreground=COLORS["primary"]).pack()
        
        # Right side: Time and Date
        time_frame = ttk.Frame(header)
        time_frame.pack(side="right", padx=10)
        
        self.time_label = ttk.Label(time_frame,
                                font=("Segoe UI", 14),
                                foreground=COLORS["text"])
        self.time_label.pack(anchor="e")
        
        self.date_label = ttk.Label(time_frame,
                                font=("Segoe UI", 10),
                                foreground=COLORS["text"])
        self.date_label.pack(anchor="e")
        
        # Status cards
        status_frame = ttk.Frame(tab)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.time_active_label = self.create_status_card(status_frame, "Active Time", "0m")
        self.next_break_label = self.create_status_card(status_frame, "Next Break", "--:--")
        self.current_status_label = self.create_status_card(status_frame, "Current Status", "Working")
        
        # Progress bar
        progress_frame = ttk.Frame(tab, style="Card.TFrame")
        progress_frame.pack(fill="x", padx=20, pady=10)
        self.progress_bar = ttk.Progressbar(progress_frame, 
                                           orient="horizontal", 
                                           mode="determinate")
        self.progress_bar.pack(fill="x", padx=10, pady=10)
        self.progress_label = ttk.Label(progress_frame, 
                                      text="0% Complete", 
                                      font=("Segoe UI", 10), 
                                      foreground=COLORS["text"])
        self.progress_label.pack(pady=(0, 10))
        
        # Control buttons
        control_frame = ttk.Frame(tab)
        control_frame.pack(pady=20)
        
        self.pause_button = ttk.Button(control_frame, text="Pause", 
                                      style="Warning.TButton",
                                      command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Take Break Now", 
                  style="Primary.TButton",
                  command=self.trigger_break).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Snooze", 
                  style="Primary.TButton",
                  command=self.snooze_alert).pack(side="left", padx=5)
        
        return tab

    def create_status_card(self, parent, title, value):
        """Create a status card component"""
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(side="left", padx=10, ipadx=20, ipady=10)
        
        ttk.Label(frame, text=title, 
                 font=("Segoe UI", 10),
                 foreground=COLORS["text"]).pack()
        label = ttk.Label(frame, text=value,
                         font=("Segoe UI", 14, "bold"),
                         foreground=COLORS["primary"])
        label.pack(pady=(5, 0))
        return label

    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        
        # Break settings
        break_frame = ttk.LabelFrame(tab, text="Break Settings")
        break_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(break_frame, text="Work Duration (minutes):").grid(row=0, column=0, padx=10, pady=5)
        ttk.Spinbox(break_frame, from_=15, to=90, textvariable=self.work_interval).grid(row=0, column=1, padx=10)
        
        ttk.Label(break_frame, text="Break Duration (minutes):").grid(row=1, column=0, padx=10, pady=5)
        ttk.Spinbox(break_frame, from_=1, to=15, textvariable=self.break_duration).grid(row=1, column=1, padx=10)
        
        return tab

    def setup_settings_listeners(self):
        self.work_interval.trace_add("write", self.handle_settings_change)
        self.break_duration.trace_add("write", self.handle_settings_change)

    def handle_settings_change(self, *args):
        try:
            current_work = int(self.work_interval.get())
            current_break = int(self.break_duration.get())
        except ValueError:
            return
        if current_work != self.prev_work or current_break != self.prev_break:
            self.prev_work = current_work
            self.prev_break = current_break
            
            if self.app_state == "working":
                self.active_time = 0
                self.monitor.last_activity_time = time.time()
                # Update UI immediately
                self.time_active_label.config(text="0m")
                work_seconds = current_work * 60
                mins, secs = divmod(work_seconds, 60)
                self.next_break_label.config(text=f"{mins:02d}:{secs:02d}")
                self.progress_bar["value"] = 0
                self.progress_label.config(text="0% Complete")
                messagebox.showinfo("Settings Updated", 
                                  f"Work duration updated to {current_work} minutes. Timer reset.")
            elif self.app_state == "breaking":
                self.break_start_time = time.time()
                # Update UI immediately
                break_seconds = current_break * 60
                self.progress_bar["value"] = 0
                self.progress_label.config(text="0% Complete")
                mins, secs = divmod(break_seconds, 60)
                self.next_break_label.config(text=f"{mins:02d}:{secs:02d}")
                messagebox.showinfo("Settings Updated",
                                  f"Break duration updated to {current_break} minutes. Timer reset.")

    def toggle_pause(self):
        """Toggle pause state of the application"""
        self.paused = not self.paused
        if self.paused:
            self.pause_button.config(text="Resume")
            self.current_status_label.config(text="Paused", foreground=COLORS["highlight"])
        else:
            self.pause_button.config(text="Pause")
            status_text = "Working" if self.app_state == "working" else "On Break"
            color = COLORS["primary"] if self.app_state == "working" else COLORS["secondary"]
            self.current_status_label.config(text=status_text, foreground=color)


    def update_ui(self):
        """Update all UI elements including gamification"""
        current_time = time.time()
        
        if not self.paused:
            if self.app_state == "working" and current_time > self.snooze_until:
                self.update_working_state(current_time)
            elif self.app_state == "breaking":
                self.update_breaking_state(current_time)
        
        # Update time displays
        self.time_label.config(text=time.strftime("%H:%M"))
        self.date_label.config(text=time.strftime("%A, %d %B %Y"))
        
        # Update gamification panel
        self.update_gamification_display()
        
        self.after(1000, self.update_ui)

    def update_working_state(self, current_time):
        work_seconds = self.work_interval.get() * 60
        time_since_last_activity = current_time - self.monitor.last_activity_time
        
        if time_since_last_activity < IDLE_THRESHOLD:
            self.active_time += 1
        else:
            self.active_time = max(0, self.active_time - 1)
            
        progress = min((self.active_time / work_seconds) * 100, 100)
        self.progress_bar["value"] = progress
        self.progress_label.config(text=f"{int(progress)}% Complete")
        
        remaining = max(work_seconds - self.active_time, 0)
        mins, secs = divmod(remaining, 60)
        self.next_break_label.config(text=f"{mins:02d}:{secs:02d}")
        self.time_active_label.config(text=f"{self.active_time // 60}m")
        
        if self.active_time >= work_seconds:
            self.trigger_break()

    def update_breaking_state(self, current_time):
        break_seconds = self.break_duration.get() * 60
        elapsed = current_time - self.break_start_time
        remaining = max(break_seconds - elapsed, 0)
        
        mins, secs = divmod(int(remaining), 60)
        self.next_break_label.config(text=f"{mins:02d}:{secs:02d}")
        self.progress_bar["value"] = (elapsed / break_seconds) * 100
        self.progress_label.config(text=f"Break: {int((elapsed / break_seconds)*100)}% Complete")
        
        if remaining <= 0:
            self.end_break()

    def trigger_break(self):
        """Handle transition to break state with gamification rewards"""
        # Award points based on completed work duration (1 point per minute)
        points_earned = self.work_interval.get()
        self.gamification.add_points(points_earned)
        
        # Original break triggering logic
        self.app_state = "breaking"
        self.break_start_time = time.time()
        self.active_time = 0
        self.current_status_label.config(text="On Break", 
                                        foreground=COLORS["secondary"])
        self.show_break_alert()
        
        # Update points display immediately
        self.update_gamification_display()


    def snooze_alert(self):
        self.snooze_until = time.time() + 300  # 5 minutes
        self.active_time = 0
        messagebox.showinfo("Snoozed", "Break reminder postponed for 5 minutes")

    def check_audio_files(self):
        if not os.path.exists(self.break_sound):
            print("Warning: Break sound file not found!")
        if not os.path.exists(self.continue_sound):
            print("Warning: Continue sound file not found!")

    def activate_screensaver(self):
        try:
            # Windows screensaver activation
            ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF140, 0)
        except Exception as e:
            print(f"Error activating screensaver: {str(e)}")

    def deactivate_screensaver(self):
        try:
            # Windows screensaver deactivation
            ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF140, 2)
        except Exception as e:
            print(f"Error deactivating screensaver: {str(e)}")

    def play_sound(self, sound_file):
        try:
            if os.path.exists(sound_file):
                winsound.PlaySound(sound_file, winsound.SND_FILENAME)
        except Exception as e:
            print(f"Error playing sound: {str(e)}")

    def show_break_alert(self):
        self.break_alert = tk.Toplevel(self)
        self.break_alert.title("Break Time!")
        self.break_alert.geometry("300x200")
        
        # Activate screensaver and play sound
        self.activate_screensaver()
        self.play_sound(self.break_sound)
        
        ttk.Label(self.break_alert, text="Time to take a break!", 
                 font=("Segoe UI", 14, "bold")).pack(pady=10)
        activities = [
            "• Stretch your body",
            "• Look at distant objects",
            "• Drink some water",
            "• Take deep breaths"
        ]
        for activity in activities:
            ttk.Label(self.break_alert, text=activity).pack()
        ttk.Button(self.break_alert, text="End Break", 
                  command=lambda: [self.end_break(), self.break_alert.destroy()]).pack(pady=10)

    def end_break(self):
        """Handle break completion with gamification tracking"""
        # Record successful break completion
        self.gamification.record_break()
        
        # Original break ending logic
        if hasattr(self, 'break_alert') and self.break_alert.winfo_exists():
            self.break_alert.destroy()
        
        self.app_state = "working"
        self.current_status_label.config(text="Working", foreground=COLORS["primary"])
        self.monitor.last_activity_time = time.time()
        self.active_time = 0
        
        self.paused = True
        self.pause_button.config(text="Resume")
        self.current_status_label.config(text="Paused", foreground=COLORS["highlight"])
        self.show_continue_alert()
        
        # Update streak display immediately
        self.update_gamification_display()


    def show_continue_alert(self):
        # Deactivate screensaver before showing continue alert
        self.deactivate_screensaver()
        self.play_sound(self.continue_sound)
        
        self.continue_alert = tk.Toplevel(self)
        self.continue_alert.title("Continue Working")
        self.continue_alert.geometry("300x150")
        ttk.Label(self.continue_alert, text="Ready to continue working?", 
                 font=("Segoe UI", 12, "bold")).pack(pady=10)
        ttk.Button(self.continue_alert, text="Continue", style="Primary.TButton",
                  command=lambda: [self.toggle_pause(), self.continue_alert.destroy()]).pack(pady=10)

    def on_closing(self):
        self.monitor.stop()
        self.destroy()

if __name__ == "__main__":
    app = HealthAppUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
