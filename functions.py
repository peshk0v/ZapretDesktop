import json
import requests
import zipfile
import io
import ctypes
import os, time
import service as sv

def getConf():
    with open("config.json", "r") as f:
        return json.load(f)

def oblist():
    lst = os.listdir("data/")
    lst.remove('bin')
    lst.remove("lists")
    lst.remove('utils')
    lst.remove('service.bat')
    ret = []
    for i in lst:
        ret.append(i[:-4])
    return ret

def getdata():
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def setdata(dta):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(dta, f)

def applysets():
    sets = getsets()
    sv.set_ipset_mode(sets["IPSET"])
    sv.game_switch(sets["GameFilter"])

def getsets():
    dta = getdata()
    return dta.get("settings", {"IPSET": "loaded", "GameFilter": "all", "autoUpdateServices": False, "autoUpdateZapret": False})

def savesets(sets):
    dta = getdata()
    if "settings" not in dta:
        dta["settings"] = {}
    dta["settings"]["IPSET"] = sets.get("IPSET", "loaded")
    dta["settings"]["GameFilter"] = sets.get("GameFilter", "all")
    dta["settings"]["autoUpdateServices"] = sets.get("autoUpdateServices", False)
    dta["settings"]["autoUpdateZapret"] = sets.get("autoUpdateZapret", False)
    setdata(dta)
    applysets()
    sv.restart()

def setAutostart(enblt):
    dta = getdata()
    dta["service"] = enblt
    setdata(dta)
    if enblt:
        sv.install(getCurrent())
    else:
        sv.service_remove()

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
    with open("services.json") as f:
        return json.load(f)

def applyservc():
    cfg = getdata()
    servc = getservc()
    with open("data\\lists\\list-general.txt", "w") as lg:
        with open("data\\lists\\list-exclude.txt", "w") as ex:
            newlg = ""
            newex = cfg.get("baseExclude", "")
            for i in servc:
                if i["Enabled"]:
                    for a in i["IPS"]:
                        newlg = newlg + a + "\n"
                    for b in i.get("Exclude", []):
                        newex = newex + "\n" + b
            ex.write(newex)
            lg.write(newlg)


def setservc(dta):
    serv = getservc()
    for idx, val in enumerate(dta):
        if idx < len(serv):
            serv[idx]["Enabled"] = val
    with open("services.json", "w") as file:
        json.dump(serv, file, indent=4)
    applyservc()
    sv.restart()
    return True
    

def updServc():
    os.rename("services.json","oldServices.json")
    new = requests.get("https://github.com/peshk0v/ZapretDesktop/raw/main/services.json")
    with open("services.json", "wb") as file:
        for chunk in new.iter_content(chunk_size=8192):
            file.write(chunk)
    merge_enabled_settings('oldServices.json', 'services.json')
    os.remove("oldServices.json")
    return True

def getCurrent():
    with open("current.zapret", "r") as f:
        return f.read()
def getObName():
    return getCurrent()[:-4]
def zapStat():
    return getdata()["service"]
def setObName(nm):
    nmm = nm + ".bat"
    with open("current.zapret", "w") as f:
        f.write(nmm)

def downloadzapret(config):
    repo_url = 'https://api.github.com/repos/' + config["zapretDYRepo"] + '/releases/latest'
    response = requests.get(repo_url)
    
    if response.status_code == 200:
        latest_release = response.json()
        zip_url = None
        
        for asset in latest_release.get("assets", []):
            if asset["name"].endswith('.zip'):
                zip_url = asset["browser_download_url"]
                break
        
        if zip_url:
            zip_response = requests.get(zip_url)

            if zip_response.status_code == 200:
                try:
                    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as z:
                        z.extractall('data/')
                    print("Скачивание и распаковка завершены.")
                except zipfile.BadZipFile:
                    print("Ошибка: полученный файл не является ZIP-архивом.")
            else:
                print(f'Ошибка при скачивании ZIP: {zip_response.status_code}')
        else:
            print("ZIP-архив не найден среди активов.")
    else:
        print(f'Ошибка при получении последнего релиза: {response.status_code}')
    with open("/data/service.py", "w") as f:
        with open("newservc.bat", "r") as s:
            f.write(s.read()) 

    applysets()
    applyservc()

def get_theme():
    dta = getdata()
    return dta.get("theme", {
        "angle": 135,
        "start": {"r": 102, "g": 126, "b": 234},
        "end": {"r": 118, "g": 75, "b": 162},
        "preset": "Purple Dream"
    })

def save_theme(theme):
    dta = getdata()
    dta["theme"] = theme
    setdata(dta)