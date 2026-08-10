@echo off
call .venv\Scripts\activate.bat

if not exist data (
  echo [!] Thu muc data\ khong ton tai - app se khong co du lieu san
)

if exist flashcard.ico (
  pyinstaller --noconfirm --windowed --onefile ^
    --icon=flashcard.ico ^
    --name "VocabTrainer" ^
    --add-data "flashcard.ico;." ^
    --add-data "data;data" ^
    main.py
) else (
  pyinstaller --noconfirm --windowed --onefile ^
    --name "VocabTrainer" ^
    --add-data "data;data" ^
    main.py
)

echo.
echo Done! File exe: dist\VocabTrainer.exe
pause