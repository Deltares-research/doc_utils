import os
import subprocess
import sys

from pypandoc.pandoc_download import download_pandoc

def check_pandoc_installed() -> bool:
    """Check if Pandoc is installed and available.

    Returns:
        True if Pandoc is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Found Pandoc: {result.stdout.split()[1]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Pandoc not found. Downloading...")
        download_pandoc()

        # Add pandoc to PATH
        pandoc_dir = _get_pandoc_dir()
        if pandoc_dir and os.path.exists(pandoc_dir):
            if pandoc_dir not in os.environ['PATH']:
                os.environ['PATH'] = pandoc_dir + os.pathsep + os.environ['PATH']
                print(f"Added pandoc to PATH: {pandoc_dir}")

            # Verify it's now accessible
            try:
                subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
                print("Pandoc is now accessible!")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"Warning: Pandoc downloaded but not accessible. Manual PATH setup may be needed.")
                print(f"Pandoc location: {pandoc_dir}")
                return False
        return False

def _get_pandoc_dir():
    """Get the directory where pypandoc downloads pandoc."""
    import pypandoc
    try:
        pandoc_path = pypandoc.get_pandoc_path()
        return os.path.dirname(pandoc_path)
    except:
        # Fallback to common locations
        if sys.platform == 'win32':
            return os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Pandoc')
        else:
            return os.path.join(os.path.expanduser('~'), '.local', 'bin')

