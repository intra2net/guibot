@Echo off

SET DISTRO="windows"
SET DISTRO_VERSION="10"
SET DISTRO_ROOT="%HOMEDRIVE%"

REM Main deps
python-3.6.6-amd64.exe
REM set a temporary path variable valid inside this session
set PYTHONPATH=C:\Users\Administrator\AppData\Local\Programs\Python\Python36
set PATH=%PYTHONPATH%;%PYTHONPATH%\Scripts;%PATH%
REM a permanent path variable will be set by the executable once this batch exits

REM GuiBot deps
pip install Pillow-5.2.0-cp36-cp36m-win_amd64.whl
pip install autopy-1.0.1-cp36-cp36m-win_amd64.whl
REM extra dependency - OpenCV for comfort
pip install numpy-1.14.5-cp36-none-win_amd64.whl
pip install opencv_python-3.4.1.15-cp36-cp36m-win_amd64.whl

REM Optional proxy guibot interface deps
pip install serpent-1.25-py2.py3-none-any.whl
pip install Pyro4-4.73-py2.py3-none-any.whl

REM GuiBot setup
echo Copying GuiBot files
cd %DISTRO_ROOT%\guibot\packaging
python setup.py install
xcopy %DISTRO_ROOT%\guibot\misc %PYTHONPATH%\Lib\site-packages\guibot\misc /E /S /I /Q /V
xcopy %DISTRO_ROOT%\guibot\tests %PYTHONPATH%\Lib\site-packages\guibot\tests /E /S /I /Q /V

echo Virtuser ready to start!
REM wait for 30 seconds
ping -n 31 localhost > nul
