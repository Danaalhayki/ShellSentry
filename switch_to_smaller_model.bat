@echo off
echo ========================================
echo Switching to Smaller Model
echo ========================================
echo.
echo Step 1: Pull a smaller model
echo This will download llama3.2:1b (~1.3 GB)
echo.
pause
ollama pull llama3.2:1b
echo.
echo Step 2: Updating .env file...
powershell -Command "(Get-Content .env) -replace 'LLM_MODEL=llama2', 'LLM_MODEL=llama3.2:1b' | Set-Content .env"
echo.
echo Done! Model switched to llama3.2:1b
echo.
echo Now restart your Flask app and try again!
pause

