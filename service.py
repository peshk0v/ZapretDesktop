import os

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
        os.system(cmd)
        log(f"Command run ({cmd})")
        return True
    except Exception as e:
        log(f"Command ({cmd})\nExceprion {e}", 2)
        return False