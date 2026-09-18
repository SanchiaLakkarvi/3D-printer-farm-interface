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

#### macOS (Intel or Apple Silicon)

Build the converter on the Mac that will run validation; no Windows or WSL
installation is needed. Use a native Terminal session for your Mac's architecture.

Install [Apple's Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/)
if they are not already installed, and wait for the installer to finish:

```bash
xcode-select --install
```

You also need Python 3.10+. If you use Homebrew, `brew install python` provides
[Python](https://formulae.brew.sh/formula/python@3.14). Then, from the repository
root, install CMake in an isolated build environment and run the native setup:

```bash
python3 -m venv validation/.tools/build-env
validation/.tools/build-env/bin/python -m pip install "cmake==3.31.10"
PATH="$PWD/validation/.tools/build-env/bin:$PATH" bash validation/setup_bgcode.sh
PYTHON_BIN="$PWD/validation/.tools/build-env/bin/python" bash validation/test_validation.sh
```

[CMake 3.31.10](https://pypi.org/project/cmake/3.31.10/) supplies Intel and Apple
Silicon wheels. Pinning CMake 3.x avoids compatibility errors in the older
upstream dependency build files with CMake 4. The build environment and converter
remain local and ignored by Git. Subsequent test runs only need the last command.
Do not use `--windows` or copy a Linux/Windows converter onto the Mac.

The macOS setup is documented and the script accommodates bundled Bash 3.2,
but the complete build and test suite have not yet been run on a Mac.

#### Linux and WSL

**WSL is a Linux validation environment.** A converter built with `--windows`
provides `bgcode.exe` for Windows Python only. WSL's Linux Python needs the native
`bgcode` executable. Both can coexist in `validation/.tools/bin/`; the validator
selects the one for the running Python platform. The runner likewise selects
that platform's virtual environment.

To build and test in **WSL Ubuntu**, run these commands in the repository directory:

```bash
sudo apt-get update
sudo apt-get install -y git cmake build-essential
BGCODE_BUILD_DIR="$HOME/.cache/uwa-bgcode-linux" bash validation/setup_bgcode.sh
bash validation/test_validation.sh
```

On other Linux systems, install Git, CMake 3.x (3.22 or newer), Make, and a C++17
compiler, then run `bash validation/setup_bgcode.sh` followed by the test runner.

For **Git Bash with Windows Python**, the following WSL Ubuntu commands build a
native, self-contained Windows executable. These commands do **not** install the
Linux converter needed for tests inside WSL:

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

### If the runner reports two failed groups in WSL

Check the errors for the real binary unit test and `VALID BINARY CORE ONE` sample.
If both report a missing Prusa converter, they are the same missing dependency
reported twice. Run the WSL setup above **without `--windows`**, then rerun the
suite. If `BGCODE_BIN` is set, it must point to a Linux executable when using
Linux Python; use `unset BGCODE_BIN` to restore automatic discovery.

Generated converters are not committed to Git, so a new checkout needs setup
even if another machine has passed the complete test suite.
