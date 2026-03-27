import requests, io, os, zipfile
import functions as fn
import service
import eel
import service as sv
import json
import shutil

config = fn.getConf()
print(fn.getCurrent())
if not os.path.exists("data"): os.mkdir("data")
if not any(os.scandir('data/')):
    fn.downloadzapret(fn.getConf())
else: print(f"Zapret Installed")

eel.init('web')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BGS_FILE = f"{BASE_DIR}/web/style/content/backgrounds/bgs.json"

@eel.expose
def get_obname():
    return fn.getObName()

@eel.expose
def get_status():
    return fn.zapStat()

@eel.expose
def start_zapret():
    fn.setAutostart(True)
    return get_status()

@eel.expose
def stop_zapret():
    fn.setAutostart(False)
    return get_status()

@eel.expose
def get_oblist():
    return fn.oblist()

@eel.expose
def set_obname(name):
    fn.setObName(name)
    return True

@eel.expose
def getservc():
    return fn.getservc()

@eel.expose
def astrt(tf):
    sv.set_autostart(tf)

@eel.expose
def setservc(data):
    fn.setservc(data)
    return True

@eel.expose
def updServc():
    return fn.updServc()

@eel.expose
def getsets():
    return fn.getsets()

@eel.expose
def savesets(sets):
    fn.savesets(sets)

@eel.expose
def get_theme():
    return fn.get_theme()

@eel.expose
def save_theme(theme):
    fn.save_theme(theme)

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
        dest_path = f"{BASE_DIR}/web/style/content/backgrounds/{dest_filename}"
        
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
    """Открывает диалог выбора файла (Windows)."""
    try:
        from tkinter import Tk, filedialog
        
        root = Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        
        file_path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")]
        )
        
        root.destroy()
        
        return file_path if file_path else None
    except Exception as e:
        print(f'Ошибка выбора файла: {e}')
        return None

eel.start('index.html', mode=fn.getMode(), size=(495, 270))