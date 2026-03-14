"""
Модуль для управления службой zapret (DPI-обходчик).
Предполагается, что этот модуль находится в корневой папке,
а все файлы zapret (bin, lists, utils) находятся в подпапке 'data'.
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import urllib.error
import winreg
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Union

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

BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"

def run_cmd(cmd: list, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Запускает внешнюю команду и возвращает результат."""
    try:
        if capture_output:
            return subprocess.run(cmd, capture_output=True, text=True, check=False)
        else:
            return subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"Ошибка выполнения команды {' '.join(cmd)}: {e}", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, returncode=-1)

def ensure_dir(path: Path) -> None:
    """Создаёт каталог, если он не существует."""
    path.mkdir(parents=True, exist_ok=True)

def read_file_lines(path: Path) -> List[str]:
    """Читает файл и возвращает список строк."""
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
    """Скачивает файл по URL в указанное место. Возвращает True при успехе."""
    try:
        req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                content = response.read()
                with open(dest, 'wb') as f:
                    f.write(content)
                return True
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}", file=sys.stderr)
    return False

def is_command_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def check_extracted() -> bool:
    """Проверяет наличие папки data/bin."""
    return (DATA_DIR / "bin").exists()

def service_query_status(service_name: str) -> Optional[str]:
    """Возвращает состояние службы Windows или None, если служба не найдена."""
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
    """Удаляет службу, если она существует."""
    if service_query_status(service_name) is None:
        return True
    run_cmd(["net", "stop", service_name])
    result = run_cmd(["sc", "delete", service_name])
    return result.returncode == 0

def kill_process_by_name(proc_name: str) -> None:
    """Завершает все процессы с заданным именем."""
    run_cmd(["taskkill", "/IM", proc_name, "/F"])

def tcp_enable() -> bool:
    """Включает TCP timestamps, если они отключены."""
    result = run_cmd(["netsh", "interface", "tcp", "show", "global"], capture_output=True)
    if result.returncode != 0:
        return False
    if "timestamps" in result.stdout.lower() and "enabled" in result.stdout.lower():
        return True
    return run_cmd(["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"]).returncode == 0

def load_user_lists() -> None:
    """Создаёт примеры пользовательских списков в data/lists, если их нет."""
    lists_dir = DATA_DIR / "lists"
    ensure_dir(lists_dir)

    examples = {
        "ipset-exclude-user.txt": "203.0.113.113/32",
        "list-general-user.txt": "domain.example.abc",
        "list-exclude-user.txt": "domain.example.abc",
    }
    for fname, content in examples.items():
        path = lists_dir / fname
        if not path.exists():
            write_file(path, content + "\n")

def get_game_filter_params() -> Tuple[str, str, str]:
    """Возвращает (GameFilter, GameFilterTCP, GameFilterUDP) в зависимости от файла game_filter.enabled."""
    flag_file = DATA_DIR / "utils" / GAME_FILTER_FILE
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
    """Возвращает состояние игрового фильтра: disabled, all, tcp, udp."""
    flag_file = DATA_DIR / "utils" / GAME_FILTER_FILE
    if not flag_file.exists():
        return "disabled"
    mode = read_file_lines(flag_file)
    return mode[0].strip().lower() if mode else "disabled"

def game_switch(mode: str) -> None:
    """Устанавливает режим игрового фильтра: disable, all, tcp, udp."""
    flag_file = DATA_DIR / "utils" / GAME_FILTER_FILE
    ensure_dir(flag_file.parent)

    if mode == "disable":
        if flag_file.exists():
            flag_file.unlink()
    elif mode in ("all", "tcp", "udp"):
        write_file(flag_file, mode + "\n")
    else:
        raise ValueError(f"Недопустимый режим: {mode}")

def check_updates_switch_status() -> bool:
    """True, если автоматическая проверка обновлений включена."""
    return (DATA_DIR / "utils" / CHECK_UPDATES_FILE).exists()

def check_updates_switch(enable: bool) -> None:
    """Включает или отключает автоматическую проверку обновлений."""
    flag_file = DATA_DIR / "utils" / CHECK_UPDATES_FILE
    ensure_dir(flag_file.parent)
    if enable:
        if not flag_file.exists():
            write_file(flag_file, "ENABLED\n")
    else:
        if flag_file.exists():
            flag_file.unlink()

def ipset_switch_status() -> str:
    """Возвращает состояние ipset-фильтра: loaded, none, any."""
    list_file = DATA_DIR / "lists" / "ipset-all.txt"
    if not list_file.exists():
        return "any"
    lines = read_file_lines(list_file)
    if not lines:
        return "any"
    if len(lines) == 1 and lines[0].strip() == "203.0.113.113/32":
        return "none"
    return "loaded"

def ipset_switch() -> None:
    """Переключает режим ipset-фильтра по циклу: loaded -> none -> any -> loaded."""
    list_file = DATA_DIR / "lists" / "ipset-all.txt"
    backup_file = list_file.with_suffix(".txt.backup")
    current = ipset_switch_status()

    if current == "loaded":
        if not backup_file.exists():
            list_file.rename(backup_file)
        else:
            if backup_file.exists():
                backup_file.unlink()
            list_file.rename(backup_file)
        write_file(list_file, "203.0.113.113/32\n")
    elif current == "none":
        if list_file.exists():
            list_file.unlink()
        write_file(list_file, "")
    elif current == "any":
        if backup_file.exists():
            if list_file.exists():
                list_file.unlink()
            backup_file.rename(list_file)
        else:
            raise FileNotFoundError("Нет резервной копии для восстановления ipset-all.txt")
    else:
        raise RuntimeError(f"Неизвестное состояние ipset: {current}")

def ipset_update() -> bool:
    """Обновляет ipset-all.txt из репозитория. Возвращает True при успехе."""
    list_file = DATA_DIR / "lists" / "ipset-all.txt"
    ensure_dir(list_file.parent)
    return download_file(IPSET_URL, list_file)

def hosts_update(auto_replace: bool = False) -> bool:
    """Проверяет актуальность системного hosts-файла. При auto_replace=True заменяет его."""
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

    if hosts_file.exists():
        current_lines = read_file_lines(hosts_file)
        found_first = any(first_line in line for line in current_lines)
        found_last = any(last_line in line for line in current_lines)
        if found_first and found_last:
            temp_file.unlink(missing_ok=True)
            return True

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

def service_check_updates(soft: bool = False) -> Optional[str]:
    """Проверяет наличие новой версии на GitHub. Возвращает версию или None."""
    try:
        req = urllib.request.Request(GITHUB_VERSION_URL, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                github_version = response.read().decode('utf-8').strip()
                return github_version if github_version != LOCAL_VERSION else None
            else:
                if not soft:
                    print("Не удалось получить информацию о версии.")
                return None
    except Exception as e:
        if not soft:
            print(f"Ошибка при проверке обновлений: {e}")
        return None

def service_diagnostics() -> Dict[str, Union[bool, str, List[str]]]:
    """Выполняет диагностику системы и возвращает словарь с результатами."""
    result = {}

    bfe_status = service_query_status("BFE")
    result['bfe_running'] = (bfe_status == "RUNNING")

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

    ts_check = run_cmd(["netsh", "interface", "tcp", "show", "global"], capture_output=True)
    result['tcp_timestamps_enabled'] = "timestamps" in ts_check.stdout.lower() and "enabled" in ts_check.stdout.lower()

    adguard_check = run_cmd(["tasklist", "/FI", "IMAGENAME eq AdguardSvc.exe"], capture_output=True)
    result['adguard_running'] = "AdguardSvc.exe" in adguard_check.stdout

    sc_query_out = run_cmd(["sc", "query"], capture_output=True).stdout
    result['killer_found'] = "Killer" in sc_query_out
    result['intel_found'] = "Intel" in sc_query_out and "Connectivity" in sc_query_out and "Network" in sc_query_out

    checkpoint_found = False
    for svc in ["TracSrvWrapper", "EPWD"]:
        if run_cmd(["sc", "query", svc], capture_output=True).returncode == 0:
            checkpoint_found = True
            break
    result['checkpoint_found'] = checkpoint_found

    result['smartbyte_found'] = "SmartByte" in sc_query_out

    bin_path = DATA_DIR / "bin"
    result['windivert_sys_exists'] = any(bin_path.glob("*.sys"))

    vpn_services = []
    for line in sc_query_out.splitlines():
        if "VPN" in line:
            parts = line.split()
            if len(parts) > 1:
                vpn_services.append(parts[1])
    result['vpn_services'] = vpn_services

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

    hosts_file = Path(os.environ['SystemRoot']) / "System32" / "drivers" / "etc" / "hosts"
    yt_in_hosts = False
    if hosts_file.exists():
        with open(hosts_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            if "youtube.com" in content or "yotou.be" in content:
                yt_in_hosts = True
    result['youtube_in_hosts'] = yt_in_hosts

    winws_running = "winws.exe" in run_cmd(["tasklist", "/FI", "IMAGENAME eq winws.exe"], capture_output=True).stdout
    windivert_running = (service_query_status(SERVICE_WINDIVERT) == "RUNNING")
    result['winws_running'] = winws_running
    result['windivert_running'] = windivert_running

    conflicting_services = ["GoodbyeDPI", "discordfix_zapret", "winws1", "winws2"]
    found_conflicts = []
    for svc in conflicting_services:
        if service_query_status(svc) is not None:
            found_conflicts.append(svc)
    result['conflicting_services'] = found_conflicts

    return result

def service_status() -> Dict[str, any]:
    """Возвращает информацию о состоянии служб и процесса."""
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

    info['windivert_sys_exists'] = any((DATA_DIR / "bin").glob("*.sys"))

    proc_check = run_cmd(["tasklist", "/FI", "IMAGENAME eq winws.exe"], capture_output=True)
    info['winws_running'] = "winws.exe" in proc_check.stdout

    return info

def service_remove() -> None:
    """Останавливает и удаляет службы zapret, WinDivert, WinDivert14, убивает процесс winws.exe."""
    kill_process_by_name("winws.exe")
    for svc in [SERVICE_ZAPRET, SERVICE_WINDIVERT, SERVICE_WINDIVERT14]:
        service_delete(svc)

def service_install(strategy_file: str) -> bool:
    """Устанавливает службу zapret на основе указанного .bat файла со стратегией. Возвращает True при успехе."""
    strategy_path = Path(strategy_file)
    if not strategy_path.is_absolute():
        strategy_path = DATA_DIR / strategy_file
    if not strategy_path.exists():
        raise FileNotFoundError(f"Файл стратегии не найден: {strategy_path}")

    with open(strategy_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    bin_path = DATA_DIR / "bin"
    lists_path = DATA_DIR / "lists"
    winws_exe = str(bin_path / "winws.exe").replace('\\', '\\\\')

    args_line = None
    for line in lines:
        if "winws.exe" in line:
            args_line = line
            break

    if args_line is None:
        raise ValueError("Не найдена строка с winws.exe в файле стратегии")

    idx = args_line.find("winws.exe")
    if idx == -1:
        raise ValueError("Не удалось найти winws.exe в строке")
    rest = args_line[idx + len("winws.exe"):].strip()

    game_filter, game_filter_tcp, game_filter_udp = get_game_filter_params()

    rest = rest.replace("%%GameFilter%%", game_filter)
    rest = rest.replace("%%GameFilterTCP%%", game_filter_tcp)
    rest = rest.replace("%%GameFilterUDP%%", game_filter_udp)
    rest = rest.replace("%%BIN%%", str(bin_path))
    rest = rest.replace("%%LISTS%%", str(lists_path))

    args = []
    in_quote = False
    current = []
    for ch in rest:
        if ch == '"' and not in_quote:
            in_quote = True
        elif ch == '"' and in_quote:
            in_quote = False
            args.append(''.join(current))
            current = []
        elif ch.isspace() and not in_quote:
            if current:
                args.append(''.join(current))
                current = []
        else:
            current.append(ch)
    if current:
        args.append(''.join(current))

    bin_path_winws = bin_path / "winws.exe"
    cmd_line = f'"{bin_path_winws}" ' + ' '.join(args)

    tcp_enable()
    service_remove()

    create_cmd = [
        "sc", "create", SERVICE_ZAPRET,
        f'binPath="{cmd_line}"',
        "DisplayName=", "zapret",
        "start=", "auto"
    ]
    result = run_cmd(create_cmd)
    if result.returncode != 0:
        return False

    run_cmd(["sc", "description", SERVICE_ZAPRET, "Zapret DPI bypass software"])
    run_cmd(["sc", "start", SERVICE_ZAPRET])

    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Services\zapret") as key:
            winreg.SetValueEx(key, "zapret-discord-youtube", 0, winreg.REG_SZ, strategy_path.stem)
    except Exception as e:
        print(f"Не удалось записать имя стратегии в реестр: {e}")

    return True

def run_tests() -> None:
    """Запускает PowerShell-скрипт test zapret.ps1 из папки data/utils."""
    ps_script = DATA_DIR / "utils" / "test zapret.ps1"
    if not ps_script.exists():
        raise FileNotFoundError(f"Скрипт не найден: {ps_script}")

    ps_check = run_cmd(["powershell", "-NoProfile", "-Command",
                        "if ($PSVersionTable.PSVersion.Major -ge 3) { exit 0 } else { exit 1 }"])
    if ps_check.returncode != 0:
        raise RuntimeError("Требуется PowerShell 3.0 или новее")

    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)])

def status_zapret() -> None:
    """Проверяет статус службы zapret и включает TCP timestamps (аналог service.bat status_zapret)."""
    status = service_query_status(SERVICE_ZAPRET)
    if status == "RUNNING":
        print(f'"{SERVICE_ZAPRET}" уже запущена как служба.')
        return
    tcp_enable()

def check_updates(soft: bool = False) -> Optional[str]:
    """Проверяет обновления. Возвращает новую версию или None."""
    return service_check_updates(soft=soft)

def load_game_filter() -> Tuple[str, str, str]:
    """Возвращает параметры игрового фильтра."""
    return get_game_filter_params()

def load_user_lists_cli() -> None:
    """Создаёт примеры пользовательских списков."""
    load_user_lists()

if __name__ == "__main__":
    print("Статус служб:", service_status())
    print("Игровой фильтр:", game_switch_status())
    print("IPSet статус:", ipset_switch_status())
    print("Автообновление:", check_updates_switch_status())