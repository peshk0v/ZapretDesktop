# -*- coding: utf-8 -*-

import eel
import service as sv
import functions as fn

eel.init(f"{sv.BASE_DIR}/web")


# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------
@eel.expose
def get_obname() -> str:
    return fn.getObName()


@eel.expose
def get_status() -> bool:
    return fn.zapStat()


@eel.expose
def start_zapret() -> bool:
    sv.service_control(5)
    return get_status()


@eel.expose
def stop_zapret() -> bool:
    sv.service_control(4)
    return get_status()


@eel.expose
def get_oblist() -> list:
    return fn.oblist()


@eel.expose
def set_obname(name: str) -> bool:
    fn.setObName(name)
    return True


@eel.expose
def getservc() -> dict:
    return fn.getservc()


@eel.expose
def astrt(tf: bool) -> None:
    if tf:
        sv.service_control(1)
    else:
        sv.service_control(2)


@eel.expose
def setservc(data: list) -> bool:
    fn.setservc(data)
    return True


@eel.expose
def updServc() -> bool:
    return fn.updServc()


@eel.expose
def getsets() -> dict:
    return fn.getsets()


@eel.expose
def savesets(sets: dict) -> None:
    fn.savesets(sets)


@eel.expose
def get_autostart_status() -> bool:
    return sv.service_control(14)


# ----------------------------------------------------------------------
# Start GUI
# ----------------------------------------------------------------------
eel.start('index.html', mode="firefox")