# -*- coding: utf-8 -*-

import os
import sys
import glob
import shutil
import urllib.request
import subprocess, getpass
from pathlib import Path
from typing import Optional, Union

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
ZAPRET_DIR = DATA_DIR / "zapret-latest"
BIN_DIR = ZAPRET_DIR / "bin"
LISTS_DIR = ZAPRET_DIR / "lists"
UTILS_DIR = ZAPRET_DIR / "utils"
SERVICE_PATH = DATA_DIR / "service.sh"
SUDO_PASSWORD = None
PASSWORD_CALLBACK = None
PASSWORD_FILE = Path(__file__).parent / ".sudo_pass"

# ----------------------------------------------------------------------
# Utilites
# ----------------------------------------------------------------------
def log(text: str, mode: int) -> None:
    """Выводит сообщение в консоль в зависимости от режима (0 - info, 1 - warning, 2 - error)."""
    match mode:
        case 0:
            print(f"[LOG] ~ {text}")
        case 1:
            print(f"[WARNING] ~ {text}")
        case 2:
            print(f"[ERROR] ~ {text}\n[PLEASE CREATE ISSULE ON GITHUB]")
    
    try:
        import eel
        eel.addLog(text, mode)()
    except:
        pass

def set_sudo_password(password):
    global SUDO_PASSWORD
    SUDO_PASSWORD = password

def set_password_callback(callback):
    global PASSWORD_CALLBACK
    PASSWORD_CALLBACK = callback

def get_sudo_password():
    global SUDO_PASSWORD
    if SUDO_PASSWORD is None and PASSWORD_CALLBACK is not None:
        SUDO_PASSWORD = PASSWORD_CALLBACK()
    return SUDO_PASSWORD

def run_cmd(cmd, input_data=None):
    """
    Выполняет команду и возвращает stdout (строка) при успехе, иначе False.
    Если передан input_data, он подаётся на stdin команды.
    """
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout
        else:
            log(f"Command failed: {' '.join(cmd)} - {result.stderr.strip()}", 2)
            return False
    except Exception as e:
        log(f"Exception running command: {e}", 2)
        return False

def run_cmd_sudo(cmd, input_data=None):
    password = get_sudo_password()
    if password is None:
        log("Sudo password not available, trying without sudo", 1)
        return run_cmd(cmd, input_data=input_data)
    full_cmd = ['sudo', '-S'] + cmd
    input_str = password + '\n'
    if input_data:
        input_str += input_data
    return run_cmd(full_cmd, input_data=input_str)

def run_service_cmd(args: list) -> str | bool:
    cmd = [str(SERVICE_PATH)] + args
    log(f"Service cmd run. Args: {args}", 0)
    return run_cmd_sudo(cmd)


def write_file(path: Path, content: str) -> None:
    """Записывает строковое содержимое в файл."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def download_file(url: str, dest: Path, timeout: int = 10) -> bool:
    """Скачивает файл по URL и сохраняет его в dest. Возвращает True при успехе."""
    try:
        req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                with open(dest, 'wb') as f:
                    f.write(response.read())
                return True
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}", file=sys.stderr)
    return False


# ----------------------------------------------------------------------
# IPSET
# ----------------------------------------------------------------------
def get_mode_ipset() -> str:
    """
    Определяет текущий режим ipset по содержимому ipset-all.txt:
    - "None"    : если файл содержит специальную заглушку 203.0.113.113/32
    - "Any"     : если файл пуст
    - "Loaded"  : если файл содержит реальные адреса
    - иначе сообщение о неподдерживаемой версии
    """
    if not ZAPRET_DIR:
        raise EnvironmentError("Переменная окружения ZAPRET_DIR не установлена")

    lists_dir = ZAPRET_DIR / "lists"
    ipset_path = lists_dir / "ipset-all.txt"

    if not lists_dir.is_dir():
        return "Текущая версия конфигураций не поддерживается"

    if not ipset_path.exists():
        ipset_path.touch()

    with open(ipset_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f if line.strip()]

    if any('203.0.113.113' in line for line in lines):
        return "None"
    elif len(lines) == 0:
        return "Any"
    else:
        return "Loaded"


def change_mode_ipset(mode: str) -> None:
    """
    Изменяет режим ipset:
    - "None"   : заменяет содержимое ipset-all.txt на заглушку
    - "Any"    : восстанавливает из бекапа (если есть)
    - "Loaded" : создаёт бекап и заполняет файл заглушкой
    """
    if not ZAPRET_DIR:
        raise EnvironmentError("Переменная окружения ZAPRET_DIR не установлена")

    lists_dir = ZAPRET_DIR / "lists"
    ipset_path = lists_dir / "ipset-all.txt"
    backup_path = lists_dir / "ipset-all.txt.backup"

    if mode == "Текущая версия конфигураций не поддерживается":
        raise ValueError("Текущая версия конфигураций не поддерживается. Для смены ipset режима следует поменять версию на более новую.")

    if mode == "None":
        if ipset_path.exists():
            ipset_path.unlink()
        ipset_path.touch()
        log(f"Выбранный режим IPSET - {get_mode_ipset()}", 0)
        return

    if mode == "Any":
        if backup_path.exists():
            if ipset_path.exists():
                ipset_path.unlink()
            shutil.copy2(backup_path, ipset_path)
            log(f"Выбранный режим IPSET - {get_mode_ipset()}", 0)
            return
        else:
            raise FileNotFoundError("Не найден бекап, переустановите zapret стратегии.")

    if backup_path.exists():
        backup_path.unlink()
    if ipset_path.exists():
        shutil.copy2(ipset_path, backup_path)

    with open(ipset_path, 'w', encoding='utf-8') as f:
        f.write("203.0.113.113/32\n")

    log(f"Выбранный режим IPSET - {get_mode_ipset()}", 0)


# ----------------------------------------------------------------------
# Status
# ----------------------------------------------------------------------
def is_service_running(service_name: str = "zapret-discord-youtube") -> bool:
    """
    Проверяет, запущен ли сервис zapret.
    """
    # Проверяем напрямую процесс nfqws
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'nfqws'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass

    # Проверяем через ps aux
    try:
        result = subprocess.run(
            "ps aux | grep -v grep | grep -q 'nfqws'",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # Проверяем systemd сервис
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass

    return False


def is_zapret_installed(service_names: list | str = None) -> bool:
    """
    Проверяет, установлен ли zapret как сервис (systemd, init.d или в PATH).
    По умолчанию ищет имена: zapret-discord-youtube, zapret, zapret-discord.
    """
    if service_names is None:
        service_names = ["zapret-discord-youtube", "zapret", "zapret-discord"]
    if isinstance(service_names, str):
        service_names = [service_names]

    systemd_paths = [
        '/etc/systemd/system',
        '/lib/systemd/system',
        '/usr/lib/systemd/system'
    ]
    for path in systemd_paths:
        if os.path.isdir(path):
            for name in service_names:
                unit_file = os.path.join(path, name + '.service')
                if os.path.isfile(unit_file):
                    return True
                if glob.glob(os.path.join(path, name + '*.service')):
                    return True

    try:
        result = subprocess.run(
            ['systemctl', 'list-unit-files', '--full', '--all'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            for name in service_names:
                for line in result.stdout.splitlines():
                    if line.startswith(name + '.service'):
                        return True
                cat_check = subprocess.run(
                    ['systemctl', 'cat', name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
                if cat_check.returncode == 0:
                    return True
    except FileNotFoundError:
        pass

    for name in service_names:
        init_script = os.path.join('/etc/init.d', name)
        if os.path.isfile(init_script) and os.access(init_script, os.X_OK):
            return True

    for name in service_names:
        for path_dir in os.environ.get('PATH', '').split(os.pathsep):
            full_path = os.path.join(path_dir, name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                return True

    extra_paths = ['/opt', '/usr/local/bin', '/usr/local/sbin']
    for base in extra_paths:
        for name in service_names:
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return True
            for f in glob.glob(os.path.join(base, '*' + name + '*')):
                if os.path.isfile(f) and os.access(f, os.X_OK):
                    return True

    return False


# ----------------------------------------------------------------------
# Main service controller
# ----------------------------------------------------------------------
def service_control(comd: int, args=None):
    """
    Управление zapret через команды:
    0  - запуск без установки сервиса
    1  - установка и запуск сервиса
    2  - удаление сервиса
    3  - проверка статуса (запущен/остановлен)
    4  - остановка сервиса
    5  - запуск сервиса
    6  - перезапуск сервиса
    7  - получение списка стратегий
    8  - получение текущей конфигурации (интерфейс, gamefilter, стратегия)
    9  - установка конфигурации (args = dict)
    10 - получение режима ipset
    11 - установка режима ipset (args = режим)
    12 - изменение gamefilter (args = 0/1)
    13 - изменение ipset (args = 0/1/2)
    14 - проверка установки сервиса (автозапуск)
    """
    match comd:
        case 0:
            run_service_cmd(["run", "--config", "conf.env"])
            log("ZAPRET STARTED WITHOUT SERVICE", 0)
            return True

        case 1:
            run_cmd_sudo([str(SERVICE_PATH), "service", "install"])
            log("ZAPRET INSTALLED WITH SERVICE AND RUN", 0)
            return True

        case 2:
            run_cmd_sudo([str(SERVICE_PATH), "service", "remove"])
            log("ZAPRET REMOVED WITH SERVICE", 0)
            return True

        case 3:
            return is_service_running()

        case 4:
            run_cmd_sudo([str(SERVICE_PATH), "service", "stop"])
            return True

        case 5:
            run_cmd_sudo([str(SERVICE_PATH), "service", "start"])
            return True

        case 6:
            run_cmd_sudo([str(SERVICE_PATH), "service", "restart"])
            return True

        case 7:
            cmd = run_service_cmd(["strategy", "list"])
            if not cmd:
                return []
            listc = cmd.split("\n")
            listc = [line for line in listc if line.strip() and 'Доступные стратегии:' not in line]
            return listc

        case 8:
            conf = run_service_cmd(["config", "show"])
            if not conf:
                return {"interface": "", "gamefilter": "", "strategy": ""}
            clines = conf.split("\n")
            celements = []
            for line in clines:
                if '=' in line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        celements.append((parts[0].strip(), parts[1].strip()))
            result = {}
            for key, val in celements:
                result[key] = val
            return result

        case 9:
            if args == "none":
                return False
            else:
                fl = f"interface={args['interface']}\ngamefilter={args['gamefilter']}\nstrategy={args['strategy']}"
                with open(f"{DATA_DIR}/conf.env", "w") as c:
                    c.write(fl)
                log("Config file rewritten!", 0)
                return True

        case 10:
            return get_mode_ipset()

        case 11:
            return change_mode_ipset(args)

        case 12:
            cfg = service_control(8)
            if args == 0:
                cfg["gamefilter"] = "false"
            else:
                cfg["gamefilter"] = "true"
            service_control(9, cfg)

        case 13:
            match args:
                case 0:
                    change_mode_ipset("Loaded")   # NONE
                case 1:
                    change_mode_ipset("None")     # ANY
                case 2:
                    change_mode_ipset("Any")      # LOADED

        case 14:
            return is_zapret_installed()