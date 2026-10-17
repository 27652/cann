#!/bin/bash
# Build only. Never run CAModel here; Coordinator owns device scheduling.
set -eo pipefail
cd "$(dirname "$0")"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release > configure.log 2>&1
cmake --build build -j2 > build.log 2>&1
