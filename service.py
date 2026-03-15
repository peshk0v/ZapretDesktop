"""
Модуль для управления службой zapret.
Установка службы выполняется напрямую (без service.bat), остальные команды через service.bat.
"""

import subprocess
import sys
import ctypes
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).parent.absolute()
SERVICE_BAT = BASE_DIR / "data/service.bat"
DATA_DIR = BASE_DIR / "data"

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return True

def require_admin():
    if not is_admin():
        raise PermissionError(
            "Это действие требует прав администратора.\n"
            "Пожалуйста, перезапустите приложение от имени администратора."
        )

def _run_bat(args: List[str], capture_output: bool = False, input_data: Optional[str] = None) -> subprocess.CompletedProcess:
    """Запускает service.bat с аргументами (всегда добавляет admin первым)."""
    cmd = [str(SERVICE_BAT), "admin"] + args
    encoding = 'cp866' if sys.platform == 'win32' else 'utf-8'
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        input=input_data,
        encoding=encoding,
        check=False
    )

def _get_game_filter_params() -> Dict[str, str]:
    """Возвращает текущие значения GameFilter, GameFilterTCP, GameFilterUDP из файла флага."""
    params = {'GameFilter': '12', 'GameFilterTCP': '12', 'GameFilterUDP': '12'}
    flag_file = DATA_DIR / "utils" / "game_filter.enabled"
    if flag_file.exists():
        mode = flag_file.read_text(encoding='utf-8').strip().lower()
        if mode == 'all':
            params = {'GameFilter': '1024-65535', 'GameFilterTCP': '1024-65535', 'GameFilterUDP': '1024-65535'}
        elif mode == 'tcp':
            params = {'GameFilter': '1024-65535', 'GameFilterTCP': '1024-65535', 'GameFilterUDP': '12'}
        elif mode == 'udp':
            params = {'GameFilter': '1024-65535', 'GameFilterTCP': '12', 'GameFilterUDP': '1024-65535'}
    return params

def _extract_winws_args(strategy_path: Path) -> List[str]:
    """Извлекает аргументы командной строки для winws.exe из файла стратегии."""
    content = strategy_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.splitlines()
    # Собираем многострочную команду
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

    # Удаляем часть до winws.exe включительно
    idx = full_line.lower().find('winws.exe')
    if idx == -1:
        raise ValueError("Не удалось найти winws.exe в строке")
    args_str = full_line[idx + len('winws.exe'):].strip()

    # Простой разбиватель аргументов с учётом кавычек
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

    # Заменяем макросы (с завершающим слешем для папок)
    game_params = _get_game_filter_params()
    replacements = {
        '%GameFilter%': game_params['GameFilter'],
        '%GameFilterTCP%': game_params['GameFilterTCP'],
        '%GameFilterUDP%': game_params['GameFilterUDP'],
        '%%GameFilter%%': game_params['GameFilter'],
        '%%GameFilterTCP%%': game_params['GameFilterTCP'],
        '%%GameFilterUDP%%': game_params['GameFilterUDP'],
        '%BIN%': str(DATA_DIR / "bin") + "\\",
        '%%BIN%%': str(DATA_DIR / "bin") + "\\",
        '%LISTS%': str(DATA_DIR / "lists") + "\\",
        '%%LISTS%%': str(DATA_DIR / "lists") + "\\",
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

    winws_path = DATA_DIR / "bin" / "winws.exe"
    if not winws_path.exists():
        raise FileNotFoundError(f"{winws_path} не найден")

    cmd_parts = [str(winws_path)] + args
    full_cmd = subprocess.list2cmdline(cmd_parts)
    binpath_value = f'"{full_cmd}"'

    print("\n--- Диагностика ---")
    print(f"Полная команда для службы:\n{full_cmd}")
    print("--------------------\n")

    subprocess.run(["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"], check=False)

    subprocess.run(["sc", "stop", "zapret"], capture_output=True)
    subprocess.run(["sc", "delete", "zapret"], capture_output=True)

    create_cmd = [
        "sc", "create", "zapret",
        "binPath=", binpath_value,
        "DisplayName=", "zapret",
        "start=", "auto"
    ]
    result = subprocess.run(create_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Ошибка создания службы: {result.stderr}")
        return False

    subprocess.run(["sc", "description", "zapret", "Zapret DPI bypass software"], check=False)

    time.sleep(2)
    start_result = subprocess.run(["sc", "start", "zapret"], capture_output=True, text=True)
    if start_result.returncode != 0:
        print(f"Ошибка запуска службы: {start_result.stderr}")
        return False

    time.sleep(3)
    proc_check = subprocess.run(["tasklist", "/FI", "IMAGENAME eq winws.exe"], capture_output=True, text=True)
    if "winws.exe" in proc_check.stdout:
        print("✓ Процесс winws.exe успешно запущен.")
    else:
        print("✗ ВНИМАНИЕ: процесс winws.exe не обнаружен после запуска службы.")

    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Services\zapret") as key:
            winreg.SetValueEx(key, "zapret-discord-youtube", 0, winreg.REG_SZ, strategy_path.stem)
    except Exception as e:
        print(f"Не удалось записать имя стратегии в реестр: {e}")

    print("Служба zapret успешно установлена и запущена.")
    return True

def remove() -> bool:
    """
    Полностью удаляет службу zapret, останавливает процесс winws.exe.
    Возвращает True при успешном удалении.
    """
    require_admin()
    SERVICE_NAME = "zapret"
    print(f"Удаление службы {SERVICE_NAME}...")

    # 1. Останавливаем службу, если она запущена
    stop_result = subprocess.run(["sc", "stop", SERVICE_NAME], capture_output=True, text=True)
    if stop_result.returncode == 0:
        print("  Служба остановлена.")
    else:
        # Если служба не найдена или уже остановлена – игнорируем ошибку
        if "not running" not in stop_result.stderr.lower() and "not exist" not in stop_result.stderr.lower():
            print(f"  Предупреждение при остановке: {stop_result.stderr}")

    # 2. Даём время на остановку
    time.sleep(2)

    # 3. Принудительно завершаем процесс winws.exe
    subprocess.run(["taskkill", "/IM", "winws.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 4. Удаляем службу
    delete_result = subprocess.run(["sc", "delete", SERVICE_NAME], capture_output=True, text=True)
    if delete_result.returncode == 0:
        print("✅ Служба zapret успешно удалена.")
        return True
    else:
        # Если служба не найдена – считаем успехом
        if "not exist" in delete_result.stderr.lower():
            print("✅ Служба zapret не существует (уже удалена).")
            return True
        else:
            print(f"❌ Ошибка при удалении службы: {delete_result.stderr}")
            # Попробуем удалить через реестр (крайний случай)
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services", 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteKey(key, SERVICE_NAME)
                winreg.CloseKey(key)
                print("✅ Служба удалена через реестр.")
                return True
            except Exception as e:
                print(f"❌ Не удалось удалить службу даже через реестр: {e}")
                return False

def restart() -> None:
    """
    Перезапускает службу zapret: останавливает и снова запускает.
    Требует прав администратора.
    """
    require_admin()
    print("Перезапуск службы zapret...")
    subprocess.run(["sc", "stop", "zapret"], capture_output=True)
    time.sleep(2)
    start_result = subprocess.run(["sc", "start", "zapret"], capture_output=True, text=True)
    if start_result.returncode == 0:
        print("✅ Служба zapret успешно перезапущена.")
    else:
        print(f"❌ Ошибка при перезапуске службы: {start_result.stderr}")

def set_autostart(enabled: bool) -> None:
    """
    Включает или отключает автоматический запуск службы при старте Windows.
    enabled=True  -> тип запуска 'auto' (автоматически)
    enabled=False -> тип запуска 'demand' (вручную)
    Требует прав администратора.
    """
    require_admin()
    start_type = "auto" if enabled else "demand"
    result = subprocess.run(["sc", "config", "zapret", "start=", start_type], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Автозапуск службы {'включён' if enabled else 'отключён'}.")
    else:
        print(f"❌ Не удалось изменить автозапуск: {result.stderr}")

def get_autostart_status() -> bool:
    """
    Возвращает True, если служба настроена на автоматический запуск (auto),
    иначе False.
    """
    result = subprocess.run(["sc", "qc", "zapret"], capture_output=True, text=True)
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if "START_TYPE" in line:
            # Пример: "START_TYPE         : 2   AUTO_START"
            if "AUTO_START" in line:
                return True
            else:
                return False
    return False

def status() -> subprocess.CompletedProcess:
    return _run_bat(["status"])

def game_switch(mode: str) -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["game_switch", mode])

def ipset_switch() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["ipset_switch"])

def check_updates_switch() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["check_updates_switch"])

def ipset_update() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["ipset_update"])

def hosts_update() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["hosts_update"])

def check_updates(soft: bool = False) -> subprocess.CompletedProcess:
    args = ["check_updates"]
    if soft:
        args.append("soft")
    return _run_bat(args)

def diagnostics() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["diagnostics"])

def run_tests() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["run_tests"])

def status_zapret() -> subprocess.CompletedProcess:
    return _run_bat(["status_zapret"])

def load_game_filter() -> Dict[str, str]:
    return _get_game_filter_params()

def load_user_lists() -> subprocess.CompletedProcess:
    require_admin()
    return _run_bat(["load_user_lists"])

def get_status_dict() -> Dict[str, Any]:
    result = _run_bat(["status"], capture_output=True)
    info = {
        'strategy': None,
        'zapret_running': None,
        'windivert_running': None,
        'windivert_sys_exists': True,
        'winws_running': None,
    }
    for line in result.stdout.splitlines():
        if "Service strategy installed from" in line and '"' in line:
            info['strategy'] = line.split('"')[1]
        elif "zapret service is RUNNING" in line:
            info['zapret_running'] = True
        elif "zapret service is NOT running" in line:
            info['zapret_running'] = False
        elif "WinDivert service is RUNNING" in line:
            info['windivert_running'] = True
        elif "WinDivert service is NOT running" in line:
            info['windivert_running'] = False
        elif "WinDivert64.sys file NOT found" in line:
            info['windivert_sys_exists'] = False
        elif "Bypass (winws.exe) is RUNNING" in line:
            info['winws_running'] = True
        elif "Bypass (winws.exe) is NOT running" in line:
            info['winws_running'] = False
    return info

__all__ = [
    'install',
    'remove',
    'restart',
    'set_autostart',
    'get_autostart_status',
    'status',
    'game_switch',
    'ipset_switch',
    'check_updates_switch',
    'ipset_update',
    'hosts_update',
    'check_updates',
    'diagnostics',
    'run_tests',
    'status_zapret',
    'load_game_filter',
    'load_user_lists',
    'get_status_dict',
]