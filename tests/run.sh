#!/usr/bin/env bash
# Offline test of the effect on this computer (ASan/UBSan), before anything goes to a device.
#   tests/run.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MV="${MPC_VST:-$HERE/mpc-vst}"
python3 "$MV/tools/gen_vst.py" "$HERE/vst/vst.json" --params-h
B="$HERE/vst/build"
SAN="-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1"
CX="-std=gnu++11 -I$HERE/src/shim -I$HERE/src/airwindows/Galactic -Wno-unused-value"
g++ $SAN $CX -c "$HERE/src/engine.cpp" -o "$B/t_engine.o"
g++ $SAN $CX -c "$HERE/src/airwindows/Galactic/Galactic.cpp" -o "$B/t_galactic.o"
g++ $SAN $CX -c "$HERE/src/airwindows/Galactic/GalacticProc.cpp" -o "$B/t_galactic_proc.o"
gcc $SAN -std=gnu11 -I"$B" -c "$MV/wrapper/vst2_wrap.c" -o "$B/t_wrap.o"
gcc $SAN -std=gnu11 -I"$B" -c "$HERE/tests/fx_test.c" -o "$B/t_fx_test.o"
g++ $SAN "$B"/t_*.o -lm -o "$B/fx_test"
"$B/fx_test"
