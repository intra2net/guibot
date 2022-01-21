@Echo off

SET DISTRO="windows"
SET DISTRO_VERSION="10"
SET DISTRO_ROOT="%HOMEDRIVE%"

REM Main deps
cd %DISTRO_ROOT%\
REM Assuming a local python executable to avoid overloading the download web page
START /WAIT python-3.9.0-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
REM set a temporary path variable valid inside this session
set PYTHONPATH="C:\Program Files\Python39"
set PATH=%PYTHONPATH%;%PYTHONPATH%\Scripts;%PATH%
REM a permanent path variable will be set by the executable once this batch exits

REM GuiBot deps
pip install --user --upgrade pip
pip install -r %DISTRO_ROOT%\guibot\packaging\pip_requirements.txt

REM GuiBot setup
echo Copying GuiBot files
cd %DISTRO_ROOT%\guibot\packaging
python setup.py install
xcopy %DISTRO_ROOT%\guibot\misc %PYTHONPATH%\Lib\site-packages\guibot\misc /E /S /I /Q /V
xcopy %DISTRO_ROOT%\guibot\tests %PYTHONPATH%\Lib\site-packages\guibot\tests /E /S /I /Q /V

REM Run all unit tests
cd %PYTHONPATH%\Lib\site-packages\guibot\tests
python -m unittest discover -v -s ../tests/
