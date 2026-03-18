import os, subprocess
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
            return run_service_cmd(["service", "status"])
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
            return {celements[0][0]: celements[0][1], celements[1][0]:celements[1][1], celements[2][0]:celements[2][1]}
            #return {celements[0]: celements[1],celements[2]:celements[3],celements[4]:celements[5]}
        case 9: #set config
            if args == "none":
                return False
            else:
                cmd = []
                cmd.append("config")
                cmd.append("set")
                for i in args:
                    cmd.append(i)
                ret = run_service_cmd(cmd)
                return ret