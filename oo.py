import service as sv
import os

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

desktop(True)