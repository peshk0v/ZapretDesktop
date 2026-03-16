"""
Модуль для управления службой zapret (полная замена service.bat).
Все функции не требуют наличия service.bat и реализованы на Python.
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import urllib.error
import winreg
import tempfile
import time
import ctypes
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Union, Any

# Константы
LOCAL_VERSION = "1.9.7b"

GITHUB_VERSION_URL = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/main/.service/version.txt"
GITHUB_RELEASE_URL = "https://github.com/Flowseal/zapret-discord-youtube/releases/tag/"
GITHUB_DOWNLOAD_URL = "https://github.com/Flowseal/zapret-discord-youtube/releases/latest"
IPSET_URL = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/ipset-service.txt"
HOSTS_URL = "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/hosts"

SERVICE_ZAPRET = "zapret"
SERVICE_WINDIVERT = "WinDivert"
SERVICE_WINDIVERT14 = "WinDivert14"

GAME_FILTER_FILE = "game_filter.enabled"
CHECK_UPDATES_FILE = "check_updates.enabled"

# Определение путей: предполагаем, что этот файл лежит в корневой папке проекта,
# а подпапки data, bin, lists, utils находятся рядом.
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
BIN_DIR = DATA_DIR / "bin"
LISTS_DIR = DATA_DIR / "lists"
UTILS_DIR = DATA_DIR / "utils"

# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------
def is_admin() -> bool:
    """Проверка, запущен ли процесс с правами администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return True

def require_admin():
    """Если не администратор, выбрасывает исключение."""
    if not is_admin():
        raise PermissionError("Это действие требует прав администратора. Запустите приложение от имени администратора.")

def run_cmd(cmd: list, capture_output: bool = False, input_data: Optional[str] = None) -> subprocess.CompletedProcess:
    """Запускает внешнюю команду и возвращает результат."""
    encoding = 'cp866' if sys.platform == 'win32' else 'utf-8'
    try:
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            input=input_data,
            encoding=encoding,
            check=False
        )
    except Exception as e:
        print(f"Ошибка выполнения команды {' '.join(cmd)}: {e}", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, returncode=-1, stderr=str(e))

def ensure_dir(path: Path) -> None:
    """Создаёт каталог, если не существует."""
    path.mkdir(parents=True, exist_ok=True)

def read_file_lines(path: Path) -> List[str]:
    """Читает файл и возвращает список строк (без символов новой строки)."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return []

def write_file(path: Path, content: str) -> None:
    """Записывает строку в файл."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def download_file(url: str, dest: Path, timeout: int = 10) -> bool:
    """Скачивает файл по URL и сохраняет в dest. Возвращает True при успехе."""
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

def check_extracted() -> bool:
    """Проверяет, распакован ли zapret (наличие папки bin)."""
    return BIN_DIR.exists()

def service_query_status(service_name: str) -> Optional[str]:
    """
    Возвращает состояние службы Windows: "RUNNING", "STOPPED", "STOP_PENDING" и т.п.
    Если служба не найдена, возвращает None.
    """
    result = run_cmd(["sc", "query", service_name], capture_output=True)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "STATE" in line:
            parts = line.split()
            if len(parts) >= 4:
                return parts[3].strip()
    return None

def service_delete(service_name: str) -> bool:
    """Останавливает и удаляет службу, если она существует. Возвращает True при успехе или если службы нет."""
    if service_query_status(service_name) is None:
        return True
    run_cmd(["net", "stop", service_name], capture_output=True)
    result = run_cmd(["sc", "delete", service_name], capture_output=True)
    return result.returncode == 0

def kill_process_by_name(proc_name: str) -> None:
    """Завершает все процессы с заданным именем, подавляя вывод."""
    subprocess.run(
        ["taskkill", "/IM", proc_name, "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def tcp_enable() -> bool:
    """Включает TCP timestamps, если они отключены. Возвращает True, если они включены или были включены."""
    result = run_cmd(["netsh", "interface", "tcp", "show", "global"], capture_output=True)
    if result.returncode != 0:
        return False
    if "timestamps" in result.stdout.lower() and "enabled" in result.stdout.lower():
        return True
    # Включаем
    res = run_cmd(["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"])
    return res.returncode == 0

def load_user_lists() -> None:
    """Создаёт примеры пользовательских списков, если они отсутствуют."""
    ensure_dir(LISTS_DIR)
    examples = {
        "ipset-exclude-user.txt": "203.0.113.113/32",
        "list-general-user.txt": "domain.example.abc",
        "list-exclude-user.txt": "domain.example.abc",
    }
    for fname, content in examples.items():
        path = LISTS_DIR / fname
        if not path.exists():
            write_file(path, content + "\n")

# ----------------------------------------------------------------------
# Работа с игровым фильтром
# ----------------------------------------------------------------------
def get_game_filter_params() -> Tuple[str, str, str]:
    """
    Возвращает значения подстановок GameFilter, GameFilterTCP, GameFilterUDP
    в зависимости от содержимого файла game_filter.enabled в папке utils.
    Возвращает (GameFilter, GameFilterTCP, GameFilterUDP).
    """
    flag_file = UTILS_DIR / GAME_FILTER_FILE
    if not flag_file.exists():
        return "12", "12", "12"
    mode = read_file_lines(flag_file)
    mode = mode[0].strip().lower() if mode else ""
    if mode == "all":
        return "1024-65535", "1024-65535", "1024-65535"
    elif mode == "tcp":
        return "1024-65535", "1024-65535", "12"
    elif mode == "udp":
        return "1024-65535", "12", "1024-65535"
    else:
        return "12", "12", "12"

def game_switch_status() -> str:
    """Возвращает состояние игрового фильтра: "disabled", "all", "tcp", "udp"."""
    flag_file = UTILS_DIR / GAME_FILTER_FILE
    if not flag_file.exists():
        return "disabled"
    mode = read_file_lines(flag_file)
    return mode[0].strip().lower() if mode else "disabled"

def game_switch(mode: str) -> None:
    """
    Устанавливает режим игрового фильтра.
    mode: "disable", "all", "tcp", "udp".
    """
    require_admin()
    flag_file = UTILS_DIR / GAME_FILTER_FILE
    ensure_dir(flag_file.parent)
    if mode == "disable":
        if flag_file.exists():
            flag_file.unlink()
    elif mode in ("all", "tcp", "udp"):
        write_file(flag_file, mode + "\n")
    else:
        raise ValueError(f"Недопустимый режим: {mode}")
    print("Перезапустите zapret, чтобы изменения вступили в силу.")

# ----------------------------------------------------------------------
# Автоматическая проверка обновлений
# ----------------------------------------------------------------------
def check_updates_switch_status() -> bool:
    """Возвращает True, если автоматическая проверка обновлений включена."""
    return (UTILS_DIR / CHECK_UPDATES_FILE).exists()

def check_updates_switch(enable: bool) -> None:
    """Включает или отключает автоматическую проверку обновлений."""
    require_admin()
    flag_file = UTILS_DIR / CHECK_UPDATES_FILE
    ensure_dir(flag_file.parent)
    if enable:
        if not flag_file.exists():
            write_file(flag_file, "ENABLED\n")
    else:
        if flag_file.exists():
            flag_file.unlink()

# ----------------------------------------------------------------------
# IPSet управление
# ----------------------------------------------------------------------
def ipset_switch_status() -> str:
    """
    Определяет состояние ipset-фильтра:
    - "loaded" - загружен нормальный список
    - "none" - список содержит только заглушку 203.0.113.113/32
    - "any" - пустой список (разрешены все)
    """
    list_file = LISTS_DIR / "ipset-all.txt"
    if not list_file.exists():
        return "any"
    lines = read_file_lines(list_file)
    if not lines:
        return "any"
    if len(lines) == 1 and lines[0].strip() == "203.0.113.113/32":
        return "none"
    return "loaded"

def set_ipset_mode(mode: str) -> bool:
    """
    Устанавливает желаемый режим ipset-фильтра.
    mode: "loaded", "none", "any"
    Возвращает True при успехе, False при ошибке.
    """
    require_admin()
    valid_modes = ["loaded", "none", "any"]
    if mode not in valid_modes:
        raise ValueError(f"Режим должен быть одним из {valid_modes}")

    list_file = LISTS_DIR / "ipset-all.txt"
    backup_file = list_file.with_suffix(".txt.backup")
    current = ipset_switch_status()

    print(f"Переключение ipset-фильтра: {current} -> {mode}")

    if mode == "loaded":
        if backup_file.exists():
            if list_file.exists():
                list_file.unlink()
            backup_file.rename(list_file)
            print("Режим loaded: восстановлен из резервной копии.")
            return True
        else:
            print("Ошибка: нет резервной копии для восстановления.")
            return False

    elif mode == "none":
        # Если текущий loaded и backup нет, создаём backup
        if current == "loaded" and not backup_file.exists():
            list_file.rename(backup_file)
        write_file(list_file, "203.0.113.113/32\n")
        print("Режим none установлен.")
        return True

    elif mode == "any":
        # Создаём пустой файл (или очищаем)
        if list_file.exists():
            list_file.write_text("", encoding='utf-8')
        else:
            list_file.touch()
        print("Режим any установлен.")
        return True

def ipset_switch() -> bool:
    """
    Циклическое переключение режимов: loaded -> none -> any -> loaded.
    Возвращает True при успехе.
    """
    current = ipset_switch_status()
    if current == "loaded":
        return set_ipset_mode("none")
    elif current == "none":
        return set_ipset_mode("any")
    elif current == "any":
        return set_ipset_mode("loaded")
    else:
        print(f"Неизвестный текущий режим: {current}")
        return False

# ----------------------------------------------------------------------
# Обновление ipset-списка
# ----------------------------------------------------------------------
def ipset_update() -> bool:
    """Обновляет ipset-all.txt из репозитория. Возвращает True при успехе."""
    require_admin()
    list_file = LISTS_DIR / "ipset-all.txt"
    ensure_dir(list_file.parent)
    success = download_file(IPSET_URL, list_file)
    if success:
        print("ipset-all.txt успешно обновлён.")
    else:
        print("Не удалось обновить ipset-all.txt.")
    return success

# ----------------------------------------------------------------------
# Обновление hosts-файла
# ----------------------------------------------------------------------
def hosts_update(auto_replace: bool = False) -> bool:
    """
    Проверяет актуальность системного hosts-файла.
    Если auto_replace=True, автоматически заменяет содержимое hosts на версию из репозитория.
    Возвращает True, если файл обновлён или уже актуален.
    """
    require_admin()
    hosts_file = Path(os.environ['SystemRoot']) / "System32" / "drivers" / "etc" / "hosts"
    temp_file = Path(tempfile.gettempdir()) / "zapret_hosts.txt"

    if not download_file(HOSTS_URL, temp_file):
        print("Не удалось загрузить hosts из репозитория.")
        return False

    downloaded_lines = read_file_lines(temp_file)
    if not downloaded_lines:
        return False
    first_line = downloaded_lines[0].strip()
    last_line = downloaded_lines[-1].strip()

    # Проверяем наличие этих строк в текущем hosts
    if hosts_file.exists():
        current_lines = read_file_lines(hosts_file)
        found_first = any(first_line in line for line in current_lines)
        found_last = any(last_line in line for line in current_lines)
        if found_first and found_last:
            temp_file.unlink(missing_ok=True)
            print("Hosts-файл уже актуален.")
            return True

    # Нужно обновление
    if auto_replace:
        backup = hosts_file.with_suffix(".bak")
        if not backup.exists():
            shutil.copy2(hosts_file, backup)
        shutil.copy2(temp_file, hosts_file)
        temp_file.unlink(missing_ok=True)
        print("Hosts-файл обновлён.")
        return True
    else:
        print("Hosts-файл требует обновления.")
        print(f"Скачанный файл сохранён как {temp_file}")
        return False

# ----------------------------------------------------------------------
# Проверка обновлений программы
# ----------------------------------------------------------------------
def service_check_updates(soft: bool = False) -> Optional[str]:
    """
    Проверяет наличие новой версии на GitHub.
    Возвращает строку с новой версией, если она доступна, иначе None.
    Если soft=True, то при ошибке просто возвращает None.
    """
    try:
        req = urllib.request.Request(GITHUB_VERSION_URL, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                github_version = response.read().decode('utf-8').strip()
                if github_version != LOCAL_VERSION:
                    return github_version
                else:
                    return None
            else:
                if not soft:
                    print("Не удалось получить информацию о версии.")
                return None
    except Exception as e:
        if not soft:
            print(f"Ошибка при проверке обновлений: {e}")
        return None

def check_updates(soft: bool = False) -> Optional[str]:
    """Публичная функция для проверки обновлений."""
    return service_check_updates(soft)

# ----------------------------------------------------------------------
# Диагностика системы
# ----------------------------------------------------------------------
def service_diagnostics() -> Dict[str, Union[bool, str, List[str]]]:
    """
    Выполняет диагностику системы и возвращает словарь с результатами проверок.
    Не выполняет автоматических исправлений, только возвращает информацию.
    """
    result = {}

    # 1. Base Filtering Engine
    bfe_status = service_query_status("BFE")
    result['bfe_running'] = (bfe_status == "RUNNING")

    # 2. Прокси
    proxy_enabled = False
    proxy_server = ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            value, _ = winreg.QueryValueEx(key, "ProxyEnable")
            proxy_enabled = bool(value)
            if proxy_enabled:
                proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except FileNotFoundError:
        pass
    result['proxy_enabled'] = proxy_enabled
    if proxy_enabled:
        result['proxy_server'] = proxy_server

    # 3. TCP timestamps
    ts_check = run_cmd(["netsh", "interface", "tcp", "show", "global"], capture_output=True)
    result['tcp_timestamps_enabled'] = "timestamps" in ts_check.stdout.lower() and "enabled" in ts_check.stdout.lower()

    # 4. Adguard процесс
    adguard_check = run_cmd(["tasklist", "/FI", "IMAGENAME eq AdguardSvc.exe"], capture_output=True)
    result['adguard_running'] = "AdguardSvc.exe" in adguard_check.stdout

    # 5. Killer службы
    sc_query_out = run_cmd(["sc", "query"], capture_output=True).stdout
    result['killer_found'] = "Killer" in sc_query_out

    # 6. Intel Connectivity
    result['intel_found'] = "Intel" in sc_query_out and "Connectivity" in sc_query_out and "Network" in sc_query_out

    # 7. Check Point
    checkpoint_found = False
    for svc in ["TracSrvWrapper", "EPWD"]:
        if run_cmd(["sc", "query", svc], capture_output=True).returncode == 0:
            checkpoint_found = True
            break
    result['checkpoint_found'] = checkpoint_found

    # 8. SmartByte
    result['smartbyte_found'] = "SmartByte" in sc_query_out

    # 9. WinDivert64.sys
    result['windivert_sys_exists'] = any(BIN_DIR.glob("*.sys"))

    # 10. VPN службы
    vpn_services = []
    for line in sc_query_out.splitlines():
        if "VPN" in line:
            parts = line.split()
            if len(parts) > 1:
                vpn_services.append(parts[1])
    result['vpn_services'] = vpn_services

    # 11. DNS (DoH)
    doh_count = 0
    try:
        key_path = r"SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as base_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(base_key, i)
                    with winreg.OpenKey(base_key, subkey_name) as subkey:
                        try:
                            flags, _ = winreg.QueryValueEx(subkey, "DohFlags")
                            if flags > 0:
                                doh_count += 1
                        except FileNotFoundError:
                            pass
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    result['doh_configured'] = (doh_count > 0)

    # 12. Проверка hosts на youtube
    hosts_file = Path(os.environ['SystemRoot']) / "System32" / "drivers" / "etc" / "hosts"
    yt_in_hosts = False
    if hosts_file.exists():
        with open(hosts_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            if "youtube.com" in content or "yotou.be" in content:
                yt_in_hosts = True
    result['youtube_in_hosts'] = yt_in_hosts

    # 13. Конфликт WinDivert
    winws_running = "winws.exe" in run_cmd(["tasklist", "/FI", "IMAGENAME eq winws.exe"], capture_output=True).stdout
    windivert_running = (service_query_status(SERVICE_WINDIVERT) == "RUNNING")
    result['winws_running'] = winws_running
    result['windivert_running'] = windivert_running

    # 14. Конфликтующие службы
    conflicting_services = ["GoodbyeDPI", "discordfix_zapret", "winws1", "winws2"]
    found_conflicts = []
    for svc in conflicting_services:
        if service_query_status(svc) is not None:
            found_conflicts.append(svc)
    result['conflicting_services'] = found_conflicts

    return result

# ----------------------------------------------------------------------
# Управление службами
# ----------------------------------------------------------------------
def service_status() -> Dict[str, any]:
    """Возвращает структурированную информацию о состоянии служб."""
    info = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Services\zapret") as key:
            strategy, _ = winreg.QueryValueEx(key, "zapret-discord-youtube")
            info['strategy'] = strategy
    except FileNotFoundError:
        info['strategy'] = None

    info['zapret_service'] = service_query_status(SERVICE_ZAPRET)
    info['windivert_service'] = service_query_status(SERVICE_WINDIVERT)
    info['windivert14_service'] = service_query_status(SERVICE_WINDIVERT14)
    info['windivert_sys_exists'] = any(BIN_DIR.glob("*.sys"))

    proc_check = run_cmd(["tasklist", "/FI", "IMAGENAME eq winws.exe"], capture_output=True)
    info['winws_running'] = "winws.exe" in proc_check.stdout

    return info

def service_remove() -> bool:
    """
    Полностью удаляет службу zapret, останавливает процесс winws.exe.
    Возвращает True при успешном удалении.
    """
    require_admin()
    print("Удаление службы zapret...")

    # Останавливаем и удаляем zapret
    service_delete(SERVICE_ZAPRET)
    kill_process_by_name("winws.exe")

    # Удаляем WinDivert (если есть и не используется другими)
    if service_query_status(SERVICE_WINDIVERT) is not None:
        run_cmd(["net", "stop", SERVICE_WINDIVERT], capture_output=True)
        run_cmd(["sc", "delete", SERVICE_WINDIVERT], capture_output=True)
    if service_query_status(SERVICE_WINDIVERT14) is not None:
        run_cmd(["net", "stop", SERVICE_WINDIVERT14], capture_output=True)
        run_cmd(["sc", "delete", SERVICE_WINDIVERT14], capture_output=True)

    print("Служба zapret удалена.")
    return True

def _extract_winws_args(strategy_path: Path) -> List[str]:
    """
    Извлекает аргументы командной строки для winws.exe из файла стратегии.
    Учитывает многострочные команды с символом продолжения '^'.
    """
    content = strategy_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.splitlines()

    # Собираем многострочную команду, начиная с первой строки, содержащей winws.exe
    full_line = ""
    in_continuation = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('::') or stripped.startswith('rem '):
            continue
        if 'winws.exe' in line or in_continuation:
            if stripped.endswith('^'):
                full_line += stripped[:-1] + ' '
                in_continuation = True
            else:
                full_line += stripped
                break

    if not full_line:
        raise ValueError("Не найдена строка с winws.exe в файле стратегии")

    # Находим позицию winws.exe
    idx = full_line.lower().find('winws.exe')
    if idx == -1:
        raise ValueError("Не удалось найти winws.exe в строке")
    args_str = full_line[idx + len('winws.exe'):].strip()

    # Удаляем возможные символы ^ (хотя мы уже убрали их при сборке)
    args_str = args_str.replace('^', '')

    # Разбиваем аргументы с учётом кавычек (простой split)
    def split_args(cmdline: str) -> List[str]:
        args = []
        current = []
        in_quote = False
        i = 0
        while i < len(cmdline):
            ch = cmdline[i]
            if ch == '"':
                in_quote = not in_quote
                i += 1
            elif ch.isspace() and not in_quote:
                if current:
                    args.append(''.join(current))
                    current = []
                i += 1
            else:
                current.append(ch)
                i += 1
        if current:
            args.append(''.join(current))
        return args

    raw_args = split_args(args_str)

    # Заменяем макросы
    game_filter, game_filter_tcp, game_filter_udp = get_game_filter_params()
    replacements = {
        '%GameFilter%': game_filter,
        '%GameFilterTCP%': game_filter_tcp,
        '%GameFilterUDP%': game_filter_udp,
        '%%GameFilter%%': game_filter,
        '%%GameFilterTCP%%': game_filter_tcp,
        '%%GameFilterUDP%%': game_filter_udp,
        '%BIN%': str(BIN_DIR) + "\\",
        '%%BIN%%': str(BIN_DIR) + "\\",
        '%LISTS%': str(LISTS_DIR) + "\\",
        '%%LISTS%%': str(LISTS_DIR) + "\\",
    }
    processed = []
    for arg in raw_args:
        for old, new in replacements.items():
            arg = arg.replace(old, new)
        if arg.startswith('@'):
            fname = arg[1:]
            if not Path(fname).is_absolute():
                fname = str(DATA_DIR / fname)
            arg = '@' + fname
        processed.append(arg)
    return processed

def install(strategy_file: str) -> bool:
    """
    Устанавливает службу zapret на основе файла стратегии (например, "general (ALT11).bat").
    Возвращает True при успехе.
    """
    require_admin()
    strategy_path = Path(strategy_file)
    if not strategy_path.is_absolute():
        strategy_path = DATA_DIR / strategy_file
    if not strategy_path.exists():
        raise FileNotFoundError(f"Файл стратегии не найден: {strategy_path}")

    print(f"Установка службы с использованием {strategy_path.name}...")
    args = _extract_winws_args(strategy_path)

    winws_path = BIN_DIR / "winws.exe"
    if not winws_path.exists():
        raise FileNotFoundError(f"{winws_path} не найден")

    # Формируем командную строку для службы
    cmd_parts = [str(winws_path)] + args
    full_cmd = subprocess.list2cmdline(cmd_parts)
    binpath_value = f'"{full_cmd}"'

    print("\n--- Диагностика ---")
    print(f"Полная команда для службы:\n{full_cmd}")
    print("--------------------\n")

    # Включаем TCP timestamps
    tcp_enable()

    # Удаляем предыдущую службу zapret (если есть)
    service_delete(SERVICE_ZAPRET)
    kill_process_by_name("winws.exe")

    # Создаём службу
    create_cmd = [
        "sc", "create", SERVICE_ZAPRET,
        "binPath=", binpath_value,
        "DisplayName=", "zapret",
        "start=", "auto"
    ]
    result = run_cmd(create_cmd, capture_output=True)
    if result.returncode != 0:
        print(f"Ошибка создания службы: {result.stderr}")
        return False

    run_cmd(["sc", "description", SERVICE_ZAPRET, "Zapret DPI bypass software"], capture_output=True)

    time.sleep(2)
    start_result = run_cmd(["sc", "start", SERVICE_ZAPRET], capture_output=True)
    if start_result.returncode != 0:
        print(f"Ошибка запуска службы: {start_result.stderr}")
        return False

    time.sleep(3)
    proc_check = run_cmd(["tasklist", "/FI", "IMAGENAME eq winws.exe"], capture_output=True)
    if "winws.exe" in proc_check.stdout:
        print("✓ Процесс winws.exe успешно запущен.")
    else:
        print("✗ ВНИМАНИЕ: процесс winws.exe не обнаружен после запуска службы.")

    # Сохраняем имя стратегии в реестр
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Services\zapret") as key:
            winreg.SetValueEx(key, "zapret-discord-youtube", 0, winreg.REG_SZ, strategy_path.stem)
    except Exception as e:
        print(f"Не удалось записать имя стратегии в реестр: {e}")

    print("Служба zapret успешно установлена и запущена.")
    return True

# ----------------------------------------------------------------------
# Запуск тестов (PowerShell скрипт)
# ----------------------------------------------------------------------
def run_tests() -> None:
    """Запускает PowerShell-скрипт test zapret.ps1 из папки utils."""
    require_admin()
    ps_script = UTILS_DIR / "test zapret.ps1"
    if not ps_script.exists():
        raise FileNotFoundError(f"Скрипт не найден: {ps_script}")

    # Проверка версии PowerShell (требуется 3+)
    ps_check = run_cmd(
        ["powershell", "-NoProfile", "-Command",
         "if ($PSVersionTable.PSVersion.Major -ge 3) { exit 0 } else { exit 1 }"],
        capture_output=True
    )
    if ps_check.returncode != 0:
        raise RuntimeError("Требуется PowerShell 3.0 или новее")

    # Запускаем в отдельном окне
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("Запущен тестовый скрипт в новом окне PowerShell.")

def restart():
    service_remove()
    with open("current.zapret", "r") as f:
        install(f.read())

# ----------------------------------------------------------------------
# Дополнительные функции для совместимости с оригинальным интерфейсом
# ----------------------------------------------------------------------
def status_zapret() -> None:
    """Проверяет, запущена ли служба zapret, и включает TCP timestamps (как в оригинале)."""
    status = service_query_status(SERVICE_ZAPRET)
    if status == "RUNNING":
        print(f'"{SERVICE_ZAPRET}" уже запущена как служба.')
    else:
        tcp_enable()

def load_game_filter() -> Tuple[str, str, str]:
    """Возвращает параметры игрового фильтра."""
    return get_game_filter_params()

def load_user_lists_cli() -> None:
    """Создаёт примеры пользовательских списков (для CLI)."""
    load_user_lists()

def get_status_dict() -> Dict[str, Any]:
    """
    Возвращает структурированную информацию о состоянии служб (для использования в других скриптах).
    """
    return service_status()

# ----------------------------------------------------------------------
# Основной блок для тестирования при запуске модуля
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Простой пример использования: выводим статус
    print("Статус служб:", service_status())
    print("Игровой фильтр:", game_switch_status())
    print("IPSet статус:", ipset_switch_status())
    print("Автообновление:", check_updates_switch_status())
    print("\nДля выполнения действий используйте функции модуля, например:")
    print("  install('general (ALT11).bat')")
    print("  remove()")
    print("  set_ipset_mode('none')")