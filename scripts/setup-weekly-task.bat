@echo off
REM Creates a Windows Task Scheduler job to run the weekly trial update
REM Run this ONCE as administrator: right-click > Run as administrator

schtasks /create ^
  /tn "TrialFinder Weekly Update" ^
  /tr "\"C:\Program Files\Git\bin\bash.exe\" \"C:\Users\sunny\projects\trialfinder\scripts\weekly-update.sh\"" ^
  /sc weekly ^
  /d SUN ^
  /st 03:00 ^
  /rl HIGHEST ^
  /f

echo.
echo Task created: "TrialFinder Weekly Update"
echo Schedule: Every Sunday at 3:00 AM
echo.
echo To test it now:  schtasks /run /tn "TrialFinder Weekly Update"
echo To check status: schtasks /query /tn "TrialFinder Weekly Update"
echo To remove it:    schtasks /delete /tn "TrialFinder Weekly Update" /f
echo.
pause
