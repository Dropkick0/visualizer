#Requires AutoHotkey v2.0
;---------------- CONFIG -----------------
global StartTabs := 6
global TotalFields := 103
global ClipTimeoutMs := 80
global InterKeyDelay := 10
global OutputFile := A_Temp "\fm_dump.tsv"
global PreviewImg := A_ScriptDir "\app\static\previews\fm_dump_preview.png"
global PyScript := A_ScriptDir "\test_preview_with_fm_dump.py"
global PythonExe := "python"
global gShootDir := ""

; FM window match
global FMExe := "ahk_exe FileMaker Pro.exe"
global MOFTitlePart := "Master Order File"
global FOFTitlePart := "Field Order File"

; Keys
global LayoutHotkey := "+{F2}"
global LayoutJumpKey := "i"
global TabKey := "{Tab}"

; Field labels (index 1 = your field 1)
global FieldLabels := [
    "RETOUCH Img #1","RETOUCH Img #2","RETOUCH Img #3","RETOUCH Img #4",
    "RETOUCH Img #5","RETOUCH Img #6","RETOUCH Img #7","RETOUCH Img #8",
    "Directory Pose Order #","Directory Pose Image #",
    "Qty R1","Prod R1","Desc R1","Img # R1","Artist Series R1",
    "Qty R2","Prod R2","Desc R2","Img # R2","Artist Series R2",
    "Qty R3","Prod R3","Desc R3","Img # R3","Artist Series R3",
    "Qty R4","Prod R4","Desc R4","Img # R4",
    "Qty R5","Prod R5","Desc R5","Img # R5",
    "Frame# F1","Frame Qty F1","Frame Desc F1",
    "Qty R6","Prod R6","Desc R6","Img # R6",
    "Frame# F2","Frame Qty F2","Frame Desc F2",
    "Qty R7","Prod R7","Desc R7","Img # R7",
    "Frame# F3","Frame Qty F3","Frame Desc F3",
    "Qty R8","Prod R8","Desc R8","Img # R8",
    "Frame# F4","Frame Qty F4","Frame Desc F4",
    "Frame# F5","Frame Qty F5","Frame Desc F5",
    "Qty R9","Prod R9","Desc R9","Img # R9",
    "Frame# F6","Frame Qty F6","Frame Desc F6",
    "Qty R10","Prod R10","Desc R10","Img # R10",
    "Qty R11","Prod R11","Desc R11","Img # R11",
    "Qty R12","Prod R12","Desc R12","Img # R12",
    "Qty R13","Prod R13","Desc R13","Img # R13",
    "Qty R14","Prod R14","Desc R14","Img # R14",
    "Qty R15","Prod R15","Desc R15","Img # R15",
    "Qty R16","Prod R16","Desc R16","Img # R16",
    "Qty R17","Prod R17","Desc R17","Img # R17",
    "Qty R18","Prod R18","Desc R18","Img # R18"
]
;-----------------------------------------

; ====== AUTO-EXECUTE ======

gShootDir := DirSelect("", 3, "Select Photographer Folder for the Day")

if (!gShootDir) {
    MsgBox "Folder not selected – exiting."
    ExitApp
}
EnvSet "DROPBOX_ROOT", gShootDir
return

NumpadMult:: RunDump()
Esc:: ExitApp

RunDump() {
    if !ActivateFMWindow() {
        MsgBox "Can't find FileMaker Pro.", "Error", "Iconx"
        return
    }
    ClickBottomRight(200,200)

    Send LayoutHotkey
    Sleep 30
    Send LayoutJumpKey
    Sleep 60

    Loop StartTabs {
        Send TabKey
        Sleep InterKeyDelay
    }

    buffer := "Idx`tLabel`tValue`r`n"
    values := []

    Loop TotalFields {
        idx := A_Index
        val := CopyFieldFast(ClipTimeoutMs)
        val := StrReplace(val, "`r`n", " ")
        val := Trim(val, " `t`r`n")
        values.Push(val)

        label := (idx <= FieldLabels.Length) ? FieldLabels[idx] : ""
        buffer .= Format("{}`t{}`t{}`r`n", idx, label, val)

        if idx < TotalFields {
            Send TabKey
            Sleep InterKeyDelay
        }
    }

    file := FileOpen(OutputFile, "w", "UTF-8")
    file.Write(buffer)
    file.Close()


    ; Build the python command using proper Format placeholders.
    ; Pass the TSV path and the selected Dropbox folder to Python.
    ; AutoHotkey's Format() uses {} not %s, so %s produced the literal string
    ; "%s" "%s" "%s" and failed to execute.
    cmd := Format('"{}" "{}" "{}" "{}"', PythonExe, PyScript, OutputFile, gShootDir)

    RunWait cmd,, "Hide"
    if (FileExist(PreviewImg))
        Run PreviewImg
    else
        MsgBox "Preview image not found:`n" PreviewImg, "Warning", "Icon!"

    ; copy just values as TSV row if you still want that
    row := ""
    for i, v in values
        row .= (i=1 ? "" : "`t") v
    A_Clipboard := row

    MsgBox "Copied " values.Length " fields.`nSaved: " OutputFile, "Done", "Iconi"
}

CopyFieldFast(timeoutMs){
    A_Clipboard := ""
    Send "^a"
    Sleep 5
    Send "^c"
    start := A_TickCount
    while (A_Clipboard = "" && A_TickCount - start < timeoutMs)
        Sleep 5
    return A_Clipboard
}

ClickBottomRight(offsetX:=40, offsetY:=40){
    hwnd := WinActive("A")
    if !hwnd
        return
    CoordMode "Mouse","Client"
    WinGetPos(, , &w, &h, "ahk_id " hwnd)
    Click w-offsetX, h-offsetY
    CoordMode "Mouse","Screen"
}

ActivateFMWindow(){
    hwndList := WinGetList(FMExe)
    for hwnd in hwndList {
        title := WinGetTitle("ahk_id " hwnd)
        if InStr(title, MOFTitlePart) {
            WinActivate("ahk_id " hwnd)
            Sleep 50
            return True
        }
    }
    for hwnd in hwndList {
        title := WinGetTitle("ahk_id " hwnd)
        if InStr(title, FOFTitlePart) {
            WinActivate("ahk_id " hwnd)
            Sleep 50
            return True
        }
    }
    if hwndList.Length {
        WinActivate("ahk_id " hwndList[1])
        Sleep 50
        return True
    }
    return False
}
