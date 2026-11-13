@echo off
title CodeOpen - Instalacao
cd /d "%~dp0"

echo ===================================================
echo  CodeOpen - Instalacao de Dependencias
echo  by OFICINA-DO-BERG
echo ===================================================
echo.

echo [1/3] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Por favor instale Python 3.8 ou superior:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
python --version
echo OK - Python encontrado
echo.

echo [2/3] Instalando dependencias...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.

if errorlevel 1 (
    echo [ERRO] Falha na instalacao!
    echo.
    pause
    exit /b 1
)

echo [3/3] Verificando instalacao...
echo.
python -c "import psutil, requests; print('OK - Todas as dependencias estao prontas')"
echo.

if errorlevel 1 (
    echo [AVISO] Algumas bibliotecas podem nao ter sido instaladas corretamente
    echo.
) else (
    echo ===================================================
    echo  INSTALACAO CONCLUIDA COM SUCESSO!
    echo ===================================================
    echo.
    echo Proximos passos:
    echo 1. Certifique-se de ter o Cloudflare WARP instalado: https://1.1.1.1/
    echo    (NOTA: Voce NAO precisa configurar proxy ou porta 40000 manualmente.
    echo     O CodeOpen configura o proxy local 40000 de forma 100% automatica!)
    echo 2. Execute: INICIAR.bat
    echo.
)

pause
