import subprocess

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
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Pandoc not found. Downloading...")
        download_pandoc()

