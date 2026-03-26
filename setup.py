from cx_Freeze import setup, Executable 
setup( 
    name = "ZapretDesktop", 
    version = "0.8", 
    description = "Обход блокировки ТСПУ при помощи подмены DPI",    
    executables = [Executable("app.py")]
)   