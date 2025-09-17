#!/usr/bin/env python3
"""Direct executable script for doq with proper Unicode handling."""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def setup_unicode_console():
    """Setup Unicode console support on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes

            # Set console to UTF-8 mode
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)  # UTF-8
            kernel32.SetConsoleCP(65001)        # UTF-8

            # Set environment
            os.environ["PYTHONIOENCODING"] = "utf-8"

        except Exception:
            pass

def get_unicode_args():
    """Get command line arguments with proper Unicode encoding on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            # Get command line as Unicode
            GetCommandLineW = ctypes.windll.kernel32.GetCommandLineW
            GetCommandLineW.restype = wintypes.LPWSTR

            CommandLineToArgvW = ctypes.windll.shell32.CommandLineToArgvW
            CommandLineToArgvW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(ctypes.c_int)]
            CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)

            cmd_line = GetCommandLineW()
            argc = ctypes.c_int()
            argv_ptr = CommandLineToArgvW(cmd_line, ctypes.byref(argc))

            if argv_ptr and argc.value > 1:
                # Extract arguments, skip script name
                unicode_args = []
                for i in range(1, argc.value):
                    unicode_args.append(argv_ptr[i])

                # Free memory
                ctypes.windll.kernel32.LocalFree(argv_ptr)
                return unicode_args

        except Exception:
            pass

    # Fallback to sys.argv
    return sys.argv[1:]

if __name__ == "__main__":
    # Setup Unicode support
    setup_unicode_console()

    # Get properly encoded arguments
    args = get_unicode_args()

    # Import and run main function
    from doq.main import main
    sys.exit(main(args))
