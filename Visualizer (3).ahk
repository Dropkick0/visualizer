#Requires AutoHotkey v2.0
;@Ahk2Exe-SetName Portrait Visualizer
;@Ahk2Exe-SetDescription Professional portrait order visualization tool
;@Ahk2Exe-SetVersion 1.0.0
;@Ahk2Exe-SetCopyright © 2024 Re MEMBER Photography
;============== COMPILED EXE CONFIG ==============
; When compiled, create a working directory in user's Documents
global WorkingDir := A_MyDocuments "\VisualizerWorkspace"
global OutputFile := WorkingDir "\fm_dump.tsv"
global PreviewImg := WorkingDir "\preview_output\fm_dump_preview.png"
global PyScript := WorkingDir "\test_preview_with_fm_dump.py"
global gShootDir := ""

;============== FILE INSTALLATIONS ==============
; These files will be embedded in the compiled exe and extracted during RunDump()
; FileInstall cannot use variables during compilation, so we define the structure here

;============== ORIGINAL CONFIG CONTINUES ==============
global StartTabs := 6
global TotalFields := 103
global ClipTimeoutMs := 100  ; Reduced from 80ms - faster clipboard ops
global InterKeyDelay := 50  ; Reduced from 20ms - faster field navigation

; FM window match - support both FileMaker Pro and Runtime
global FMExe := "ahk_exe FileMaker Pro.exe"
global FMRuntimeExe := "ahk_exe FileMaker Pro Runtime.exe"
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

; Start folder selector in the Dropbox PHOTOGRAPHER UPLOADS directory
StartPath := "C:\Users\remem\Re MEMBER Dropbox\PHOTOGRAPHY PROOFING\PHOTOGRAPHER UPLOADS (1)"
gShootDir := DirSelect(StartPath, 3, "Select Your Photographer's Main Folder for the Day")

if (!gShootDir) {
    MsgBox "Folder not selected – exiting."
    ExitApp
}

; Show instructions popup
MsgBox "📁 Photographer folder selected: " gShootDir "`n`n" .
      "🎯 NEXT STEPS:`n`n" .
      "• Press NUMPAD * key to run the Visualizer`n`n" .
      "• Press ESC key to cancel if needed`n`n" .
      "• Working files will be saved to: " WorkingDir "`n`n" .
      "• To change photographer folders, run this script again", 
      "Ready to Run Visualizer", "Iconi"
; Remove trailing backslash to avoid quoting issues when launching Python
if (SubStr(gShootDir, -1) == "\\")
    gShootDir := SubStr(gShootDir, 1, -1)

; Persist the selected Dropbox folder for next launch
try {
    cfgPath := A_ScriptDir "\config.json"
    cfgText := FileRead(cfgPath, "UTF-8")
    if (cfgText != "") {
        escPath := StrReplace(gShootDir, "\", "\\")
        cfgText := RegExReplace(cfgText, '("photo_root"\s*:\s*")[^"]*(")', "$1" escPath "$2")
        FileDelete cfgPath
        FileAppend cfgText, cfgPath, "UTF-8"
    }
} catch as e {
    ; ignore errors writing config
}
EnvSet "DROPBOX_ROOT", gShootDir
return

NumpadMult:: RunDump()
Esc:: ExitApp

RunDump() {
    ; Ensure working directory structure exists
    DirCreate WorkingDir
    DirCreate WorkingDir "\preview_output"
    DirCreate WorkingDir "\app"
    DirCreate WorkingDir "\Composites"
    DirCreate WorkingDir "\Frames"
    
    ; Extract embedded files if they don't exist
    if !FileExist(PyScript) {
        ExtractEmbeddedFiles()
    }
    
    ; Set working directory for Python execution (ensure absolute path)
    SetWorkingDir WorkingDir
    ; Verify we're in the right directory
    if (A_WorkingDir != WorkingDir) {
        MsgBox "Failed to set working directory to: " WorkingDir "`nCurrent: " A_WorkingDir, "Error", "Iconx"
        return
    }
    
    if !ActivateFMWindow() {
        MsgBox "Can't find FileMaker Pro or FileMaker Pro Runtime with Master Order File or Field Order File.", "Error", "Iconx"
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


    ; Build Python command without batch wrappers or extra console window
    ; Prefer pythonw.exe to suppress any console if available
    pyw := A_AppData "\Programs\Python\Python311\pythonw.exe"
    if !FileExist(pyw)
        pyw := "C:\\Python311\\pythonw.exe"
    if !FileExist(pyw)
        pyw := "pythonw.exe"  ; Fallback to PATH

    script := "test_preview_with_fm_dump.py"
    MsgBox "Starting Python visualizer...`nThe preview will open when ready.",
           "Running Visualizer", "Iconi"

    cmd := Format('"%s" "%s" "%s" "%s"', pyw, script, OutputFile, gShootDir)
    try {
        ExitCode := RunWait(cmd, WorkingDir, "Hide")

        if FileExist(PreviewImg) {
            Run PreviewImg
        } else if (ExitCode != 0) {
            MsgBox "Python exited with code " ExitCode " and no preview was found.",
                   "Preview Failed", "Iconx"
        } else {
            MsgBox "Script reported success but the preview file is missing.",
                   "Missing Preview", "Icon!"
        }
    } catch Error as e {
        MsgBox "❌ Error launching Python script:`n" e.Message "`n`n" .
               "Command: " cmd "`n`n" .
               "Working directory: " WorkingDir,
               "Error", "Iconx"
    }

    ; copy just values as TSV row if you still want that
    row := ""
    for i, v in values
        row .= (i=1 ? "" : "`t") v
    A_Clipboard := row
}

CopyFieldFast(timeoutMs){
    A_Clipboard := ""
    Send "^a"
    Sleep 3  ; Reduced from 5ms
    Send "^c"
    start := A_TickCount
    ; Check more frequently with shorter sleep for faster response
    while (A_Clipboard = "" && A_TickCount - start < timeoutMs)
        Sleep 2  ; Reduced from 5ms - check more frequently
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
    ; Get all windows and search for FileMaker-related titles
    allWindows := WinGetList()
    
    ; Arrays to store found windows
    mofWindows := []
    fofWindows := []
    allFileMakerWindows := []
    
    ; Search through all windows for FileMaker titles
    for hwnd in allWindows {
        try {
            title := WinGetTitle("ahk_id " hwnd)
            processName := WinGetProcessName("ahk_id " hwnd)
            
            ; Check if this is a FileMaker window (by process name, title, or FileMaker database names)
            isFileMaker := InStr(processName, "FileMaker") || InStr(title, "FileMaker") || InStr(title, "Field Order File") || InStr(title, "Master Order File")
            
            if (isFileMaker) {
                allFileMakerWindows.Push({hwnd: hwnd, title: title, process: processName})
                
                ; Check for Master Order File
                if InStr(title, MOFTitlePart) {
                    mofWindows.Push({hwnd: hwnd, title: title, process: processName})
                }
                
                ; Check for Field Order File
                if InStr(title, FOFTitlePart) {
                    fofWindows.Push({hwnd: hwnd, title: title, process: processName})
                }
            }
        } catch {
            ; Skip windows that can't be accessed
            continue
        }
    }
    
    ; Priority 1: Master Order File in regular FileMaker Pro (only if MOF exists)
    for window in mofWindows {
        if InStr(window.process, "FileMaker Pro") && !InStr(window.process, "Runtime") {
            WinActivate("ahk_id " window.hwnd)
            Sleep 50
            return True
        }
    }
    
    ; Priority 2: Field Order File in FileMaker Pro Runtime
    for window in fofWindows {
        if InStr(window.process, "Runtime") || InStr(window.process, "FileMaker") {
            WinActivate("ahk_id " window.hwnd)
            Sleep 50
            return True
        }
    }
    
    ; Priority 3: Any Field Order File
    for window in fofWindows {
        WinActivate("ahk_id " window.hwnd)
        Sleep 50
        return True
    }
    
    ; Priority 4: Any Master Order File
    for window in mofWindows {
        WinActivate("ahk_id " window.hwnd)
        Sleep 50
        return True
    }
    
    ; Last resort: Any FileMaker window
    if allFileMakerWindows.Length {
        WinActivate("ahk_id " allFileMakerWindows[1].hwnd)
        Sleep 50
        return True
    }
    
    return False
}



ExtractEmbeddedFiles() {
    ; Extract Python scripts
    FileInstall "test_preview_with_fm_dump.py", A_Temp "\pv_temp_script.py", 1
    FileInstall "requirements.txt", A_Temp "\pv_temp_requirements.txt", 1
    
    ; Extract app files
    FileInstall "app\__init__.py", A_Temp "\pv_app_init.py", 1
    FileInstall "app\config.py", A_Temp "\pv_app_config.py", 1
    FileInstall "app\enhanced_preview.py", A_Temp "\pv_app_enhanced.py", 1
    FileInstall "app\fm_dump_parser.py", A_Temp "\pv_app_parser.py", 1
    FileInstall "app\frame_overlay.py", A_Temp "\pv_app_overlay.py", 1
    FileInstall "app\image_search.py", A_Temp "\pv_app_search.py", 1
    FileInstall "app\ocr_extractor.py", A_Temp "\pv_app_ocr.py", 1
    FileInstall "app\order_from_tsv.py", A_Temp "\pv_app_order.py", 1
    FileInstall "app\order_utils.py", A_Temp "\pv_app_utils.py", 1
    FileInstall "app\trio_composite.py", A_Temp "\pv_app_trio.py", 1

    
    ; Extract composite images
    FileInstall "Composites\Frame Black - Black  5x10 3 Image.jpg", A_Temp "\pv_comp1.jpg", 1
    FileInstall "Composites\Frame Black - Gray  5x10 3 Image.jpg", A_Temp "\pv_comp2.jpg", 1
    FileInstall "Composites\Frame Black - Tan 5x10 3 Image.jpg", A_Temp "\pv_comp3.jpg", 1
    FileInstall "Composites\Frame Black - White  5x10 3 Image.jpg", A_Temp "\pv_comp4.jpg", 1
    FileInstall "Composites\Frame Cherry - Black  5x10 3 Image.jpg", A_Temp "\pv_comp5.jpg", 1
    FileInstall "Composites\Frame Cherry - Gray 5x10 3 Image.jpg", A_Temp "\pv_comp6.jpg", 1
    FileInstall "Composites\Frame Cherry - Tan 5x10 3 Image.jpg", A_Temp "\pv_comp7.jpg", 1
    FileInstall "Composites\Frame Cherry - White  5x10 3 Image.jpg", A_Temp "\pv_comp8.jpg", 1
    
    ; Extract frame images
    FileInstall "Frames\Black Frame.jpg", A_Temp "\pv_frame1.jpg", 1
    FileInstall "Frames\Cherry Frame.jpg", A_Temp "\pv_frame2.jpg", 1
    
    ; Extract config files
    FileInstall "POINTS SHEET & CODES.csv", A_Temp "\pv_config.csv", 1
    
    ; Now move files to proper locations
    FileCopy A_Temp "\pv_temp_script.py", WorkingDir "\test_preview_with_fm_dump.py", 1
    FileCopy A_Temp "\pv_temp_requirements.txt", WorkingDir "\requirements.txt", 1
    
    ; Copy app files
    FileCopy A_Temp "\pv_app_init.py", WorkingDir "\app\__init__.py", 1
    FileCopy A_Temp "\pv_app_config.py", WorkingDir "\app\config.py", 1
    FileCopy A_Temp "\pv_app_enhanced.py", WorkingDir "\app\enhanced_preview.py", 1
    FileCopy A_Temp "\pv_app_parser.py", WorkingDir "\app\fm_dump_parser.py", 1
    FileCopy A_Temp "\pv_app_overlay.py", WorkingDir "\app\frame_overlay.py", 1
    FileCopy A_Temp "\pv_app_search.py", WorkingDir "\app\image_search.py", 1
    FileCopy A_Temp "\pv_app_ocr.py", WorkingDir "\app\ocr_extractor.py", 1
    FileCopy A_Temp "\pv_app_order.py", WorkingDir "\app\order_from_tsv.py", 1
    FileCopy A_Temp "\pv_app_utils.py", WorkingDir "\app\order_utils.py", 1
    FileCopy A_Temp "\pv_app_trio.py", WorkingDir "\app\trio_composite.py", 1

    
    ; Copy composite images
    FileCopy A_Temp "\pv_comp1.jpg", WorkingDir "\Composites\Frame Black - Black  5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp2.jpg", WorkingDir "\Composites\Frame Black - Gray  5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp3.jpg", WorkingDir "\Composites\Frame Black - Tan 5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp4.jpg", WorkingDir "\Composites\Frame Black - White  5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp5.jpg", WorkingDir "\Composites\Frame Cherry - Black  5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp6.jpg", WorkingDir "\Composites\Frame Cherry - Gray 5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp7.jpg", WorkingDir "\Composites\Frame Cherry - Tan 5x10 3 Image.jpg", 1
    FileCopy A_Temp "\pv_comp8.jpg", WorkingDir "\Composites\Frame Cherry - White  5x10 3 Image.jpg", 1
    
    ; Copy frame images
    FileCopy A_Temp "\pv_frame1.jpg", WorkingDir "\Frames\Black Frame.jpg", 1
    FileCopy A_Temp "\pv_frame2.jpg", WorkingDir "\Frames\Cherry Frame.jpg", 1
    
    ; Copy config files
    FileCopy A_Temp "\pv_config.csv", WorkingDir "\POINTS SHEET & CODES.csv", 1
    
    ; Clean up temp files
    FileDelete A_Temp "\pv_*"
}
