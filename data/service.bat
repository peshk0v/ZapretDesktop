@echo off
set "LOCAL_VERSION=1.9.7b"
setlocal EnableDelayedExpansion

:: Проверка прав администратора
call :check_extracted
if "%1"=="admin" goto :admin
:: Если не admin, перезапускаем с правами
echo Requesting admin rights...
powershell -NoProfile -Command "Start-Process 'cmd.exe' -ArgumentList '/c \"\"%~f0\" admin %*\"' -Verb RunAs"
exit /b

:admin
:: Административные команды
call :check_command chcp
call :check_command find
call :check_command findstr
call :check_command netsh
call :load_user_lists

:: Отладка: покажем полученные аргументы
echo [DEBUG] Full args: %* >&2
echo [DEBUG] 1=%~1, 2=%~2, 3=%~3, 4=%~4 >&2

:: Обработка аргументов командной строки (регистронезависимо)
if /i "%~2"=="install" goto :install_cmd
if /i "%~2"=="remove" goto :remove_cmd
if /i "%~2"=="status" goto :status_cmd
if /i "%~2"=="game_switch" goto :game_switch_cmd
if /i "%~2"=="ipset_switch" goto :ipset_switch_cmd
if /i "%~2"=="check_updates_switch" goto :check_updates_switch_cmd
if /i "%~2"=="ipset_update" goto :ipset_update_cmd
if /i "%~2"=="hosts_update" goto :hosts_update_cmd
if /i "%~2"=="check_updates" goto :check_updates_cmd
if /i "%~2"=="diagnostics" goto :diagnostics_cmd
if /i "%~2"=="run_tests" goto :run_tests_cmd
if /i "%~2"=="status_zapret" goto :status_zapret
if /i "%~2"=="load_game_filter" goto :load_game_filter_cmd
if /i "%~2"=="load_user_lists" goto :load_user_lists_cmd

:: Если ни одна команда не подошла — показать справку
goto :usage

:usage
echo Usage: %~nx0 ^<command^> [arguments]
echo Commands:
echo   install ^<strategy.bat^>   Install service with specified strategy file
echo   remove                     Remove zapret service and related
echo   status                     Show service status
echo   game_switch ^<mode^>        Set game filter mode: disable, all, tcp, udp
echo   ipset_switch               Toggle ipset filter mode
echo   check_updates_switch       Toggle auto-update check
echo   ipset_update               Update ipset list
echo   hosts_update               Check/update hosts file
echo   check_updates              Check for new version
echo   diagnostics                Run system diagnostics
echo   run_tests                  Run configuration tests
echo   status_zapret              Check if zapret service is running (internal)
echo   load_game_filter            Load game filter parameters (internal)
echo   load_user_lists             Create user list templates (internal)
exit /b 1

:install_cmd
if "%~3"=="" (
    echo Error: strategy file name required.
    exit /b 1
)
set "STRATEGY_FILE=%~3"
echo [DEBUG] Install: strategy file = "%STRATEGY_FILE%"
call :service_install "%STRATEGY_FILE%"
exit /b

:remove_cmd
call :service_remove
exit /b

:status_cmd
call :service_status
exit /b

:game_switch_cmd
if "%~3"=="" (
    echo Error: mode required ^(disable, all, tcp, udp^)
    exit /b 1
)
call :game_switch "%~3"
exit /b

:ipset_switch_cmd
call :ipset_switch
exit /b

:check_updates_switch_cmd
call :check_updates_switch
exit /b

:ipset_update_cmd
call :ipset_update
exit /b

:hosts_update_cmd
call :hosts_update
exit /b

:check_updates_cmd
if /i "%~3"=="soft" ( call :service_check_updates soft ) else call :service_check_updates
exit /b

:diagnostics_cmd
call :service_diagnostics
exit /b

:run_tests_cmd
call :run_tests
exit /b

:status_zapret
call :test_service zapret soft
call :tcp_enable
exit /b

:load_game_filter_cmd
call :game_switch_status
exit /b

:load_user_lists_cmd
call :load_user_lists
exit /b

:: ==================== Подпрограммы (оригинальные с улучшенной обработкой) ====================

:load_user_lists
set "LISTS_PATH=%~dp0lists\"
if not exist "%LISTS_PATH%ipset-exclude-user.txt" echo 203.0.113.113/32>"%LISTS_PATH%ipset-exclude-user.txt"
if not exist "%LISTS_PATH%list-general-user.txt" echo domain.example.abc>"%LISTS_PATH%list-general-user.txt"
if not exist "%LISTS_PATH%list-exclude-user.txt" echo domain.example.abc>"%LISTS_PATH%list-exclude-user.txt"
exit /b

:tcp_enable
netsh interface tcp show global | findstr /i "timestamps" | findstr /i "enabled" > nul || netsh interface tcp set global timestamps=enabled > nul 2>&1
exit /b

:service_status
chcp 437 > nul
sc query "zapret" >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Services\zapret" /v zapret-discord-youtube 2^>nul') do echo Service strategy installed from "%%B"
)
call :test_service zapret
call :test_service WinDivert
set "BIN_PATH=%~dp0bin\"
if not exist "%BIN_PATH%\*.sys" call :PrintRed "WinDivert64.sys file NOT found."
echo:
tasklist /FI "IMAGENAME eq winws.exe" | find /I "winws.exe" > nul
if !errorlevel!==0 (
    call :PrintGreen "Bypass (winws.exe) is RUNNING."
) else (
    call :PrintRed "Bypass (winws.exe) is NOT running."
)
exit /b

:test_service
set "ServiceName=%~1"
set "ServiceStatus="
for /f "tokens=3 delims=: " %%A in ('sc query "%ServiceName%" ^| findstr /i "STATE"') do set "ServiceStatus=%%A"
set "ServiceStatus=%ServiceStatus: =%"
if "%ServiceStatus%"=="RUNNING" (
    if "%~2"=="soft" (
        echo "%ServiceName%" is ALREADY RUNNING as service, use "service.bat remove" first if you want to run standalone bat.
        exit /b
    ) else (
        echo "%ServiceName%" service is RUNNING.
    )
) else if "%ServiceStatus%"=="STOP_PENDING" (
    call :PrintYellow "!ServiceName! is STOP_PENDING, that may be caused by a conflict with another bypass. Run diagnostics to try to fix conflicts"
) else if not "%~2"=="soft" (
    echo "%ServiceName%" service is NOT running.
)
exit /b

:service_remove
chcp 65001 > nul
set SRVCNAME=zapret
echo Stopping and removing service %SRVCNAME%...
sc query "!SRVCNAME!" >nul 2>&1
if !errorlevel!==0 (
    net stop %SRVCNAME% >nul 2>&1
    sc delete %SRVCNAME% >nul 2>&1
) else (
    echo Service "%SRVCNAME%" is not installed.
)
echo Killing winws.exe process...
tasklist /FI "IMAGENAME eq winws.exe" | find /I "winws.exe" > nul
if !errorlevel!==0 taskkill /IM winws.exe /F > nul 2>&1

:: WinDivert не удаляем, чтобы не повредить другим службам
exit /b

:service_install
cd /d "%~dp0"
set "selectedFile=%~1"
if not defined selectedFile exit /b 1
if not exist "%selectedFile%" (
    echo Strategy file not found: "%selectedFile%"
    exit /b 1
)
set "BIN_PATH=%~dp0bin\"
set "LISTS_PATH=%~dp0lists\"
set "args_with_value=sni host altorder"
set "args="
set "capture=0"
set "mergeargs=0"
set QUOTE="

for /f "usebackq tokens=*" %%a in ("%selectedFile%") do (
    set "line=%%a"
    call set "line=%%line:^!=EXCL_MARK%%"
    echo !line! | findstr /i "%BIN_PATH%winws.exe" >nul
    if not errorlevel 1 set "capture=1"
    if !capture!==1 (
        if not defined args set "line=!line:*%BIN_PATH%winws.exe=!"
        set "temp_args="
        for %%i in (!line!) do (
            set "arg=%%i"
            if not "!arg!"=="^" (
                if "!arg:~0,2!" EQU "--" if not !mergeargs!==0 set "mergeargs=0"
                if "!arg:~0,1!" EQU "!QUOTE!" (
                    set "arg=!arg:~1,-1!"
                    echo !arg! | findstr ":" >nul
                    if !errorlevel!==0 (
                        set "arg=\!QUOTE!!arg!\!QUOTE!"
                    ) else if "!arg:~0,1!"=="@" (
                        set "arg=\!QUOTE!@%~dp0!arg:~1!\!QUOTE!"
                    ) else if "!arg:~0,5!"=="%%BIN%%" (
                        set "arg=\!QUOTE!!BIN_PATH!!arg:~5!\!QUOTE!"
                    ) else if "!arg:~0,7!"=="%%LISTS%%" (
                        set "arg=\!QUOTE!!LISTS_PATH!!arg:~7!\!QUOTE!"
                    ) else (
                        set "arg=\!QUOTE!%~dp0!arg!\!QUOTE!"
                    )
                ) else if "!arg:~0,12!" EQU "%%GameFilter%%" (
                    set "arg=%GameFilter%"
                ) else if "!arg:~0,15!" EQU "%%GameFilterTCP%%" (
                    set "arg=%GameFilterTCP%"
                ) else if "!arg:~0,15!" EQU "%%GameFilterUDP%%" (
                    set "arg=%GameFilterUDP%"
                )
                if !mergeargs!==1 (
                    set "temp_args=!temp_args!,!arg!"
                ) else if !mergeargs!==3 (
                    set "temp_args=!temp_args!=!arg!"
                    set "mergeargs=1"
                ) else (
                    set "temp_args=!temp_args! !arg!"
                )
                if "!arg:~0,2!" EQU "--" (
                    set "mergeargs=2"
                ) else if !mergeargs! GEQ 1 (
                    if !mergeargs!==2 set "mergeargs=1"
                    for %%x in (!args_with_value!) do if /i "%%x"=="!arg!" set "mergeargs=3"
                )
            )
        )
        if not "!temp_args!"=="" set "args=!args! !temp_args!"
    )
)
call :tcp_enable
call :game_switch_status
set ARGS=%args%
call set "ARGS=%%ARGS:EXCL_MARK=^!%%"
echo Final args: !ARGS!
set SRVCNAME=zapret
net stop %SRVCNAME% >nul 2>&1
sc delete %SRVCNAME% >nul 2>&1
sc create %SRVCNAME% binPath= "\"%BIN_PATH%winws.exe\" !ARGS!" DisplayName= "zapret" start= auto
sc description %SRVCNAME% "Zapret DPI bypass software"
sc start %SRVCNAME%
for %%F in ("%selectedFile%") do set "filename=%%~nF"
reg add "HKLM\System\CurrentControlSet\Services\zapret" /v zapret-discord-youtube /t REG_SZ /d "%filename%" /f
exit /b

:service_check_updates
chcp 437 > nul
set "GITHUB_VERSION_URL=https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/main/.service/version.txt"
set "GITHUB_RELEASE_URL=https://github.com/Flowseal/zapret-discord-youtube/releases/tag/"
set "GITHUB_DOWNLOAD_URL=https://github.com/Flowseal/zapret-discord-youtube/releases/latest"
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Invoke-WebRequest -Uri \"%GITHUB_VERSION_URL%\" -Headers @{\"Cache-Control\"=\"no-cache\"} -UseBasicParsing -TimeoutSec 5).Content.Trim()" 2^>nul') do set "GITHUB_VERSION=%%A"
if not defined GITHUB_VERSION (
    echo Warning: failed to fetch the latest version. This warning does not affect the operation of zapret
    timeout /T 2 >nul
    if "%1"=="soft" exit /b
    exit /b
)
if "%LOCAL_VERSION%"=="%GITHUB_VERSION%" (
    echo Latest version installed: %LOCAL_VERSION%
    if "%1"=="soft" exit /b
    exit /b
)
echo New version available: %GITHUB_VERSION%
echo Release page: %GITHUB_RELEASE_URL%%GITHUB_VERSION%
echo Opening the download page...
start "" "%GITHUB_DOWNLOAD_URL%"
if "%1"=="soft" exit /b
exit /b

:service_diagnostics
chcp 437 > nul
sc query BFE | findstr /I "RUNNING" > nul
if !errorlevel!==0 ( call :PrintGreen "Base Filtering Engine check passed" ) else ( call :PrintRed "[X] Base Filtering Engine is not running. This service is required for zapret to work" )
echo:
set "proxyEnabled=0"
set "proxyServer="
for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2^>nul ^| findstr /i "ProxyEnable"') do if "%%B"=="0x1" set "proxyEnabled=1"
if !proxyEnabled!==1 (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2^>nul ^| findstr /i "ProxyServer"') do set "proxyServer=%%B"
    call :PrintYellow "[?] System proxy is enabled: !proxyServer!"
    call :PrintYellow "Make sure it's valid or disable it if you don't use a proxy"
) else call :PrintGreen "Proxy check passed"
echo:
netsh interface tcp show global | findstr /i "timestamps" | findstr /i "enabled" > nul
if !errorlevel!==0 ( call :PrintGreen "TCP timestamps check passed" ) else (
    call :PrintYellow "[?] TCP timestamps are disabled. Enabling timestamps..."
    netsh interface tcp set global timestamps=enabled > nul 2>&1
    if !errorlevel!==0 ( call :PrintGreen "TCP timestamps successfully enabled" ) else ( call :PrintRed "[X] Failed to enable TCP timestamps" )
)
echo:
tasklist /FI "IMAGENAME eq AdguardSvc.exe" | find /I "AdguardSvc.exe" > nul
if !errorlevel!==0 (
    call :PrintRed "[X] Adguard process found. Adguard may cause problems with Discord"
    call :PrintRed "https://github.com/Flowseal/zapret-discord-youtube/issues/417"
) else call :PrintGreen "Adguard check passed"
echo:
sc query | findstr /I "Killer" > nul
if !errorlevel!==0 (
    call :PrintRed "[X] Killer services found. Killer conflicts with zapret"
    call :PrintRed "https://github.com/Flowseal/zapret-discord-youtube/issues/2512#issuecomment-2821119513"
) else call :PrintGreen "Killer check passed"
echo:
sc query | findstr /I "Intel" | findstr /I "Connectivity" | findstr /I "Network" > nul
if !errorlevel!==0 (
    call :PrintRed "[X] Intel Connectivity Network Service found. It conflicts with zapret"
    call :PrintRed "https://github.com/ValdikSS/GoodbyeDPI/issues/541#issuecomment-2661670982"
) else call :PrintGreen "Intel Connectivity check passed"
echo:
set "checkpointFound=0"
sc query | findstr /I "TracSrvWrapper" > nul && set "checkpointFound=1"
sc query | findstr /I "EPWD" > nul && set "checkpointFound=1"
if !checkpointFound!==1 (
    call :PrintRed "[X] Check Point services found. Check Point conflicts with zapret"
    call :PrintRed "Try to uninstall Check Point"
) else call :PrintGreen "Check Point check passed"
echo:
sc query | findstr /I "SmartByte" > nul
if !errorlevel!==0 (
    call :PrintRed "[X] SmartByte services found. SmartByte conflicts with zapret"
    call :PrintRed "Try to uninstall or disable SmartByte through services.msc"
) else call :PrintGreen "SmartByte check passed"
echo:
set "BIN_PATH=%~dp0bin\"
if not exist "%BIN_PATH%\*.sys" call :PrintRed "WinDivert64.sys file NOT found."
echo:
set "VPN_SERVICES="
sc query | findstr /I "VPN" > nul
if !errorlevel!==0 (
    for /f "tokens=2 delims=:" %%A in ('sc query ^| findstr /I "VPN"') do (
        if not defined VPN_SERVICES ( set "VPN_SERVICES=!VPN_SERVICES!%%A" ) else ( set "VPN_SERVICES=!VPN_SERVICES!,%%A" )
    )
    call :PrintYellow "[?] VPN services found:!VPN_SERVICES!. Some VPNs can conflict with zapret"
    call :PrintYellow "Make sure that all VPNs are disabled"
) else call :PrintGreen "VPN check passed"
echo:
set "dohfound=0"
for /f "delims=" %%a in ('powershell -NoProfile -Command "Get-ChildItem -Recurse -Path 'HKLM:System\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\' | Get-ItemProperty | Where-Object { $_.DohFlags -gt 0 } | Measure-Object | Select-Object -ExpandProperty Count"') do if %%a gtr 0 set "dohfound=1"
if !dohfound!==0 (
    call :PrintYellow "[?] Make sure you have configured secure DNS in a browser with some non-default DNS service provider,"
    call :PrintYellow "If you use Windows 11 you can configure encrypted DNS in the Settings to hide this warning"
) else call :PrintGreen "Secure DNS check passed"
echo:
set "hostsFile=%SystemRoot%\System32\drivers\etc\hosts"
if exist "%hostsFile%" (
    set "yt_found=0"
    >nul 2>&1 findstr /I "youtube.com" "%hostsFile%" && set "yt_found=1"
    >nul 2>&1 findstr /I "yotou.be" "%hostsFile%" && set "yt_found=1"
    if !yt_found!==1 call :PrintYellow "[?] Your hosts file contains entries for youtube.com or yotou.be. This may cause problems with YouTube access"
)
tasklist /FI "IMAGENAME eq winws.exe" | find /I "winws.exe" > nul
set "winws_running=!errorlevel!"
sc query "WinDivert" | findstr /I "RUNNING STOP_PENDING" > nul
set "windivert_running=!errorlevel!"
if !winws_running! neq 0 if !windivert_running!==0 (
    call :PrintYellow "[?] winws.exe is not running but WinDivert service is active. Attempting to delete WinDivert..."
    net stop "WinDivert" >nul 2>&1
    sc delete "WinDivert" >nul 2>&1
    sc query "WinDivert" >nul 2>&1
    if !errorlevel!==0 (
        call :PrintRed "[X] Failed to delete WinDivert. Checking for conflicting services..."
        set "conflicting_services=GoodbyeDPI"
        set "found_conflict=0"
        for %%s in (!conflicting_services!) do (
            sc query "%%s" >nul 2>&1
            if !errorlevel!==0 (
                call :PrintYellow "[?] Found conflicting service: %%s. Stopping and removing..."
                net stop "%%s" >nul 2>&1
                sc delete "%%s" >nul 2>&1
                if !errorlevel!==0 ( call :PrintGreen "Successfully removed service: %%s" ) else ( call :PrintRed "[X] Failed to remove service: %%s" )
                set "found_conflict=1"
            )
        )
        if !found_conflict!==0 (
            call :PrintRed "[X] No conflicting services found. Check manually if any other bypass is using WinDivert."
        ) else (
            call :PrintYellow "[?] Attempting to delete WinDivert again..."
            net stop "WinDivert" >nul 2>&1
            sc delete "WinDivert" >nul 2>&1
            sc query "WinDivert" >nul 2>&1
            if !errorlevel! neq 0 ( call :PrintGreen "WinDivert successfully deleted after removing conflicting services" ) else ( call :PrintRed "[X] WinDivert still cannot be deleted. Check manually if any other bypass is using WinDivert." )
        )
    ) else call :PrintGreen "WinDivert successfully removed"
    echo:
)
set "conflicting_services=GoodbyeDPI discordfix_zapret winws1 winws2"
set "found_any_conflict=0"
set "found_conflicts="
for %%s in (!conflicting_services!) do (
    sc query "%%s" >nul 2>&1
    if !errorlevel!==0 (
        if "!found_conflicts!"=="" ( set "found_conflicts=%%s" ) else ( set "found_conflicts=!found_conflicts! %%s" )
        set "found_any_conflict=1"
    )
)
if !found_any_conflict!==1 (
    call :PrintRed "[X] Conflicting bypass services found: !found_conflicts!"
    set "CHOICE="
    set /p "CHOICE=Do you want to remove these conflicting services? (Y/N) (default: N) "
    if "!CHOICE!"=="" set "CHOICE=N"
    if "!CHOICE!"=="y" set "CHOICE=Y"
    if /i "!CHOICE!"=="Y" (
        for %%s in (!found_conflicts!) do (
            call :PrintYellow "Stopping and removing service: %%s"
            net stop "%%s" >nul 2>&1
            sc delete "%%s" >nul 2>&1
            if !errorlevel!==0 ( call :PrintGreen "Successfully removed service: %%s" ) else ( call :PrintRed "[X] Failed to remove service: %%s" )
        )
        net stop "WinDivert" >nul 2>&1
        sc delete "WinDivert" >nul 2>&1
        net stop "WinDivert14" >nul 2>&1
        sc delete "WinDivert14" >nul 2>&1
    )
    echo:
)
set "CHOICE="
set /p "CHOICE=Do you want to clear the Discord cache? (Y/N) (default: Y)  "
if "!CHOICE!"=="" set "CHOICE=Y"
if "!CHOICE!"=="y" set "CHOICE=Y"
if /i "!CHOICE!"=="Y" (
    tasklist /FI "IMAGENAME eq Discord.exe" | findstr /I "Discord.exe" > nul
    if !errorlevel!==0 (
        echo Discord is running, closing...
        taskkill /IM Discord.exe /F > nul
        if !errorlevel! == 0 ( call :PrintGreen "Discord was successfully closed" ) else ( call :PrintRed "Unable to close Discord" )
    )
    set "discordCacheDir=%appdata%\discord"
    for %%d in ("Cache" "Code Cache" "GPUCache") do (
        set "dirPath=!discordCacheDir!\%%~d"
        if exist "!dirPath!" (
            rd /s /q "!dirPath!"
            if !errorlevel!==0 ( call :PrintGreen "Successfully deleted !dirPath!" ) else ( call :PrintRed "Failed to delete !dirPath!" )
        ) else call :PrintRed "!dirPath! does not exist"
    )
)
echo:
exit /b

:game_switch_status
chcp 437 > nul
set "gameFlagFile=%~dp0utils\game_filter.enabled"
if not exist "%gameFlagFile%" (
    set "GameFilterStatus=disabled"
    set "GameFilter=12"
    set "GameFilterTCP=12"
    set "GameFilterUDP=12"
    exit /b
)
set "GameFilterMode="
for /f "usebackq delims=" %%A in ("%gameFlagFile%") do if not defined GameFilterMode set "GameFilterMode=%%A"
if /i "%GameFilterMode%"=="all" (
    set "GameFilterStatus=enabled (TCP and UDP)"
    set "GameFilter=1024-65535"
    set "GameFilterTCP=1024-65535"
    set "GameFilterUDP=1024-65535"
) else if /i "%GameFilterMode%"=="tcp" (
    set "GameFilterStatus=enabled (TCP)"
    set "GameFilter=1024-65535"
    set "GameFilterTCP=1024-65535"
    set "GameFilterUDP=12"
) else (
    set "GameFilterStatus=enabled (UDP)"
    set "GameFilter=1024-65535"
    set "GameFilterTCP=12"
    set "GameFilterUDP=1024-65535"
)
exit /b

:game_switch
chcp 437 > nul
set "gameFlagFile=%~dp0utils\game_filter.enabled"
set "mode=%~1"
if "%mode%"=="disable" (
    if exist "%gameFlagFile%" del /f /q "%gameFlagFile%"
) else if "%mode%"=="all" (
    echo all>"%gameFlagFile%"
) else if "%mode%"=="tcp" (
    echo tcp>"%gameFlagFile%"
) else if "%mode%"=="udp" (
    echo udp>"%gameFlagFile%"
) else (
    echo Invalid mode. Use: disable, all, tcp, udp
    exit /b 1
)
call :PrintYellow "Restart the zapret to apply the changes"
exit /b

:check_updates_switch_status
chcp 437 > nul
set "checkUpdatesFlag=%~dp0utils\check_updates.enabled"
if exist "%checkUpdatesFlag%" ( set "CheckUpdatesStatus=enabled" ) else ( set "CheckUpdatesStatus=disabled" )
exit /b

:check_updates_switch
chcp 437 > nul
set "checkUpdatesFlag=%~dp0utils\check_updates.enabled"
if not exist "%checkUpdatesFlag%" (
    echo Enabling check updates...
    echo ENABLED > "%checkUpdatesFlag%"
) else (
    echo Disabling check updates...
    del /f /q "%checkUpdatesFlag%"
)
exit /b

:ipset_switch_status
chcp 437 > nul
set "listFile=%~dp0lists\ipset-all.txt"
for /f %%i in ('type "%listFile%" 2^>nul ^| find /c /v ""') do set "lineCount=%%i"
if !lineCount!==0 ( set "IPsetStatus=any" ) else (
    findstr /R "^203\.0\.113\.113/32$" "%listFile%" >nul
    if !errorlevel!==0 ( set "IPsetStatus=none" ) else ( set "IPsetStatus=loaded" )
)
exit /b

:ipset_switch
chcp 437 > nul
set "listFile=%~dp0lists\ipset-all.txt"
set "backupFile=%listFile%.backup"
call :ipset_switch_status
if "%IPsetStatus%"=="loaded" (
    echo Switching to none mode...
    if not exist "%backupFile%" ( ren "%listFile%" "ipset-all.txt.backup" ) else ( del /f /q "%backupFile%" & ren "%listFile%" "ipset-all.txt.backup" )
    >"%listFile%" echo 203.0.113.113/32
) else if "%IPsetStatus%"=="none" (
    echo Switching to any mode...
    >"%listFile%" rem
) else if "%IPsetStatus%"=="any" (
    echo Switching to loaded mode...
    if exist "%backupFile%" ( del /f /q "%listFile%" & ren "%backupFile%" "ipset-all.txt" ) else ( echo Error: no backup to restore. Update list first. & exit /b 1 )
)
exit /b

:ipset_update
chcp 437 > nul
set "listFile=%~dp0lists\ipset-all.txt"
set "url=https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/ipset-service.txt"
echo Updating ipset-all...
if exist "%SystemRoot%\System32\curl.exe" (
    curl -L -o "%listFile%" "%url%"
) else (
    powershell -NoProfile -Command "$url = '%url%'; $out = '%listFile%'; $dir = Split-Path -Parent $out; if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }; $res = Invoke-WebRequest -Uri $url -TimeoutSec 10 -UseBasicParsing; if ($res.StatusCode -eq 200) { $res.Content | Out-File -FilePath $out -Encoding UTF8 } else { exit 1 }"
)
echo Finished
exit /b

:hosts_update
chcp 437 > nul
set "hostsFile=%SystemRoot%\System32\drivers\etc\hosts"
set "hostsUrl=https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/hosts"
set "tempFile=%TEMP%\zapret_hosts.txt"
set "needsUpdate=0"
echo Checking hosts file...
if exist "%SystemRoot%\System32\curl.exe" (
    curl -L -s -o "%tempFile%" "%hostsUrl%"
) else (
    powershell -NoProfile -Command "$url = '%hostsUrl%'; $out = '%tempFile%'; $res = Invoke-WebRequest -Uri $url -TimeoutSec 10 -UseBasicParsing; if ($res.StatusCode -eq 200) { $res.Content | Out-File -FilePath $out -Encoding UTF8 } else { exit 1 }"
)
if not exist "%tempFile%" (
    call :PrintRed "Failed to download hosts file from repository"
    call :PrintYellow "Copy hosts file manually from %hostsUrl%"
    exit /b 1
)
set "firstLine="
set "lastLine="
for /f "usebackq delims=" %%a in ("%tempFile%") do (
    if not defined firstLine set "firstLine=%%a"
    set "lastLine=%%a"
)
findstr /C:"!firstLine!" "%hostsFile%" >nul 2>&1
if !errorlevel! neq 0 ( echo First line from repository not found in hosts file & set "needsUpdate=1" )
findstr /C:"!lastLine!" "%hostsFile%" >nul 2>&1
if !errorlevel! neq 0 ( echo Last line from repository not found in hosts file & set "needsUpdate=1" )
if "%needsUpdate%"=="1" (
    echo:
    call :PrintYellow "Hosts file needs to be updated"
    call :PrintYellow "Please manually copy the content from the downloaded file to your hosts file"
    start notepad "%tempFile%"
    explorer /select,"%hostsFile%"
) else (
    call :PrintGreen "Hosts file is up to date"
    if exist "%tempFile%" del /f /q "%tempFile%"
)
exit /b

:run_tests
chcp 437 >nul
powershell -NoProfile -Command "if ($PSVersionTable -and $PSVersionTable.PSVersion -and $PSVersionTable.PSVersion.Major -ge 3) { exit 0 } else { exit 1 }" >nul 2>&1
if %errorLevel% neq 0 (
    echo PowerShell 3.0 or newer is required.
    echo Please upgrade PowerShell and rerun this script.
    echo.
    exit /b 1
)
echo Starting configuration tests in PowerShell window...
echo.
start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0utils\test zapret.ps1"
exit /b

:: ==================== Утилиты ====================
:PrintGreen
powershell -NoProfile -Command "Write-Host \"%~1\" -ForegroundColor Green"
exit /b

:PrintRed
powershell -NoProfile -Command "Write-Host \"%~1\" -ForegroundColor Red"
exit /b

:PrintYellow
powershell -NoProfile -Command "Write-Host \"%~1\" -ForegroundColor Yellow"
exit /b

:check_command
where %1 >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] %1 not found in PATH
    echo Fix your PATH variable with instructions here https://github.com/Flowseal/zapret-discord-youtube/issues/7490
    exit /b 1
)
exit /b 0

:check_extracted
if not exist "%~dp0bin\" (
    echo Zapret must be extracted from archive first or bin folder not found for some reason
    exit /b 1
)
exit /b 0