import tkinter as tk
from tkinter import ttk, messagebox
import time
import os
import ctypes
import winsound
from config import COLORS, DEFAULT_WORK_MINUTES, DEFAULT_BREAK_MINUTES, IDLE_THRESHOLD

class HealthAppUI(tk.Tk):
    def __init__(self, activity_monitor, gamification):
        super().__init__()
        self.title("HealthGuard Pro")
        self.geometry("1000x700")
        self.configure(bg=COLORS["background"])

        self.paused = False
        self.active_time = 0
        self.app_state = "working"
        self.break_start_time = 0
        self.snooze_until = 0

        self.work_interval = tk.IntVar(value=DEFAULT_WORK_MINUTES)
        self.break_duration = tk.IntVar(value=DEFAULT_BREAK_MINUTES)
        self.prev_work = DEFAULT_WORK_MINUTES
        self.prev_break = DEFAULT_BREAK_MINUTES

        self.break_sound = "break_alert.wav"
        self.continue_sound = "continue_alert.wav"
        self.check_audio_files()

        self.monitor = activity_monitor
        self.gamification = gamification

        self.setup_styles()
        self.create_widgets()
        self.setup_settings_listeners()
        self.update_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["background"])
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 5])
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"),
                       foreground="white", background=COLORS["primary"])
        style.configure("Warning.TButton", font=("Segoe UI", 10, "bold"),
                       foreground="white", background=COLORS["highlight"])
        style.configure("Card.TFrame", background="white", relief="raised", borderwidth=1)

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.dashboard_tab = self.create_dashboard()
        self.settings_tab = self.create_settings_tab()
        self.gamification_tab = self.create_gamification_tab()

        self.notebook.add(self.dashboard_tab, text=" Dashboard ")
        self.notebook.add(self.settings_tab, text=" Settings ")
        self.notebook.add(self.gamification_tab, text=" Gamification ")

    def create_dashboard(self):
        tab = ttk.Frame(self.notebook)
        header = ttk.Frame(tab, style="Card.TFrame")
        header.pack(fill="x", padx=20, pady=10)

        title_frame = ttk.Frame(header)
        title_frame.pack(side="left", padx=10)
        ttk.Label(title_frame, text="HealthGuard Pro", font=("Segoe UI", 18, "bold"),
                 foreground=COLORS["primary"]).pack()

        time_frame = ttk.Frame(header)
        time_frame.pack(side="right", padx=10)
        self.time_label = ttk.Label(time_frame, font=("Segoe UI", 14), foreground=COLORS["text"])
        self.time_label.pack(anchor="e")
        self.date_label = ttk.Label(time_frame, font=("Segoe UI", 10), foreground=COLORS["text"])
        self.date_label.pack(anchor="e")

        status_frame = ttk.Frame(tab)
        status_frame.pack(fill="x", padx=20, pady=10)
        self.time_active_label = self.create_status_card(status_frame, "Active Time", "0m")
        self.next_break_label = self.create_status_card(status_frame, "Next Break", "--:--")
        self.current_status_label = self.create_status_card(status_frame, "Current Status", "Working")

        progress_frame = ttk.Frame(tab, style="Card.TFrame")
        progress_frame.pack(fill="x", padx=20, pady=10)
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=10, pady=10)
        self.progress_label = ttk.Label(progress_frame, text="0% Complete", font=("Segoe UI", 10),
                                       foreground=COLORS["text"])
        self.progress_label.pack(pady=(0, 10))

        control_frame = ttk.Frame(tab)
        control_frame.pack(pady=20)
        self.pause_button = ttk.Button(control_frame, text="Pause", style="Warning.TButton",
                                      command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=5)
        ttk.Button(control_frame, text="Take Break Now", style="Primary.TButton",
                  command=self.trigger_break).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Snooze", style="Primary.TButton",
                  command=self.snooze_alert).pack(side="left", padx=5)

        return tab

    def create_status_card(self, parent, title, value):
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(side="left", padx=10, ipadx=20, ipady=10)
        ttk.Label(frame, text=title, font=("Segoe UI", 10), foreground=COLORS["text"]).pack()
        label = ttk.Label(frame, text=value, font=("Segoe UI", 14, "bold"), foreground=COLORS["primary"])
        label.pack(pady=(5, 0))
        return label

    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        break_frame = ttk.LabelFrame(tab, text="Break Settings")
        break_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(break_frame, text="Work Duration (minutes):").grid(row=0, column=0, padx=10, pady=5)
        ttk.Spinbox(break_frame, from_=15, to=90, textvariable=self.work_interval).grid(row=0, column=1, padx=10)
        ttk.Label(break_frame, text="Break Duration (minutes):").grid(row=1, column=0, padx=10, pady=5)
        ttk.Spinbox(break_frame, from_=1, to=15, textvariable=self.break_duration).grid(row=1, column=1, padx=10)

        return tab

    def create_gamification_tab(self):
        tab = ttk.Frame(self.notebook)
        points_frame = ttk.Frame(tab, style="Card.TFrame")
        points_frame.pack(fill="x", padx=20, pady=10, ipadx=10, ipady=10)
        ttk.Label(points_frame, text="Total Points", font=("Segoe UI", 12)).pack()
        self.points_label = ttk.Label(points_frame, text=str(self.gamification.data['points']),
                                    font=("Segoe UI", 24, "bold"), foreground=COLORS["primary"])
        self.points_label.pack(pady=5)

        streak_frame = ttk.Frame(tab, style="Card.TFrame")
        streak_frame.pack(fill="x", padx=20, pady=10, ipadx=10, ipady=10)
        ttk.Label(streak_frame, text="Current Streak", font=("Segoe UI", 12)).pack()
        self.streak_label = ttk.Label(streak_frame, text=f"{self.gamification.data['current_streak']} days",
                                     font=("Segoe UI", 18), foreground=COLORS["secondary"])
        self.streak_label.pack(pady=5)

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
        self.points_label.config(text=str(self.gamification.data['points']))
        streak_text = f"{self.gamification.data['current_streak']} days "
        streak_text += "🔥" * min(self.gamification.data['current_streak'], 3)
        self.streak_label.config(text=streak_text)

        points_challenge = self.gamification.data['challenges']['weekly_points']
        points_text = f"Earn {points_challenge['target']} points: {points_challenge['progress']}/{points_challenge['target']}"
        if points_challenge['completed']:
            points_text += " ✓"
        self.weekly_points_challenge.config(text=points_text, foreground=COLORS["secondary"] if points_challenge['completed'] else COLORS["text"])

        breaks_challenge = self.gamification.data['challenges']['weekly_breaks']
        breaks_text = f"Take {breaks_challenge['target']} breaks: {breaks_challenge['progress']}/{breaks_challenge['target']}"
        if breaks_challenge['completed']:
            breaks_text += " ✓"
        self.weekly_breaks_challenge.config(text=breaks_text, foreground=COLORS["secondary"] if breaks_challenge['completed'] else COLORS["text"])

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
                self.time_active_label.config(text="0m")
                work_seconds = current_work * 60
                mins, secs = divmod(work_seconds, 60)
                self.next_break_label.config(text=f"{mins:02d}:{secs:02d}")
                self.progress_bar["value"] = 0
                self.progress_label.config(text="0% Complete")
                messagebox.showinfo("Settings Updated", f"Work duration updated to {current_work} minutes. Timer reset.")
            elif self.app_state == "breaking":
                self.break_start_time = time.time()
                break_seconds = current_break * 60
                self.progress_bar["value"] = 0
                self.progress_label.config(text="0% Complete")
                mins, secs = divmod(break_seconds, 60)
                self.next_break_label.config(text=f"{mins:02d}:{secs:02d}")
                messagebox.showinfo("Settings Updated", f"Break duration updated to {current_break} minutes. Timer reset.")

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.config(text="Resume" if self.paused else "Pause")
        status_text = "Paused" if self.paused else ("Working" if self.app_state == "working" else "On Break")
        color = COLORS["highlight"] if self.paused else (COLORS["primary"] if self.app_state == "working" else COLORS["secondary"])
        self.current_status_label.config(text=status_text, foreground=color)

    def update_ui(self):
        current_time = time.time()
        if not self.paused:
            if self.app_state == "working" and current_time > self.snooze_until:
                self.update_working_state(current_time)
            elif self.app_state == "breaking":
                self.update_breaking_state(current_time)
        self.time_label.config(text=time.strftime("%H:%M"))
        self.date_label.config(text=time.strftime("%A, %d %B %Y"))
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
        points_earned = self.work_interval.get()
        self.gamification.add_points(points_earned)
        self.app_state = "breaking"
        self.break_start_time = time.time()
        self.active_time = 0
        self.current_status_label.config(text="On Break", foreground=COLORS["secondary"])
        self.show_break_alert()
        self.update_gamification_display()

    def snooze_alert(self):
        self.snooze_until = time.time() + 300
        self.active_time = 0
        messagebox.showinfo("Snoozed", "Break reminder postponed for 5 minutes")

    def check_audio_files(self):
        if not os.path.exists(self.break_sound):
            print("Warning: Break sound file not found!")
        if not os.path.exists(self.continue_sound):
            print("Warning: Continue sound file not found!")

    def activate_screensaver(self):
        try:
            ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF140, 0)
        except Exception as e:
            print(f"Error activating screensaver: {str(e)}")

    def deactivate_screensaver(self):
        try:
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
        self.activate_screensaver()
        self.play_sound(self.break_sound)
        ttk.Label(self.break_alert, text="Time to take a break!", font=("Segoe UI", 14, "bold")).pack(pady=10)
        activities = ["• Stretch your body", "• Look at distant objects", "• Drink some water", "• Take deep breaths"]
        for activity in activities:
            ttk.Label(self.break_alert, text=activity).pack()
        ttk.Button(self.break_alert, text="End Break", command=lambda: [self.end_break(), self.break_alert.destroy()]).pack(pady=10)

    def end_break(self):
        self.gamification.record_break()
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
        self.update_gamification_display()

    def show_continue_alert(self):
        self.deactivate_screensaver()
        self.play_sound(self.continue_sound)
        self.continue_alert = tk.Toplevel(self)
        self.continue_alert.title("Continue Working")
        self.continue_alert.geometry("300x150")
        ttk.Label(self.continue_alert, text="Ready to continue working?", font=("Segoe UI", 12, "bold")).pack(pady=10)
        ttk.Button(self.continue_alert, text="Continue", style="Primary.TButton",
                  command=lambda: [self.toggle_pause(), self.continue_alert.destroy()]).pack(pady=10)

    def on_closing(self):
        self.monitor.stop()
        self.destroy()