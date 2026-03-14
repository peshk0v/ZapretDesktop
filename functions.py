import json
import requests
import zipfile
import io

def getConf():
    with open("config.json", "r") as f:
        return json.load(f)

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
