# G-code Validation

This module validates uploaded 3D printer G-code files before printer selection.

It is designed for the **3D-printer-farm-interface** project and checks whether an uploaded file is valid and compatible with one of the supported Prusa printer profiles.

## Supported Files

- `.gcode`
- `.bgcode`

The validator checks the file content as well as the extension, so renaming an unrelated file to `.gcode` or `.bgcode` will not make it valid.

## Supported Printer Profiles

Current configured profiles:

- **Prusa CORE One HF0.4 nozzle**
- **Original Prusa XL - 5T Input Shaper 0.4 nozzle**

The same uploaded file is checked against both profiles.

A file passes validation only when exactly one supported printer profile matches.

## Validation Flow

```text
UPLOAD G-CODE
    |
    v
1. FILE FORMAT VALIDATION
    |
    v
2. PARSE + INTEGRITY
    |
    v
3. READ METADATA
    |
    v
4. M862 EXECUTABLE CROSS-CHECK
    |
    v
5. CHECK BOTH PRINTER PROFILES
   + build volume
   + nozzle configuration
   + temperature limits
    |
    v
6. EXACTLY ONE SUPPORTED PROFILE?
    |
    +-- YES --> PASS --> SELECT_PRINTER
    |
    +-- NO  --> FAIL --> UPLOAD_GCODE / RE-SLICE

```

## Run Validation Tests

Use Python 3.10+ and the official Prusa `bgcode` converter. The full suite requires
the converter and fails with setup instructions if it is missing; the real binary
test is never silently skipped.

Run from the repository root:

```bash
bash validation/test_validation.sh
```

The runner checks both real CORE One formats and all four deliberately broken
samples. It probes Python candidates before choosing one, avoiding inactive
Microsoft Store aliases on Windows. To select Thonny explicitly in Git Bash:

```bash
PYTHON_BIN="$LOCALAPPDATA/Programs/Thonny/python.exe" bash validation/test_validation.sh
```

### Install the binary converter

The validator looks for `BGCODE_BIN` (when explicitly set), then `bgcode` on
`PATH`, then `validation/.tools/bin/bgcode` (`bgcode.exe` on Windows).
An invalid explicit `BGCODE_BIN` is an error, rather than a fallback to another
converter. Paths containing spaces are supported.

To build the official converter locally on Linux, install Git, CMake 3.x (3.22 or newer),
Make, and a C++17 compiler, then run:

```bash
bash validation/setup_bgcode.sh
```

For Windows, the following WSL Ubuntu commands build a native, self-contained
Windows executable. Run them in the repository directory in WSL:

```bash
sudo apt-get update
sudo apt-get install -y git cmake make g++-mingw-w64-x86-64-posix
BGCODE_BUILD_DIR="$HOME/.cache/uwa-bgcode-windows" bash validation/setup_bgcode.sh --windows
```

Then run `bash validation/test_validation.sh` in **Git Bash with Windows Python**.
The Windows build does not require WSL at validation time. Alternatively, build
natively using Git Bash, CMake 3.x and Visual Studio C++ build tools with
`bash validation/setup_bgcode.sh`.

`BGCODE_BUILD_DIR` selects the build cache; using WSL's Linux filesystem avoids
slow dependency extraction on Windows-mounted drives. Omit it to build under
`validation/.tools/`.

The setup script downloads the official source at commit
`d4da9073616d70a43c151e8c1d7fbff879d2e08a` and its checksum-pinned dependencies,
then installs under `validation/.tools/`. Source, build files and binaries are
ignored by Git. Setup needs internet access and may take several minutes; normal
validation runs offline. See Prusa's [build instructions](https://github.com/prusa3d/libbgcode/blob/d4da9073616d70a43c151e8c1d7fbff879d2e08a/doc/building.md)
and [converter usage](https://github.com/prusa3d/libbgcode/blob/d4da9073616d70a43c151e8c1d7fbff879d2e08a/doc/bgcode.md).

If you already have an official converter elsewhere, no local build is needed:

```bash
BGCODE_BIN="/path/to/bgcode" bash validation/test_validation.sh
```
