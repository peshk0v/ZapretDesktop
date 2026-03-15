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

def setAutostart(enblt):
    dta = getdata()
    dta["service"] = enblt
    setdata(dta)
    if enblt:
        sv.install(getCurrent())
    else:
        sv.remove()

def getservc():
    with open("services.json") as f:
        return json.load(f)

def setservc(dta):
    print(dta)

def updServc():
    time.sleep(10)
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
