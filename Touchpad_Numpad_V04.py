SHOW_CONSOLE = 0      # Genel konsol çıktıları (aktif pencere vs.)
SHOW_TOUCHPAD_DATA = 0 # Touchpad HID verileri konsolda görünsün mü?

import threading
import ctypes
import sys
import time
from pynput import mouse, keyboard
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import psutil
import win32gui
import win32process
import tkinter as tk

dll_path = r"C:\Users\kalip33\Documents\pydoc\hidapi-win\x64\hidapi.dll"
ctypes.CDLL(dll_path)
import hid

APP_NAME = "Touchpad & Numpad Listener"

class TrayManager:
    def __init__(self):
        self.icon = None
        self.lock = threading.Lock()

    def create_icon(self):
        img = Image.new('RGB', (32, 32), color=(0, 102, 204))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 24, 24), fill=(255, 255, 255))
        d.text((12, 8), "T", fill=(0, 102, 204))
        return img

    def update_tooltip(self, text):
        with self.lock:
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
            settings_win.geometry("270x180")

            var_console = tk.IntVar(value=SHOW_CONSOLE)
            var_touchpad = tk.IntVar(value=SHOW_TOUCHPAD_DATA)

            def on_toggle_console():
                global SHOW_CONSOLE
                SHOW_CONSOLE = var_console.get()

            def on_toggle_touchpad():
                global SHOW_TOUCHPAD_DATA
                SHOW_TOUCHPAD_DATA = var_touchpad.get()

            tk.Label(settings_win, text="Konsol Görünürlüğü:").pack(pady=10)
            check_console = tk.Checkbutton(settings_win, text="Genel verileri konsolda göster", variable=var_console, command=on_toggle_console)
            check_console.pack()

            tk.Label(settings_win, text="Touchpad HID Verisi:").pack(pady=5)
            check_touchpad = tk.Checkbutton(settings_win, text="Touchpad verisini konsolda göster", variable=var_touchpad, command=on_toggle_touchpad)
            check_touchpad.pack()

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

def get_active_window_title():
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value if buff.value else "Bilinmeyen Uygulama"

def get_active_app():
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        proc = psutil.Process(pid)
        return proc.name()
    except Exception:
        return "Bilinmeyen.exe"

def log_active_app_and_update_tray():
    active_app = get_active_app()
    active_title = get_active_window_title()
    info = f"{active_app} | {active_title}"
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

TOUCHPAD_VID = 0x5ac
TOUCHPAD_PID = 0x24f

def touchpad_hid_thread():
    device_info = None
    for d in hid.enumerate():
        if d['vendor_id'] == TOUCHPAD_VID and d['product_id'] == TOUCHPAD_PID:
            if SHOW_CONSOLE:
                print(f"Touchpad HID cihazı bulundu: {d}")
            device_info = d
            break

    if not device_info:
        if SHOW_CONSOLE:
            print("Touchpad HID cihazı bulunamadı!")
        return

    dev = hid.Device(vid=TOUCHPAD_VID, pid=TOUCHPAD_PID)

    if SHOW_CONSOLE:
        print(f"{device_info['product_string']} cihazından veri bekleniyor...")
    try:
        while True:
            data = dev.read(64)
            if data:
                if SHOW_TOUCHPAD_DATA:
                    print(f"[HID Touchpad] Veri: {data}")
                    if len(data) >= 3:
                        x_move = data[1]
                        y_move = data[2]
                        print(f"[HID Touchpad] Hareket: X={x_move}, Y={y_move}")
    except Exception as e:
        if SHOW_CONSOLE:
            print("Touchpad HID cihazında hata:", e)
    finally:
        dev.close()
        if SHOW_CONSOLE:
            print("Touchpad HID bağlantısı kapatıldı.")

if __name__ == "__main__":
    mouse_thread = threading.Thread(target=start_mouse_listener, daemon=True)
    keyboard_thread = threading.Thread(target=start_keyboard_listener, daemon=True)
    tray_thread = threading.Thread(target=start_tray, daemon=True)
    touchpad_thread = threading.Thread(target=touchpad_hid_thread, daemon=True)

    mouse_thread.start()
    keyboard_thread.start()
    tray_thread.start()
    touchpad_thread.start()

    mouse_thread.join()
    keyboard_thread.join()
