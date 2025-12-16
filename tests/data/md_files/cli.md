# Command Line Interface (CLI)

The CIP-tool provides a powerful command-line interface for generating, running, and extracting boundary conditions for hydraulic models. This guide covers all available commands, their options, and detailed usage examples.

## Overview

The CIP-tool CLI consists of three main commands:

1. **`generate`** - Generate boundary conditions from input scenarios
2. **`run-sobek`** - Execute Sobek hydraulic model simulations
3. **`extract`** - Process and extract boundary conditions for a nested model

### General Usage

```bash
cip-tool [--version] [--help] <command> [<args>]
```

### Getting Help

View general help:
```bash
cip-tool --help
```

View help for a specific command:
```bash
cip-tool generate --help
cip-tool run-sobek --help
cip-tool extract --help
```

Check version:
```bash
cip-tool --version
```

---

## Commands

### 1. Generate Command

The `generate` command creates boundary conditions for hydraulic models based on input scenario data. The CIP-tool is configured to create boundary conditions for a 1D SOBEK model for the Rhine-Meuse estuary (**sobek-rmm-j15_5-v4**). Under the hood, the CIP-tool creates the boundary conditions with the Randvoorwaarden Generator Water Modellen (**RGWM**). It sets all the input files for the RGWM and executes it.

Typically, the scenarios to consider are so-called 'Conditionele Illustratie Punten' (CIP's). These are the scenarios that have to be studied in the context of permitting for projects in the Dutch main rivers. The tool can also be used to create other scenarios.



#### Syntax

```bash
cip-tool generate -i INPUT_FILE -o OUTPUT_DIR [-c CONFIG_FILE] [--calculate-surge]
```

#### Arguments

| Argument | Short | Long | Required | Description |
|----------|-------|------|----------|-------------|
| Input file | `-i` | `--input-file` | Yes | Path to the CSV file containing scenario data |
| Output directory | `-o` | `--output-dir` | Yes | Path to output directory (created if it doesn't exist) |
| Config file | `-c` | `--config` | No | Path to custom config.yaml file |
| Calculate surge | | `--calculate-surge` | No | Enable iterative boundary condition generation |

#### Input File Format

The scenarios to consider are configured in a CSV input file. This file must contain the following columns, each row of the file contains the inut for one scenario:

| Column | Description | Unit | Required |
|--------|-------------|------|----------|
| Scenario | Scenario identifier/number | - | Yes |
| Keringstoestand[open/gesloten] | Barrier state (open/closed) | - | Yes |
| Rijnafvoer te Lobith[m3/s] | Rhine discharge at Lobith | m³/s | Yes |
| Maasafvoer te Lith[m3/s] | Meuse discharge at Lith | m³/s | Yes |
| Stormopzet[m + NAP] | Maximum storm surge | m + NAP | Only without `--calculate-surge` |
| Zeewaterstand[m + NAP] | Maximum total sea water level | m + NAP | Only with `--calculate-surge` |
| Windsnelheid[m/s] | Wind speed | m/s | Yes |
| Windrichting[-] | Wind direction | - | Yes |



**Example input file (`invoer_CIP_tabel.csv`):**

```csv
Scenario,Keringstoestand[open/gesloten],Rijnafvoer te Lobith[m3/s],Maasafvoer te Lith[m3/s],Stormopzet[m + NAP],Zeewaterstand[m + NAP],Windsnelheid[m/s],Windrichting[-]
1,Open,9000,1861,3,5,19.38,WNW
2,Gesloten,11500,2448,4.5,6,27.41,WNW
```

#### Using the `--calculate-surge` flag

To generate the correct waterlevel timeseries at the downstream boundaries, the user should choose one of two options:
1. Enter the maximum amount of storm surge in the column `Stormopzet[m + NAP]` and run the `generate` command **without** the flag `--calculate-surge`. The resulting downstream water level for each scenario is the sum of astronomical tides, sea level rise and the amount of storm surge entered in the input file. The storm surge is variable in time and reaches the set maximum. 
2. Enter the maximum total water level at the Maasmondin the column `Zeewaterstand[m + NAP]` and the run the `generate` command **with** the flag `--calculate-surge`. The CIP tool will now calculate the amount of max storm surge that together with astronomical tides and sea level rise reaches the expected maximum water level. This option should be taken when creating scenarios for set CIP's in permitting projects.


When `--calculate-surge` is enabled:

1. The tool performs iterative simulations to find the correct storm surge values
2. Each iteration adjusts the surge to match target water levels
3. The process continues until convergence (typically 3-5 iterations)
4. Final adjusted surge values are saved for the model runs
5. The column `Zeewaterstand[m + NAP]` becomes **required** in the input file

#### Output

The command creates the following outputs in the specified directory:

- `rgwm_results/` - RGWM model input files and scenarios
- `rmm_results/` - RMM model setup, including boundary conditions and batch files to run the models.
- Scenario-specific folders (e.g., `Q0/`, `Q1/`, etc.)
- Log files and configuration files

#### Examples

##### Basic Generation (Default Configuration)

Generate boundary conditions using default tool paths:

```bash
cip-tool generate -i examples/inputs/invoer_CIP_tabel.csv -o output
```

**Output:**
```
Done.
```

##### Generation with Custom Configuration

Use a custom configuration file to specify tool paths:

```bash
cip-tool generate -i examples/inputs/invoer_CIP_tabel.csv -o output -c examples/config.yaml
```

##### Generation with Surge Calculation

Enable iterative surge calculation to achieve target water levels:

```bash
cip-tool generate -i examples/inputs/invoer_CIP_tabel.csv -o output --calculate-surge
```

**Output:**
```
Iteratie 1
Done.
Maximale waterstand in scenario Q0: 3.71 m +NAP
Verschil met beoogde CIP maximale waterstand: -1.29 m + NAP
Maximale waterstand in scenario Q1: 5.14 m +NAP
Verschil met beoogde CIP maximale waterstand: -0.86 m + NAP
Iteratie 2
Done.
Maximale waterstand in scenario Q0: 4.94 m +NAP
Verschil met beoogde CIP maximale waterstand: -0.06 m + NAP
Maximale waterstand in scenario Q1: 5.98 m +NAP
Verschil met beoogde CIP maximale waterstand: -0.02 m + NAP
Iteratie 3
Done.
Maximale waterstand in scenario Q0: 4.99 m +NAP
Verschil met beoogde CIP maximale waterstand: -0.01 m + NAP
Maximale waterstand in scenario Q1: 6.0 m +NAP
Verschil met beoogde CIP maximale waterstand: 0.0 m + NAP
Iteratie 4
Done.
Maximale waterstand in scenario Q0: 5.0 m +NAP
Verschil met beoogde CIP maximale waterstand: 0.0 m + NAP
Maximale waterstand in scenario Q1: 6.0 m +NAP
Verschil met beoogde CIP maximale waterstand: 0.0 m + NAP
Geconvergeerd na 4 iteraties

Beoogde CIP condities:
   Scenario  Zeewaterstand[m + NAP]
0         1                     5.0
1         2                     6.0

Condities voor RGWM:
   Scenario  Stormopzet[m + NAP]
0         1                 4.36
1         2                 5.38

Verschillen:
[0. 0.]
```



---

### 2. Run-Sobek Command

The `run-sobek` command executes Sobek hydraulic model batch jobs and streams output to both the console and a log file. For scenarios with closing storm surge barriers, the Singlerunner is employed to account for correct operation of the storm surge barriers.

#### Syntax

```bash
cip-tool run-sobek (-o OUTPUT_DIR | -b BATCH_FILE)
```

#### Arguments

You must provide **exactly one** of the following:

| Argument | Short | Long | Description |
|----------|-------|------|-------------|
| Output directory | `-o` | `--output-dir` | Path to output directory in which the models were prepare using the `generate` command earlier (the run script is auto-resolved within this file) |
| Batch file | `-b` | `--batch-file` | Direct path to the run bscript atch (.bat) file |

#### System Requirements

- **Windows only** - Batch files require Windows operating system
- Sobek/DIMR must be properly installed
- Required environment variables should be set

#### Behavior

- Executes the Sobek batch file through Windows command processor
- Streams all output to the console in real-time
- Saves complete log to a `.log` file next to the batch file
- Returns the exit code of the batch process
- Handles paths with spaces correctly

#### Examples

##### Run with Output Directory

Automatically locate and run the batch file in the RMM results folder:

```bash
cip-tool run-sobek -o output
```

The tool looks for the batch file at:
```
examples/output/rmm_results/bsub_joblist.bat
```

**Output:**
```
C:\...\examples\output\rmm_results>set OMP_NUM_THREADS=2

C:\...\examples\output\rmm_results>start "[started in Q0]" /d "Q0/model_output" /w /b run_sobekdimr.bat

C:\...\examples\output\rmm_results\Q0\model_output>C:\...\dimr\scripts\run_dimr.bat dimr.xml
Configfile:dimr.xml
OMP_NUM_THREADS is already defined
OMP_NUM_THREADS is 2
Working directory: C:\...\examples\output\rmm_results\Q0\model_output
executing: "C:\...\dimr\bin\dimr.exe"  dimr.xml
Dimr [2025-12-08 14:30:24.920] #0 >> Deltares, DIMR_EXE Version 2.00.00.68167M
Dimr [2025-12-08 14:30:24.987] #0 >> Deltares, DIMR_LIB Version 1.02.00.68167M
...
[Simulation progress output]
...
```

##### Run with Explicit Batch File

Directly execute a specific batch file:

```bash
cip-tool run-sobek -b examples/output/rmm_results/bsub_joblist.bat
```

##### Log File Location

The log file is automatically created alongside the batch file:

- Batch file: `examples/output/rmm_results/bsub_joblist.bat`
- Log file: `examples/output/rmm_results/bsub_joblist.log`

#### Error Handling

If the batch execution fails (non-zero exit code), the command will exit with the same error code:

```bash
cip-tool run-sobek -o output
# Returns non-zero exit code on failure
```

---

### 3. Extract Command

The `extract` command processes simulation results and extracts boundary condition data for a nested model. By default, the CIP-tool is configured to generate boundary conditions for the 2D D-HYDRO model of the Biesbosch. Boundary conditions that are prepared for the model are:


- Wind speed and direction
- Waterlevels at downstream boundariers
- River discharges at upstream boundaries

Lateral discharges are not created, however these can be re-used from the SOBEK model boundary conditions that were generated with the `generate` command.

#### Syntax

```bash
cip-tool extract -i INPUT_FILE -o OUTPUT_DIR [-c CONFIG_FILE]
```

#### Arguments

| Argument | Short | Long | Required | Description |
|----------|-------|------|----------|-------------|
| Input file | `-i` | `--input-file` | Yes | Path to extraction configuration CSV |
| Output directory | `-o` | `--output-dir` | Yes | Path to directory containing simulation results |
| Config file | `-c` | `--config` | No | Path to custom config.yaml file |

#### Input File Format

The extraction configuration CSV must contain the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| file | Name of the NetCDF result file | `observations.nc` |
| location | Location identifier in the model | `BE_976.00` |
| new_name_loc | New name for the location | `Beneden-Merwede_0001` |
| variabele | Variable name to extract | `water_level` |
| new_name_var | New name for the variable | `waterlevelbnd` |

**Example extraction file (`variabelen_voor_bc_file_deelmodel.csv`):**

```csv
file,location,new_name_loc,variabele,new_name_var
observations.nc,BE_976.00,Beneden-Merwede_0001,water_level,waterlevelbnd
observations.nc,WL_935.00,Waal_0001,water_discharge,dischargebnd
observations.nc,HD_983.00,Nieuwe-Merwede_0001,water_level,waterlevelbnd
observations.nc,MA_230.00,Maas_0001,water_discharge,dischargebnd
```

#### Output

The command extracts data from simulation results and creates:

- Processed boundary condition files
- Renamed and reformatted data for nested models


#### Examples

##### Basic Extraction

Extract results

```bash
cip-tool extract -i examples/inputs/variabelen_voor_bc_file_deelmodel.csv -o examples/inputs/results-to-extract/rmm_results
```

**Output:**
```
File : observations.nc Locatie : BE_976.00 Variabel : water_level
File : observations.nc Locatie : WL_935.00 Variabel : water_discharge
File : observations.nc Locatie : HD_983.00 Variabel : water_level
File : observations.nc Locatie : MA_230.00 Variabel : water_discharge
Done.
```

##### Extracting from Specific Result Directory

If results are in a subdirectory:

```bash
cip-tool extract -i examples/inputs/variabelen_voor_bc_file_deelmodel.csv -o examples/output/rmm_results
```

---

## Configuration

### Default Configuration

When the `--config` argument is **not** specified, the tool uses default paths relative to the current directory:

- **DIMR path:** `bin/dimr_runners/sobek_dimr/x64/dimr/scripts`
- **RGWM path:** `bin/rgwm_versie2.4.3/bin/rgwm.exe`

### Custom Configuration

You can provide a custom `config.yaml` file to override default paths.

#### Config File Structure

```yaml
DIMR:
    path: bin/dimr_runners/sobek_dimr/x64/dimr/scripts

RGWM:
    path: bin/rgwm_versie2.4.3/bin/rgwm.exe
```

#### Configuration Requirements

- **Both sections required:** DIMR and RGWM paths must be specified
- **DIMR path:** Must point to an existing directory
- **RGWM path:** Must point to an executable file (rgwm.exe)
- **Path types:** Can be absolute or relative to the config file location

#### Example Configuration Files

**Absolute paths:**

```yaml
DIMR:
    path: C:/tools/sobek/dimr/scripts

RGWM:
    path: C:/tools/rgwm/bin/rgwm.exe
```

**Relative paths (relative to config.yaml location):**

```yaml
DIMR:
    path: ../bin/dimr_runners/sobek_dimr/x64/dimr/scripts

RGWM:
    path: ../bin/rgwm_versie2.4.3/bin/rgwm.exe
```

---

## Workflow Example

Here's a complete workflow from scenario generation to result extraction:

### Step 1: Prepare Input Files

Create your scenario input file:

```csv
Scenario,Keringstoestand[open/gesloten],Rijnafvoer te Lobith[m3/s],Maasafvoer te Lith[m3/s],Stormopzet[m + NAP],Zeewaterstand[m + NAP],Windsnelheid[m/s],Windrichting[-]
1,Open,9000,1861,3,5,19.38,WNW
2,Gesloten,11500,2448,4.5,6,27.41,WNW
3,Open,12000,2600,5,6.5,30.5,W
```

### Step 2: Generate Boundary Conditions

```bash
cip-tool generate -i scenarios.csv -o output --calculate-surge
```

### Step 3: Run Sobek Simulations

```bash
cip-tool run-sobek -o output
```

### Step 4: Extract Results

```bash
cip-tool extract -i extraction_config.csv -o output
```

---

## Troubleshooting

### Common Issues

#### Input File Not Found

**Error:**
```
ArgumentTypeError: 'input.csv' is not an existing file.
```

**Solution:**
- Verify the file path is correct
- Use absolute paths or ensure relative paths are correct
- Check file permissions

#### Output Directory Creation Failed

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
- Check write permissions on the target directory
- Ensure the path is valid
- Try running with elevated privileges if necessary

#### Batch File Not Found (run-sobek)

**Error:**
```
FileNotFoundError: Batch file not found: ...
```

**Solution:**
- Ensure you've run the `generate` command first
- Verify the output directory contains the `rmm_results` folder
- Use absolute paths or check your current working directory

#### Wrong Operating System (run-sobek)

**Error:**
```
RuntimeError: Running a .bat file requires Windows.
```

**Solution:**
- The `run-sobek` command only works on Windows
- Use a Windows machine or WSL with Windows interop enabled

#### Missing Configuration Paths

**Error:**
```
FileNotFoundError: DIMR path does not exist
```

**Solution:**
- Verify paths in config.yaml are correct
- Ensure DIMR and RGWM are properly installed
- Check that paths are relative to the config file location

#### Surge Calculation Not Converging

**Issue:** Iterative surge calculation takes too many iterations or doesn't converge

**Solution:**
- Check that input water levels are realistic
- Verify model setup is correct
- Review initial storm surge estimates
- Check for model stability issues

---

## Best Practices

### File Organization

```
project/
├── config.yaml
├── inputs/
│   ├── scenarios.csv
│   └── extraction_config.csv
├── output/
│   ├── rgwm_results/
│   └── rmm_results/
└── bin/
    ├── dimr_runners/
    └── rgwm_versie2.4.3/
```

### Tips

1. **Use version control** for input files and configuration
2. **Create template files** for consistent scenario definitions
3. **Document your scenarios** with meaningful names/numbers
4. **Back up results** before re-running simulations
5. **Use meaningful output directory names** (e.g., `output_2025_flood_study`)
6. **Check logs** after Sobek runs for warnings or errors
7. **Validate extracted data** before using in downstream analyses

### Performance Considerations

- Large scenario sets may take considerable time to run
- Surge calculation adds multiple iterations (typically 3-5x runtime)
- Consider parallel execution for independent scenarios
- Monitor disk space for large result files

---

## Additional Resources

- [Quick Reference Guide](../api/cli-quick-reference.md)
- [Installation Guide](installation-zip-file.md)
- [API Documentation](../api/cli.md)
- [Change Log](../change-log.md)

---

## Support

For issues, questions, or contributions:

- Check the [documentation](../index.md)
- Review the [installation guide](installation-zip-file.md)
- Contact support: software.support@deltares.nl

