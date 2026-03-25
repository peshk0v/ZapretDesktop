# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import requests
import zipfile
import io
import ctypes
import service as sv

# ----------------------------------------------------------------------
# Configs
# ----------------------------------------------------------------------
def getConf() -> dict:
    """Загружает основную конфигурацию из config.json."""
    with open(f"{sv.BASE_DIR}/config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def getdata() -> dict:
    """Загружает данные из data.json."""
    with open(f"{sv.BASE_DIR}/data.json", "r", encoding="utf-8") as f:
        return json.load(f)


def setdata(dta: dict) -> None:
    """Сохраняет данные в data.json."""
    with open(f"{sv.BASE_DIR}/data.json", "w", encoding="utf-8") as f:
        json.dump(dta, f)


def getservc() -> dict:
    """Возвращает список сервисов из services.json."""
    with open(f"{sv.BASE_DIR}/services.json", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Bypass
# ----------------------------------------------------------------------
def oblist() -> list:
    """Возвращает список имён доступных стратегий (без расширения .bat)."""
    lst = sv.service_control(7)
    return [i[:-4] for i in lst]


def getCurrent() -> str:
    """Возвращает текущую стратегию (с .bat)."""
    return sv.service_control(8)["strategy"]


def getObName() -> str:
    """Возвращает имя текущей стратегии без расширения."""
    return getCurrent()[:-4]


def setObName(nm: str) -> None:
    """Устанавливает стратегию по имени (добавляет .bat и сохраняет в конфиг)."""
    nmm = nm + ".bat"
    se = sv.service_control(8)
    se["strategy"] = nmm
    sv.service_control(9, se)


def zapStat() -> bool:
    """Возвращает статус работы zapret (запущен/остановлен)."""
    return sv.service_control(3)


# ----------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------
def getsets() -> dict:
    """Возвращает настройки из data.json."""
    dta = getdata()
    return dta["settings"]


def change_names(names: str | bool) -> int:
    """Преобразует строковое/булево значение в числовой код для service_control."""
    match names:
        case "loaded":
            return 2
        case "any":
            return 1
        case "none":
            return 0
        case True:
            return 1
        case False:
            return 0


def applysets() -> None:
    """Применяет текущие настройки IPSET и GameFilter к zapret."""
    sets = getsets()
    sv.service_control(13, change_names(sets["IPSET"]))
    sv.service_control(12, change_names(sets["GameFilter"]))


def savesets(sets: dict) -> None:
    """Сохраняет настройки и перезапускает сервис."""
    dta = getdata()
    dta["settings"] = sets
    setdata(dta)
    applysets()
    sv.service_control(6)


# ----------------------------------------------------------------------
# Services
# ----------------------------------------------------------------------
def merge_enabled_settings(old_path: str, new_path: str) -> None:
    """
    Переносит состояние Enabled из старого файла сервисов в новый.
    Используется при обновлении списка сервисов.
    """
    if os.path.exists(old_path):
        with open(old_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    else:
        old_data = []

    with open(new_path, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    old_enabled = {}
    for item in old_data:
        if isinstance(item, dict) and 'Name' in item and 'Enabled' in item:
            old_enabled[item['Name']] = item['Enabled']

    for item in new_data:
        if isinstance(item, dict) and 'Name' in item:
            name = item['Name']
            item['Enabled'] = old_enabled.get(name, False)

    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)


def applyservc() -> None:
    """
    Формирует файлы list-general.txt и list-exclude.txt на основе
    включённых сервисов.
    """
    cfg = getdata()
    servc = getservc()
    with open(f"{sv.BASE_DIR}/data/zapret-latest/lists/list-general.txt", "w") as lg:
        with open(f"{sv.BASE_DIR}/data/zapret-latest/lists/list-exclude.txt", "w") as ex:
            newlg = ""
            newex = cfg["baseExclude"]
            for i in servc:
                if i["Enabled"]:
                    for a in i["IPS"]:
                        newlg = newlg + a + "\n"
                    for b in i["Exclude"]:
                        newex = newex + "\n" + b
            ex.write(newex)
            lg.write(newlg)


def setservc(dta: list) -> bool:
    """
    Сохраняет состояния Enabled для сервисов из переданного списка.
    """
    serv = getservc()
    for idx, val in enumerate(dta):
        if idx < len(serv):
            serv[idx]["Enabled"] = val
    with open(f"{sv.BASE_DIR}/services.json", "w", encoding="utf-8") as file:
        json.dump(serv, file, indent=4)
    applyservc()
    return True


def updServc() -> bool:
    """
    Обновляет список сервисов из репозитория, сохраняя старые настройки Enabled.
    """
    os.rename(f"{sv.BASE_DIR}/services.json", f"{sv.BASE_DIR}/oldServices.json")
    new = requests.get("https://github.com/peshk0v/ZapretDesktop/raw/main/services.json")
    with open(f"{sv.BASE_DIR}/services.json", "wb") as file:
        for chunk in new.iter_content(chunk_size=8192):
            file.write(chunk)
    merge_enabled_settings(f"{sv.BASE_DIR}/oldServices.json", f"{sv.BASE_DIR}/services.json")
    os.remove(f"{sv.BASE_DIR}/oldServices.json")
    return True


# ----------------------------------------------------------------------
# Desktop
# ----------------------------------------------------------------------
def desktop(tf: bool) -> None:
    """Создаёт или удаляет .desktop файл для автозапуска GUI."""
    if tf:
        with open("ZAPRET.desktop", "w", encoding="utf-8") as z:
            fl = (
                f"[Desktop Entry]\n"
                f"Encoding=UTF-8\n"
                f"Version=0.1\n"
                f"Type=Application\n"
                f"Terminal=false\n"
                f"Exec={sv.BASE_DIR}/venv/bin/python3 {sv.BASE_DIR}/app.py\n"
                f"Name=ZAPRET\n"
                f"Icon={sv.BASE_DIR}/icon.png"
            )
            z.write(fl)
        os.system("mv ZAPRET.desktop ~/.local/share/applications/ZAPRET.desktop")
        os.system("update-desktop-database ~/.local/share/applications")
    else:
        os.system("rm ~/.local/share/applications/ZAPRET.desktop")
        os.system("update-desktop-database ~/.local/share/applications")


def downloadzapret(config: dict) -> None:
    """Скачивает и устанавливает zapret (используется при первом запуске)."""
    try:
        os.system("git clone https://github.com/Sergeydigl3/zapret-discord-youtube-linux.git data/")
    finally:
        os.system(f"{sv.BASE_DIR}/data/service.sh download-deps --default")
    applyservc()


def update_zapret() -> None:
    """Обновляет zapret: сохраняет conf.env, удаляет data/, скачивает заново, восстанавливает conf.env."""
    conf_env_path = f"{sv.BASE_DIR}/data/conf.env"
    
    conf_env_content = None
    if os.path.exists(conf_env_path):
        with open(conf_env_path, 'r') as f:
            conf_env_content = f.read()
    
    if os.path.exists(sv.DATA_DIR):
        import shutil
        shutil.rmtree(sv.DATA_DIR)
    
    os.system(f"git clone https://github.com/Sergeydigl3/zapret-discord-youtube-linux.git {sv.DATA_DIR}/")
    os.system(f"{sv.BASE_DIR}/data/service.sh download-deps --default")
    
    if conf_env_content:
        with open(conf_env_path, 'w') as f:
            f.write(conf_env_content)
    
    applysets()
    applyservc()
    sv.service_control(6)


def get_theme() -> dict:
    """Возвращает настройки темы из data.json."""
    dta = getdata()
    return dta.get("theme", {
        "angle": 135,
        "start": {"r": 102, "g": 126, "b": 234},
        "end": {"r": 118, "g": 75, "b": 162},
        "preset": None
    })


def save_theme(theme: dict) -> None:
    """Сохраняет настройки темы в data.json."""
    dta = getdata()
    dta["theme"] = theme
    setdata(dta)