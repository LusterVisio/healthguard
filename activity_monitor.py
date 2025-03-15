import time
from threading import Thread
from pynput import keyboard, mouse
import win32gui
import mss
from PIL import Image, ImageChops
import numpy as np

class ActivityMonitor:
    def __init__(self, app):
        self.app = app
        self.last_activity_time = time.time()
        self.listener_running = True
        self.last_window = None
        self.last_screenshot = None
        
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
        from config import SCREEN_CHECK_INTERVAL
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
        from config import SCREEN_CHECK_INTERVAL
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