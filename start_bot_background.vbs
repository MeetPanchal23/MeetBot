Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Run pythonw.exe completely hidden in the background (0 = hidden window)
WshShell.CurrentDirectory = strPath
WshShell.Run "pythonw main.py", 0, False
