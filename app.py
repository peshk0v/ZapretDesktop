import requests, io, os, zipfile
import functions as fn
import eel
import service as sv
import time

config = fn.getConf()
print(fn.getCurrent())
# if not any(os.scandir('data/')):
#fn.downloadzapret(fn.getConf())
# else: print(f"Zapret Installed")

eel.init('web')

@eel.expose
def get_obname():
    return fn.getObName()

@eel.expose
def get_status():
    return fn.zapStat()

@eel.expose
def start_zapret():
    sv.service_control(5)
    return get_status()

@eel.expose
def stop_zapret():
    sv.service_control(4)
    return get_status()

@eel.expose
def get_oblist():
    return fn.oblist()

@eel.expose
def set_obname(name):
    fn.setObName(name)
    return True

@eel.expose
def getservc():
    return fn.getservc()

@eel.expose
def astrt(tf):
    if tf:
        sv.service_control(1)
    else:
        sv.service_control(2)

@eel.expose
def setservc(data):
    fn.setservc(data)
    return True

@eel.expose
def updServc():
    return fn.updServc()

@eel.expose
def getsets():
    return fn.getsets()

@eel.expose
def savesets(sets):
    fn.savesets(sets)

@eel.expose
def get_autostart_status():
    return sv.service_control(14)

eel.start('index.html', mode="firefox")