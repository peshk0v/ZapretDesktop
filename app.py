import requests, io, os, zipfile
import functions as fn
from service import service_install, service_remove, service_status, game_switch, ipset_update

if not any(os.scandir('data/')):
    fn.downloadzapret(fn.getConf())
else: print("Zapret Installed")