import json
import requests
import zipfile
import io
import ctypes
import os, time, sys
import service as sv

def getConf():
    with open(f"{sv.BASE_DIR}/config.json", "r") as f:
        return json.load(f)

def oblist():
    lst = sv.service_control(7)
    ret = []
    for i in lst:
        ret.append(i[:-4])
    return ret

def getdata():
    with open(f"{sv.BASE_DIR}/data.json", "r") as f:
        return json.load(f)

def setdata(dta):
    with open(f"{sv.BASE_DIR}/data.json", "w") as f:
        json.dump(dta, f)

def applysets():
    sets = getsets()
    sv.service_control(13, change_names(sets["IPSET"]))
    sv.service_control(12, change_names(sets["GameFilter"]))
    

def getsets():
    dta = getdata()
    return dta["settings"]

def savesets(set):
    dta = getdata()
    dta["settings"] = set
    setdata(dta)
    applysets()
    sv.service_control(6)

def change_names(names):
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

# def setAutostart(enblt):
#     dta = getdata()
#     dta["service"] = enblt
#     setdata(dta)
#     if enblt:
#         sv.install(getCurrent())
#     else:
#         sv.service_remove()

def desktop(tf):
    if tf:
        with open("ZAPRET.desktop", "w") as z:
            fl = f"[Desktop Entry]\nEncoding=UTF-8\nVersion=0.1\nType=Application\nTerminal=false\nExec={sv.BASE_DIR}/venv/bin/python3 {sv.BASE_DIR}/app.py\nName=ZAPRET\nIcon={sv.BASE_DIR}/icon.png"
            z.write(fl)
        os.system("mv ZAPRET.desktop ~/.local/share/applications/ZAPRET.desktop")
        os.system("update-desktop-database ~/.local/share/applications")
    else:
        os.system("rm ~/.local/share/applications/ZAPRET.desktop")
        os.system("update-desktop-database ~/.local/share/applications")

def merge_enabled_settings(old_path: str, new_path: str) -> None:
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
            if name in old_enabled:
                item['Enabled'] = old_enabled[name]
            else:
                item['Enabled'] = False

    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)

def getservc():
    with open(f"{sv.BASE_DIR}/services.json") as f:
        return json.load(f)

def applyservc():
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


def setservc(dta):
    serv = getservc()
    for idx, val in enumerate(dta):
        if idx < len(serv):
            serv[idx]["Enabled"] = val
    with open(f"{sv.BASE_DIR}/services.json", "w") as file:
        json.dump(serv, file, indent=4)
    applyservc()
    # sv.service_control(6)
    return True
    

def updServc():
    os.rename(f"{sv.BASE_DIR}/services.json",f"{sv.BASE_DIR}/oldServices.json")
    new = requests.get("https://github.com/peshk0v/ZapretDesktop/raw/main/services.json")
    with open(f"{sv.BASE_DIR}/services.json", "wb") as file:
        for chunk in new.iter_content(chunk_size=8192):
            file.write(chunk)
    merge_enabled_settings(f"{sv.BASE_DIR}/oldServices.json", f"{sv.BASE_DIR}/services.json")
    os.remove(f"{sv.BASE_DIR}/oldServices.json")
    return True

def getCurrent():
    return sv.service_control(8)["strategy"]

def getObName():
    return getCurrent()[:-4]
def zapStat():
    return sv.service_control(3)
def setObName(nm):
    nmm = nm + ".bat"
    se = getConf()
    se["strategy"] = nmm
    sv.service_control(9, se)

def downloadzapret(config):
    try:
        os.system("git clone https://github.com/Sergeydigl3/zapret-discord-youtube-linux.git data/")
    finally:
        os.system(f"{sv.BASE_DIR}/data/service.sh download-deps --default")

#   applysets()
    applyservc()