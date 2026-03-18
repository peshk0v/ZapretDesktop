import os, subprocess, shutil, glob
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
ZAPRET_DIR = DATA_DIR / "zapret-latest"
BIN_DIR = ZAPRET_DIR / "bin"
LISTS_DIR = ZAPRET_DIR / "lists"
UTILS_DIR = ZAPRET_DIR / "utils"
SERVICE_PATH = DATA_DIR / "service.sh"

#UTILITES
def log(text, mode):
    match mode:
        case 0:
            print(f"[LOG] ~ {text}")
        case 1:
            print(f"[WARNING] ~ {text}")
        case 2:
            print(f"[ERROR] ~ {text}\n[PLEASE CREATE ISSULE ON GITHUB]")

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        log(f"RUNCMD {cmd}", 0)
        return result.stdout
    except subprocess.CalledProcessError as e:
        log(f"RUNCMD {e.stderr}", 2)
        return False

def run_service_cmd(args):
    cmd = [SERVICE_PATH]
    for i in args:
        cmd.append(i)
    log(f"Service cmd run. Args: {args}", 0)
    return run_cmd(cmd)

def write_file(path: Path, content: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def download_file(url: str, dest: Path, timeout: int = 10) -> bool:
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

def get_mode_ipset():
    zapret_dir = ZAPRET_DIR
    if not zapret_dir:
        raise EnvironmentError("Переменная окружения ZAPRET_DIR не установлена")
    lists_dir = os.path.join(zapret_dir, 'lists')
    ipset_path = os.path.join(lists_dir, 'ipset-all.txt')
    if not os.path.isdir(lists_dir):
        return "Текущая версия конфигураций не поддерживается"
    if not os.path.isfile(ipset_path):
        open(ipset_path, 'w').close()
    with open(ipset_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f if line.strip()]
    if any('203.0.113.113' in line for line in lines):
        return "None"
    elif len(lines) == 0:
        return "Any"
    else:
        return "Loaded"

def is_service_running(service_name="zapret-discord-youtube"):
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

        try:
            result = subprocess.run(
                ['pgrep', '-f', service_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass

        try:
            result = subprocess.run(
                f"ps aux | grep -v grep | grep -q '{service_name}'",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

def is_zapret_installed(service_names=None):
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

def change_mode_ipset(mode):
    zapret_dir = ZAPRET_DIR
    if not zapret_dir:
        raise EnvironmentError("Переменная окружения ZAPRET_DIR не установлена")
    lists_dir = os.path.join(zapret_dir, 'lists')
    ipset_path = os.path.join(lists_dir, 'ipset-all.txt')
    backup_path = os.path.join(lists_dir, 'ipset-all.txt.backup')
    if mode == "Текущая версия конфигураций не поддерживается":
        raise ValueError("Текущая версия конфигураций не поддерживается. Для смены ipset режима следует поменять версию на более новую.")
    if mode == "None":
        if os.path.exists(ipset_path):
            os.remove(ipset_path)
        open(ipset_path, 'w').close()
        log(f"Выбранный режим IPSET - {get_mode_ipset()}",0)
        return
    if mode == "Any":
        if os.path.exists(backup_path):
            if os.path.exists(ipset_path):
                os.remove(ipset_path)
            shutil.copy2(backup_path, ipset_path)
            log(f"Выбранный режим IPSET - {get_mode_ipset()}",0)
            return
        else:
            raise FileNotFoundError("Не найден бекап, переустановите zapret стратегии.")
    if os.path.exists(backup_path):
        os.remove(backup_path)
    if os.path.exists(ipset_path):
        shutil.copy2(ipset_path, backup_path)
    with open(ipset_path, 'w', encoding='utf-8') as f:
        f.write("203.0.113.113/32\n")
    log(f"Выбранный режим IPSET - {get_mode_ipset()}",0)

#MAIN CONTROLLER

def service_control(comd, args="none"):
    match comd:
        case 0: #start wa service
            run_service_cmd(["run", "--config", "conf.env"])
            log("ZAPRET STARTED WITHOUT SERVICE", 0)
            return True
        case 1: #install service
            run_service_cmd(["service", "install"])
            log("ZAPRET INSTALLED WITH SEEVICE AND RUN", 0)
            return True
        case 2: #remove service
            run_service_cmd(["service", "remove"])
            log("ZAPRET REMOVED WITH SERVICE")
        case 3: #service status
            return is_service_running()
        case 4: #service stop
            run_service_cmd(["service", "stop"])
        case 5: #service start
            run_service_cmd(["service", "start"])
        case 6: #service restart
            run_service_cmd(["service", "restart"])
        case 7: #get strategy list
            cmd = run_service_cmd(["strategy", "list"])
            listc = cmd.split("\n")
            listc.remove('Доступные стратегии:')
            listc.remove('')
            listc.remove('')
            return listc
        case 8: #get config
            conf = run_service_cmd(["config", "show"])
            clines = conf.split("\n")
            celements = []
            for i in clines:
                if clines.index(i) >= 2:
                    celements.append(i.split("="))
            log("Get config file on json",0)
            return {celements[0][0]: celements[0][1], celements[1][0]:celements[1][1], celements[2][0]:celements[2][1]}
            #return {celements[0]: celements[1],celements[2]:celements[3],celements[4]:celements[5]}
        case 9: #set config
            if args == "none":
                return False
            else:
                fl = f"interface={args['interface']}\ngamefilter={args['gamefilter']}\nstrategy={args['strategy']}"
                with open(f"{DATA_DIR}/conf.env", "w") as c:
                    c.write(fl)
                log("Config file rewrited!", 0)
                return True
        case 10: #get ipset status
            return get_mode_ipset()
        case 11: #set ipset status
            return change_mode_ipset(args)
        case 12: #change gamefiler
            cfg = service_control(8)
            if args == 0:
                cfg["gamefilter"] = "false"
            else:
                cfg["gamefilter"] = "true"
            service_control(9, cfg)
        case 13: #change ipset
            match args:
                case 0:
                    change_mode_ipset("Loaded") #NONE
                case 1:
                    change_mode_ipset("None") #ANY
                case 2:
                    change_mode_ipset("Any") #LOADED
        case 14:
            return is_zapret_installed()