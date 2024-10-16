SET DISTRO="windows"
SET DISTRO_VERSION="10"
SET DISTRO_ROOT="%HOMEDRIVE%"

REM AutoPy is not available for Python3.9 at present
SET DISABLE_AUTOPY=1
REM Tesseract doesn't have original installers for Windows
SET DISABLE_OCR=1
REM Drag/drop with the current default DC backend is not supported on Windows
SET DISABLE_DRAG=1
REM Requires X server and thus only available on Linux
SET DISABLE_XDOTOOL=1
REM Requires VNC server and thus only available on Linux
SET DISABLE_VNCDOTOOL=1

REM Main deps
REM Assuming a local python executable to avoid overloading the download web page
START /WAIT python-3.12.6-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
REM set a temporary path variable valid inside this session
set PYTHONPATH="C:\Program Files\Python312"
set PATH=%PYTHONPATH%;%PYTHONPATH%\Scripts;%PATH%
REM a permanent path variable will be set by the executable once this batch exits

REM Install the vc_redist for C++ silently
REM Assuming a local executable to avoid overloading the download web page
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'C:\packages\vc_redist.x64.exe' -ArgumentList '/q' -Wait"

REM GuiBot deps
pip install --user --upgrade pip
pip install -r %DISTRO_ROOT%\guibot\packaging\pip_requirements.txt
pip install setuptools

REM GuiBot setup
echo Copying GuiBot files
cd %DISTRO_ROOT%\guibot\packaging
python setup.py install
xcopy %DISTRO_ROOT%\guibot\misc %PYTHONPATH%\Lib\site-packages\guibot\misc /E /S /I /Q /V
xcopy %DISTRO_ROOT%\guibot\tests %PYTHONPATH%\Lib\site-packages\guibot\tests /E /S /I /Q /V

REM Run all unit tests
cd %PYTHONPATH%\Lib\site-packages\guibot\tests
python -m unittest discover -v -s ../tests/
