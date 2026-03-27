# -*- coding: utf-8 -*-

import eel
import service as sv
import functions as fn
import threading, subprocess
import os
import json
import shutil

eel.init(f"{sv.BASE_DIR}/web")
sudo_password = None
password_event = threading.Event()
PASSWORD_FILE = sv.PASSWORD_FILE
BGS_FILE = f"{sv.BASE_DIR}/web/style/content/backgrounds/bgs.json"

# ----------------------------------------------------------------------
# Password handling
# ----------------------------------------------------------------------
def _get_saved_password():
    """Внутренняя функция для чтения пароля из файла."""
    try:
        if PASSWORD_FILE.exists():
            with open(PASSWORD_FILE, 'r') as f:
                return f.read().strip()
    except:
        pass
    return None

def _save_sudo_password(password):
    """Внутренняя функция для сохранения пароля в файл."""
    try:
        with open(PASSWORD_FILE, 'w') as f:
            f.write(password)
        os.chmod(PASSWORD_FILE, 0o600)
        return True
    except:
        return False

def get_sudo_password_callback():
    global sudo_password
    if sudo_password is None:
        saved = _get_saved_password()
        if saved:
            sudo_password = saved
            sv.set_sudo_password(saved)
    return sudo_password

sv.set_password_callback(get_sudo_password_callback)

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------
@eel.expose
def get_obname() -> str:
    return fn.getObName()

@eel.expose
def get_status() -> bool:
    return fn.zapStat()

@eel.expose
def start_zapret() -> bool:
    sv.service_control(1)
    return get_status()

@eel.expose
def stop_zapret() -> bool:
    sv.service_control(4)
    return get_status()

@eel.expose
def get_oblist() -> list:
    return fn.oblist()

@eel.expose
def set_obname(name: str) -> bool:
    fn.setObName(name)
    return True

@eel.expose
def getservc() -> dict:
    return fn.getservc()

@eel.expose
def astrt(tf: bool) -> None:
    if tf:
        sv.service_control(1)
    else:
        sv.service_control(2)

@eel.expose
def setservc(data: list) -> bool:
    fn.setservc(data)
    return True

@eel.expose
def updServc() -> bool:
    return fn.updServc()

@eel.expose
def update_zapret() -> None:
    fn.update_zapret()

@eel.expose
def getsets() -> dict:
    return fn.getsets()

@eel.expose
def savesets(sets: dict) -> None:
    fn.savesets(sets)

@eel.expose
def get_autostart_status() -> bool:
    return sv.service_control(14)

@eel.expose
def get_saved_password():
    """EEL-функция для получения пароля из файла."""
    return _get_saved_password()

@eel.expose
def save_sudo_password(password):
    """EEL-функция для сохранения пароля в файл."""
    return _save_sudo_password(password)

@eel.expose
def set_sudo_password(password):
    """EEL-функция для установки пароля в памяти и разблокировки ожидания."""
    global sudo_password
    sudo_password = password
    sv.set_sudo_password(password)
    password_event.set()
    return True

@eel.expose
def test_sudo():
    """Проверяет, работает ли сохранённый пароль sudo."""
    password = get_sudo_password_callback()
    if password:
        try:
            result = subprocess.run(
                ['sudo', '-S', 'echo', 'test'],
                input=password + '\n',
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() == 'test'
        except:
            pass
    return False

@eel.expose
def get_theme() -> dict:
    return fn.get_theme()

@eel.expose
def save_theme(theme: dict) -> None:
    fn.save_theme(theme)

@eel.expose
def add_log(text: str, mode: int):
    """Мост для передачи логов из Python в JavaScript."""
    pass

@eel.expose
def get_backgrounds():
    """Возвращает список обоев из bgs.json."""
    try:
        with open(BGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'Ошибка загрузки обоев: {e}')
        return []

@eel.expose
def add_background(filename: str, name: str, color: list):
    """Добавляет новые обои."""
    try:
        dest_filename = os.path.basename(filename)
        dest_path = f"{sv.BASE_DIR}/web/style/content/backgrounds/{dest_filename}"
        
        if os.path.exists(filename) and not os.path.exists(dest_path):
            shutil.copy2(filename, dest_path)
        
        with open(BGS_FILE, 'r', encoding='utf-8') as f:
            backgrounds = json.load(f)
        
        backgrounds.append({
            "Name": name,
            "File": dest_filename,
            "Color": color
        })
        
        with open(BGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(backgrounds, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f'Ошибка добавления обоев: {e}')
        return False

@eel.expose
def edit_background_color(index: int, color: list):
    """Изменяет акцентный цвет обоев."""
    try:
        with open(BGS_FILE, 'r', encoding='utf-8') as f:
            backgrounds = json.load(f)
        
        if 0 <= index < len(backgrounds):
            backgrounds[index]["Color"] = color
            
            with open(BGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(backgrounds, f, indent=4, ensure_ascii=False)
            
            return True
        return False
    except Exception as e:
        print(f'Ошибка изменения цвета: {e}')
        return False

@eel.expose
def select_background_file():
    """Открывает диалог выбора файла (Linux)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")]
        )
        
        root.destroy()
        
        return file_path if file_path else None
    except Exception as e:
        print(f'Ошибка выбора файла: {e}')
        return None

# ----------------------------------------------------------------------
# Start GUI
# ----------------------------------------------------------------------
eel.start('index.html', mode="firefox")