#!/usr/bin/env bash
# Offline test of Airwindows ports on this computer (ASan/UBSan).
#   tests/run_aw.sh [Name ...]        default: every ports/*/
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MV="${MPC_VST:-$HERE/mpc-vst}"
SAN="-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1"
names=("$@")
[ ${#names[@]} -gt 0 ] || names=($(ls "$HERE/ports"))
failed=()
for n in "${names[@]}"; do
  P="$HERE/ports/$n"; B="$P/build"; A="$HERE/src/airwindows/$n"
  mkdir -p "$B"
  python3 "$MV/tools/gen_vst.py" "$P/vst.json" --params-h >/dev/null &&
  CX="-std=gnu++11 -I$HERE/src/shim -I$A -DAW_CLASS=$n -include $A/$n.h -fwrapv -w" &&
  g++ $SAN $CX -c "$HERE/src/aw_engine.cpp" -o "$B/t_engine.o" &&
  g++ $SAN $CX -c "$A/$n.cpp" -o "$B/t_plugin.o" &&
  g++ $SAN $CX -c "$A/${n}Proc.cpp" -o "$B/t_proc.o" &&
  gcc $SAN -std=gnu11 -w -I"$B" -c "$MV/wrapper/vst2_wrap.c" -o "$B/t_wrap.o" &&
  gcc $SAN -std=gnu11 -I"$B" -c "$HERE/tests/aw_test.c" -o "$B/t_test.o" &&
  g++ $SAN "$B"/t_*.o -lm -o "$B/aw_test" &&
  "$B/aw_test" > "$B/test.log" 2>&1
  if [ $? -eq 0 ]; then echo "PASSED $n"; else echo "FAILED $n"; cat "$B/test.log" 2>/dev/null | grep -v '^ok' ; failed+=("$n"); fi
done
[ ${#failed[@]} -eq 0 ] || { echo "failed: ${failed[*]}"; exit 1; }
