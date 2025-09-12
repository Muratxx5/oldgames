SHOW_CONSOLE = 0  # Genel konsol çıktıları (aktif pencere vs.)

import threading
import sys
from pynput import mouse, keyboard
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import tkinter as tk

APP_NAME = "Touchpad & Numpad Listener"

class TrayManager:
    def __init__(self):
        self.icon = None

    def create_icon(self):
        img = Image.new('RGB', (32, 32), color=(0, 102, 204))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 24, 24), fill=(255, 255, 255))
        d.text((12, 8), "T", fill=(0, 102, 204))
        return img

    def update_tooltip(self, text):
        if self.icon is not None:
            self.icon.title = text

    def on_exit(self, icon, item):
        if SHOW_CONSOLE:
            print("Çıkış seçildi, program kapatılıyor...")
        stop_all_listeners()
        icon.stop()
        sys.exit(0)

    def on_settings(self, icon, item):
        def show_settings_window():
            settings_win = tk.Tk()
            settings_win.title("Ayarlar")
            settings_win.geometry("270x130")

            var_console = tk.IntVar(value=SHOW_CONSOLE)
            def on_toggle_console():
                global SHOW_CONSOLE
                SHOW_CONSOLE = var_console.get()

            tk.Label(settings_win, text="Konsol Görünürlüğü:").pack(pady=10)
            check_console = tk.Checkbutton(settings_win, text="Genel verileri konsolda göster", variable=var_console, command=on_toggle_console)
            check_console.pack()
            tk.Button(settings_win, text="Kapat", command=settings_win.destroy).pack(pady=15)
            settings_win.attributes('-topmost', True)
            settings_win.mainloop()

        threading.Thread(target=show_settings_window, daemon=True).start()

    def run(self):
        self.icon = Icon(
            APP_NAME,
            self.create_icon(),
            menu=Menu(
                MenuItem("Ayarlar", self.on_settings),
                MenuItem("Çıkış", self.on_exit)
            )
        )
        self.icon.title = APP_NAME
        self.icon.run()

tray_manager = TrayManager()
mouse_listener = None
keyboard_listener = None

def log_active_app_and_update_tray():
    try:
        import ctypes, psutil, win32gui, win32process
        hwnd = win32gui.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        active_title = buff.value if buff.value else "Bilinmeyen Uygulama"
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        exe_name = proc.name()
    except Exception:
        active_title = "Bilinmeyen Uygulama"
        exe_name = "Bilinmeyen.exe"
    info = f"{exe_name} | {active_title}"
    if SHOW_CONSOLE:
        print(f"[ACTIVE] {info}")
    tray_manager.update_tooltip(info)
def on_move(x, y):
    if SHOW_CONSOLE:
        print(f'[Touchpad] Mouse moved to ({x}, {y})')

def on_click(x, y, button, pressed):
    if SHOW_CONSOLE:
        print(f'[Touchpad] {button} {"pressed" if pressed else "released"} at ({x}, {y})')
    if pressed:
        log_active_app_and_update_tray()

def on_scroll(x, y, dx, dy):
    if SHOW_CONSOLE:
        print(f'[Touchpad] Scrolled at ({x}, {y}) by ({dx}, {dy})')
    if dx < 0:
        if SHOW_CONSOLE:
            print("[Gesture] Detected left scroll → Ctrl + Shift + B")
        with keyboard.Controller().pressed(keyboard.Key.ctrl):
            with keyboard.Controller().pressed(keyboard.Key.shift):
                keyboard.Controller().press('b')
                keyboard.Controller().release('b')
    elif dx > 0:
        if SHOW_CONSOLE:
            print("[Gesture] Detected right scroll → Ctrl + B")
        with keyboard.Controller().pressed(keyboard.Key.ctrl):
            keyboard.Controller().press('b')
            keyboard.Controller().release('b')

def on_key_press(key):
    if SHOW_CONSOLE:
        try:
            print(f'[Numpad] Key pressed: {key.char}')
        except AttributeError:
            print(f'[Numpad] Special key pressed: {key}')

def on_key_release(key):
    if SHOW_CONSOLE:
        try:
            print(f'[Numpad] Key released: {key.char}')
        except AttributeError:
            print(f'[Numpad] Special key released: {key}')

def stop_all_listeners():
    global mouse_listener, keyboard_listener
    if mouse_listener is not None:
        mouse_listener.stop()
    if keyboard_listener is not None:
        keyboard_listener.stop()

def start_mouse_listener():
    global mouse_listener
    mouse_listener = mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll)
    mouse_listener.start()
    mouse_listener.join()

def start_keyboard_listener():
    global keyboard_listener
    keyboard_listener = keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release)
    keyboard_listener.start()
    keyboard_listener.join()

def start_tray():
    tray_manager.run()

if __name__ == "__main__":
    mouse_thread = threading.Thread(target=start_mouse_listener, daemon=True)
    keyboard_thread = threading.Thread(target=start_keyboard_listener, daemon=True)
    tray_thread = threading.Thread(target=start_tray, daemon=True)

    mouse_thread.start()
    keyboard_thread.start()
    tray_thread.start()

    mouse_thread.join()
    keyboard_thread.join()
