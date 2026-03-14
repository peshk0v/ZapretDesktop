import requests, io, os, zipfile
import functions as fn
import service
import eel

config = fn.getConf()
print(fn.getCurrent())
if not any(os.scandir('data/')):
    fn.downloadzapret(fn.getConf())
else: print(f"Zapret Installed")

eel.init('web')

@eel.expose
def get_obname():
    return fn.getObName()

@eel.expose
def get_status():
    return fn.zapStat()

@eel.expose
def start_zapret():
    fn.setAutostart(True)
    return get_status()

@eel.expose
def stop_zapret():
    fn.setAutostart(False)
    return get_status()

@eel.expose
def get_oblist():
    return fn.oblist()

@eel.expose
def set_obname(name):
    fn.setObName(name)
    return True

eel.start('index.html', mode='edge')