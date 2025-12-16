# Installation Guide using the Zip File

This guide explains how to install the CIP-tool from a zip file containing all necessary components. 
This method is for users who received the complete package (zip file).

## Table of Contents

1. [What's Included](#whats-included)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Verifying Installation](#verifying-installation)
6. [Next Steps](#next-steps)

---

## What's Included

The zip file contains:

- **Wheel file** (`.whl`) - The CIP-tool Python package
- **bin/** - External dependencies (RGWM and DIMR runners)
  - `rgwm_versie2.4.3/` - Randvoorwaarden Generator Water Modellen
  - `dimr_runners/sobek_dimr/` - DIMR with Sobek support
  - `SingleRunner/` - SingleRunner wheel (if applicable)
- **examples/** - Example configuration and input files
  - `config.yaml` - Pre-configured example
  - `inputs/` - Sample input files
  - `test_model/` - Example model for testing

---

## Prerequisites

Before installing CIP-tool, ensure you have:

- **Python 3.11.x** - The tool requires Python version 3.11
- **pip** - Python package installer (usually included with Python)
- **Windows OS** - Required for running Sobek simulations

### Check Your Python Version

```powershell
python --version
```

You should see output like: `Python 3.11.x`

If you don't have Python 3.11, you'll need to install it from the official Python installer or contact your system administrator.

### Install with Conda (Optional)

If you prefer using Conda for Python environment management, you can create a dedicated environment for CIP-tool with Python 3.11:

1. **Create a new conda environment:**
   ```powershell
   conda create -n cip-tool python=3.11
   ```

2. **Activate the environment:**
   ```powershell
   conda activate cip-tool
   ```

3. **Verify the Python version:**
   ```powershell
   python --version
   ```

Once activated, you can proceed with the installation steps below using this conda environment. Remember to activate the environment each time you want to use CIP-tool.

---

## Installation Steps

### Step 1: Extract the Zip File

1. Locate the downloaded zip file (e.g., `CIP-tool-offline-v1.1.0.zip`)
2. Extract it to a location on your system, for example:
   ```
   C:\tools\CIP-tool\
   ```

After extraction, your directory should look like:

```
C:\tools\CIP-tool\
├── CIP_tool-1.1.0-py3-none-any.whl
├── bin/
│   ├── dimr_runners/
│   │   └── sobek_dimr/
│   │       └── x64/
│   ├── rgwm_versie2.4.3/
│   │   ├── bin/
│   │   │   └── rgwm.exe
│   │   ├── data/
│   │   └── ...
│   └── SingleRunner/
│       └── singlerunner-2.0.1-py3-none-any.whl
└── examples/
    ├── config.yaml
    ├── inputs/
    └── test_model/
```

### Step 2: Install the Wheel

Open PowerShell or Command Prompt and navigate to the extraction directory:

```powershell
cd C:\tools\CIP-tool
```

Install the CIP-tool wheel using pip:

```powershell
pip install CIP_tool-1.1.0-py3-none-any.whl
```

> **Note:** Replace `1.1.0` with the actual version number in your wheel file name.


### Step 3: Verify Installation

Check that the installation was successful:

```powershell
cip-tool --version
```

You should see the installed version number.

---

## Configuration

### Update Configuration File

Edit the `config.yaml` file to point to the correct paths for the external tools.

If you extracted to `C:\tools\CIP-tool\`, your `config.yaml` should look like:

```yaml
DIMR:
    path: C:/tools/CIP-tool/bin/dimr_runners/sobek_dimr/x64/dimr/scripts

RGWM:
    path: C:/tools/CIP-tool/bin/rgwm_versie2.4.3/bin/rgwm.exe
```

> **Important:** 
> - Use forward slashes (`/`) in paths, even on Windows, or use escaped backslashes (`\\`)
> - Adjust the paths if you extracted to a different location

### Verify Tool Paths

Check that the paths in your config file are correct (open a powershell and type the following commands):

1. **Verify RGWM executable exists:**
   ```powershell
   Test-Path C:\tools\CIP-tool\bin\rgwm_versie2.4.3\bin\rgwm.exe
   ```

2. **Verify DIMR scripts folder exists:**
   ```powershell
   Test-Path C:\tools\CIP-tool\bin\dimr_runners\sobek_dimr\x64\dimr\scripts
   ```

Both commands should return `True`.

---

## Verifying Installation

### Test CIP-tool Commands

1. **Check version:**
   ```powershell
   cip-tool --version
   ```

2. **View available commands:**
   ```powershell
   cip-tool --help
   ```

### Run a Test Scenario

If you have the complete examples folder, you can test the full workflow:

```powershell
# Generate boundary conditions
cip-tool generate -i examples/inputs/invoer_CIP_tabel.csv -o output

# Run Sobek simulation 
cip-tool run-sobek -o output

# extract results
cip-tool extract -i examples/inputs/variabelen_voor_bc_file_deelmodel.csv -o examples/inputs/results-to-extract/rmm_results
```
---

## Directory Structure Reference

Your working project structure should follow this pattern:

```
your-project/
├── config.yaml              # Configuration file (points to bin/ folder)
├── inputs/
│   ├── invoer_CIP_tabel.csv              # Input scenarios
│   └── variabelen_voor_bc_file_deelmodel.csv  # Variables config
├── output/                  # Output directory (created automatically)
│   ├── rgwm_results/
│   └── rmm_results/
└── test_model/              # Your Sobek model (if running simulations)
    ├── dimr.xml
    └── dflow1d/
```

The `bin/` folder can remain in the extraction location (e.g., `C:\tools\CIP-tool\bin\`) and be referenced from multiple projects via their `config.yaml` files.

---

## Next Steps

After installation:

1. **Read the next chapter `Command Line Interface`** to learn how to use CIP-tool commands
3. **Explore the examples folder** to understand the input file formats
4. **Prepare your own scenario data** following the example formats
5. **Start using CIP-tool** with your models

---

## Troubleshooting

### Python Not Found

If you get "python is not recognized":

1. Make sure Python 3.11 is installed
2. Add Python to your PATH environment variable
3. Try using `py -3.11` instead of `python`

### Wheel Installation Fails

If pip fails to install the wheel:

1. Ensure you have pip installed: `python -m ensurepip --upgrade`
2. Try upgrading pip: `python -m pip install --upgrade pip`
3. Use the full pip command: `python -m pip install CIP_tool-1.1.0-py3-none-any.whl`

### External Tools Not Found

If CIP-tool can't find RGWM or DIMR:

1. Verify the paths in your `config.yaml` are correct
2. Use absolute paths in the config file
3. Make sure the executables exist at the specified locations
4. Check file permissions (executables should be runnable)

### Permission Issues

If you get permission errors:

1. Run PowerShell as Administrator
2. Or install to a user directory: `pip install --user CIP_tool-1.1.0-py3-none-any.whl`

---

## Need Help?

For additional support:

- Contact support: software.support@deltares.nl

---

## Updating CIP-tool

To update to a newer version:

1. Uninstall the current version:
   ```powershell
   pip uninstall cip-tool
   ```

2. Install the new wheel file:
   ```powershell
   pip install CIP_tool-X.X.X-py3-none-any.whl
   ```

3. Update the `bin/` folder if new versions of external tools are included

> **Note:** Your configuration files and project data will not be affected by the update.

