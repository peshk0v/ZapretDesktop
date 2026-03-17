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
    with open("data.json", "r") as f:
        return json.load(f)

def setdata(dta):
    with open("data.json", "w") as f:
        json.dump(dta, f)

def applysets():
    sets = getsets()
    sv.set_ipset_mode(sets["IPSET"])
    sv.game_switch(sets["GameFilter"])

def getsets():
    dta = getdata()
    return dta["settings"]

def savesets(set):
    dta = getdata()
    dta["settings"] = set
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
    servc = getservc()
    with open("data\lists\list-general.txt", "w") as lg:
        new = ""
        for i in servc:
            if i["Enabled"]:
                for a in i["IPS"]:
                    new = new + a + "\n"
        lg.write(new)


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
    os.system("git clone https://github.com/Sergeydigl3/zapret-discord-youtube-linux.git data/")
    os.system("./data/service.sh download-deps --default")

#   applysets()
#   applyservc()