import os
import sys
import platform
import glob
import ctypes
import traceback
import subprocess
import shutil

import mediapipe as mp


def validate_mediapipe():
    """
    Run a series of diagnostic checks to determine why MediaPipe native
    libraries might fail to load in Linux environments (used by Streamlit Cloud).

    Returns (ok: bool, message: str).
    """
    diagnostics = []

    try:
        diagnostics.append(f"mediapipe.__version__ = {getattr(mp, '__version__', 'unknown')}")
    except Exception as e:
        diagnostics.append(f"Could not read mediapipe.__version__: {e}")

    diagnostics.append(f"python = {sys.version}")
    diagnostics.append(f"platform = {platform.platform()}")

    # Locate mediapipe package root
    try:
        mp_file = getattr(mp, '__file__', None)
        mp_root = os.path.dirname(mp_file) if mp_file else None
        diagnostics.append(f"mediapipe.__file__ = {mp_file}")
        diagnostics.append(f"mediapipe root = {mp_root}")
    except Exception as e:
        diagnostics.append(f"Error locating mediapipe package path: {e}")
        mp_root = None

    so_candidates = []
    try:
        if mp_root:
            so_candidates = glob.glob(os.path.join(mp_root, '**', '*.so'), recursive=True)
            diagnostics.append(f"Found {len(so_candidates)} .so files under mediapipe package (showing up to 10).")
            for p in so_candidates[:10]:
                diagnostics.append(f"so candidate: {p}")
    except Exception as e:
        diagnostics.append(f"Error searching for .so files: {e}")

    # Try to load each candidate with ctypes to capture the real OSError
    load_errors = []
    for so in so_candidates:
        try:
            ctypes.CDLL(so)
            diagnostics.append(f"ctypes load OK: {so}")
        except OSError as os_err:
            load_errors.append((so, str(os_err)))
            diagnostics.append(f"ctypes load FAILED: {so}: {os_err}")
            if shutil.which('ldd'):
                try:
                    ldd_proc = subprocess.run(['ldd', so], capture_output=True, text=True)
                    diagnostics.append(f"ldd {so}:\n{ldd_proc.stdout}\n{ldd_proc.stderr}")
                except Exception as e:
                    diagnostics.append(f"ldd failed for {so}: {e}")

    # If there were no .so files found in mediapipe package, also try the mediapipe_c_bindings module location
    try:
        from mediapipe.tasks.python.core import mediapipe_c_bindings
        cb_file = getattr(mediapipe_c_bindings, '__file__', None)
        diagnostics.append(f"mediapipe_c_bindings.__file__ = {cb_file}")
        if cb_file and cb_file.endswith('.py'):
            # The loader constructs absolute .so path; search same dir for .so
            cb_root = os.path.dirname(cb_file)
            cb_sos = glob.glob(os.path.join(cb_root, '*.so'))
            for p in cb_sos:
                if p not in so_candidates:
                    so_candidates.append(p)
                    diagnostics.append(f"found cb .so: {p}")
                    try:
                        ctypes.CDLL(p)
                        diagnostics.append(f"ctypes load OK: {p}")
                    except OSError as os_err:
                        load_errors.append((p, str(os_err)))
                        diagnostics.append(f"ctypes load FAILED: {p}: {os_err}")
                        if shutil.which('ldd'):
                            try:
                                ldd_proc = subprocess.run(['ldd', p], capture_output=True, text=True)
                                diagnostics.append(f"ldd {p}:\n{ldd_proc.stdout}\n{ldd_proc.stderr}")
                            except Exception as e:
                                diagnostics.append(f"ldd failed for {p}: {e}")
    except Exception as e:
        diagnostics.append(f"Could not import mediapipe.tasks.python.core.mediapipe_c_bindings: {e}")

    # Build a helpful message
    if load_errors:
        msg_lines = [
            "MediaPipe native library load failures detected.",
            "Below are the collected diagnostics (first see the ctypes load failures):",
            "",
        ]
        for so, err in load_errors:
            msg_lines.append(f"FAILED: {so}\n  -> {err}\n")
        msg_lines.append("--- FULL DIAGNOSTICS ---")
        msg_lines.extend(diagnostics)
        return False, '\n'.join(msg_lines)

    # If there were .so files and none failed to load via ctypes, return success
    if so_candidates:
        msg = "MediaPipe native shared libraries appear to be present and loadable on this host.\n"
        msg += "If Streamlit still fails in a worker process, the issue could be an incompatible wheel vs. system libraries.\n"
        msg += "Diagnostics:\n" + '\n'.join(diagnostics[:50])
        return True, msg

    # No .so found => likely wheel didn't include native libs or installed a pure-python stub
    msg_lines = [
        "No MediaPipe native .so libraries were found in the installed package.",
        "This suggests the installed mediapipe wheel is incompatible with the platform or the wheel installation failed.",
        "Diagnostics:",
    ]
    msg_lines.extend(diagnostics)
    return False, '\n'.join(msg_lines)
