#!/usr/bin/env bash
set -euo pipefail

VALIDATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$VALIDATION_DIR/.tools"
SOURCE_DIR="$TOOLS_DIR/libbgcode"
# Pin the official source so every setup uses the same converter.
REVISION="d4da9073616d70a43c151e8c1d7fbff879d2e08a"
# Keep this array non-empty for macOS's bundled Bash 3.2 with `set -u`.
CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF)
BUILD_NAME="native"

if [[ "${1:-}" == "--windows" ]]; then
    BUILD_NAME="windows"
    CMAKE_ARGS+=("-DCMAKE_TOOLCHAIN_FILE=$VALIDATION_DIR/cmake/mingw-w64.cmake")
    shift
fi
if [[ $# -ne 0 ]]; then
    echo "Usage: bash backend/app/validation/setup_bgcode.sh [--windows]"
    exit 1
fi

for tool in git cmake; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is required. See backend/app/validation/README.md for build prerequisites."
        exit 1
    fi
done

mkdir -p "$TOOLS_DIR"
if [[ ! -d "$SOURCE_DIR/.git" ]]; then
    git clone https://github.com/prusa3d/libbgcode.git "$SOURCE_DIR"
fi
if [[ -n "$(git -C "$SOURCE_DIR" status --porcelain)" ]]; then
    echo "ERROR: $SOURCE_DIR contains local changes; refusing to overwrite them."
    exit 1
fi
if ! git -C "$SOURCE_DIR" cat-file -e "$REVISION^{commit}" 2>/dev/null; then
    git -C "$SOURCE_DIR" fetch --depth 1 origin "$REVISION"
fi
git -C "$SOURCE_DIR" checkout --detach "$REVISION"

BUILD_DIR="${BGCODE_BUILD_DIR:-$TOOLS_DIR/build-$BUILD_NAME}"
DEPS_DIR="$BUILD_DIR/deps"
DEPS_PREFIX="$DEPS_DIR/install"

# Only build dependencies needed by the CLI, using upstream's checksum-pinned downloads.
cmake -S "$SOURCE_DIR/deps" -B "$DEPS_DIR" "${CMAKE_ARGS[@]}" \
    -DLibBGCode_Deps_SELECT_ALL=OFF \
    -DLibBGCode_Deps_BUILD_Boost=ON \
    -DLibBGCode_Deps_BUILD_heatshrink=ON \
    -DLibBGCode_Deps_BUILD_ZLIB=ON \
    "-DLibBGCode_Deps_DEP_INSTALL_PREFIX=$DEPS_PREFIX" \
    "-DLibBGCode_Deps_DEP_DOWNLOAD_DIR=$TOOLS_DIR/downloads" \
    -DDEP_MAX_THREADS=2
cmake --build "$DEPS_DIR" --config Release --parallel 2

cmake -S "$SOURCE_DIR" -B "$BUILD_DIR/libbgcode" "${CMAKE_ARGS[@]}" \
    -DLibBGCode_BUILD_TESTS=OFF \
    "-DCMAKE_PREFIX_PATH=$DEPS_PREFIX" \
    "-DCMAKE_INSTALL_PREFIX=$TOOLS_DIR"
cmake --build "$BUILD_DIR/libbgcode" --config Release --parallel 2
cmake --install "$BUILD_DIR/libbgcode" --config Release

echo "Installed the official Prusa converter in $TOOLS_DIR/bin."
if [[ "$BUILD_NAME" == "windows" ]]; then
    echo "This is a Windows executable: run tests in Git Bash with Windows Python."
    echo "For tests in WSL, also run this setup without --windows to build the Linux converter."
else
    echo "Run bash backend/app/validation/test_validation.sh on the platform used for this build."
fi
