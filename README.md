# Visualizer Debugging

If the visualizer fails to generate a preview the easiest way to diagnose the problem is to check the `python_err.log` file. The AutoHotkey launcher writes all Python output to this file inside the working directory. Open it with a text editor after a failed run to see the full traceback. Common top-line messages include:

| Traceback line | Meaning |
| -------------- | ------- |
| `ModuleNotFoundError: No module named 'PIL'` | Pillow not installed. Run `pip install pillow opencv-python flask loguru`. |
| `FileNotFoundError: Composites\Frame Cherry - Tan 10x20 3 Image.jpg` | A required asset is missing or the path is wrong. |
| `OSError: [WinError 193] %1 is not a valid Win32 application` | The wrong Python executable was used. |

The launcher now checks the Windows registry for a CPython 3.11 install before
falling back to bundled paths or the `py.exe` launcher. If you still get a
"system cannot find the file specified" message, verify that a standard Python
installation exists or adjust the registry lookup to match your version.

Once the exception is known the fix is usually a one‑liner. After applying the fix run the preview again and re-check `python_err.log` for any new errors.
