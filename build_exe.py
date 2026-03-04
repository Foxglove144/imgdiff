import PyInstaller.__main__
import os
import shutil


def build():
    # Clean previous builds to ensure a fresh compile
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)
    if os.path.exists("dist"):
        shutil.rmtree("dist", ignore_errors=True)

    # PyInstaller options
    opts = [
        "imgdiff_gui.py",  # Your main script
        "--name=ImgDiff",  # Name of the executable
        "--onefile",  # Bundle everything into a single .exe file
        "--windowed",  # No console window (GUI mode)
        "--clean",  # Clean PyInstaller cache
        "--noconfirm",  # Overwrite output directory without asking
    ]

    # Automatically collect tkinterdnd2 files if the library is installed
    try:
        import tkinterdnd2

        print("tkinterdnd2 detected. Collecting hooks...")
        opts.append("--collect-all=tkinterdnd2")
    except ImportError:
        print("tkinterdnd2 not found. Building without drag-and-drop support.")

    PyInstaller.__main__.run(opts)


if __name__ == "__main__":
    build()
