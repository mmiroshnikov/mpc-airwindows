#!/usr/bin/env bash
# Build the MPC OS plugin: skin (on this computer) + armhf .so (Debian bullseye cross compiler in Docker).
#   ./build.sh
# Output: vst/build/skin/Airwindows - VST - Galactic/ (galactic.so inside) and dist/Galactic-1.0.0-mpc-armv7.zip.
# libstdc++ is linked statically, so the .so needs only glibc (<= 2.31 here; the device has 2.39).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MV="$(cd "${MPC_VST:-$HERE/mpc-vst}" && pwd)"
B="$HERE/vst/build"
SKIN="$B/skin/Airwindows - VST - Galactic"
IMAGE="${BUILD_IMAGE:-node:19-bullseye}"

mkdir -p "$B"
cc -O2 -I"$MV/tools/vendor/force-shadow/tools" -o "$B/shadow_art" "$MV/tools/shadow_art.c" -lm
python3 "$HERE/tools/aw_backdrop.py" Galactic -o "$B/backdrop.png"
python3 "$MV/tools/gen_vst.py" "$HERE/vst/vst.json"

docker run --rm -v "$HERE":/b -v "$MV":/mv:ro -w /b "$IMAGE" bash -euc '
  if ! command -v arm-linux-gnueabihf-g++ >/dev/null; then
    apt-get update -qq && apt-get install -y -qq --no-install-recommends g++-arm-linux-gnueabihf >/dev/null
  fi
  CXX=arm-linux-gnueabihf-g++; CC=arm-linux-gnueabihf-gcc
  F="-O2 -fPIC -fvisibility=hidden -Wall -Wno-unused-parameter -Wno-unused-value -Wno-unused-variable"
  O=vst/build/arm; mkdir -p $O
  $CXX $F -std=gnu++11 -Isrc/shim -Isrc/airwindows/Galactic -c src/engine.cpp -o $O/engine.o
  $CXX $F -std=gnu++11 -Isrc/shim -Isrc/airwindows/Galactic -c src/airwindows/Galactic/Galactic.cpp -o $O/galactic.o
  $CXX $F -std=gnu++11 -Isrc/shim -Isrc/airwindows/Galactic -c src/airwindows/Galactic/GalacticProc.cpp -o $O/galactic_proc.o
  $CC $F -std=gnu11 -Ivst/build -c /mv/wrapper/vst2_wrap.c -o $O/vst2_wrap.o
  $CXX -shared -fPIC -fvisibility=hidden -static-libstdc++ -static-libgcc -Wl,--exclude-libs,ALL -Wl,--no-undefined \
      $O/engine.o $O/galactic.o $O/galactic_proc.o $O/vst2_wrap.o -lm -o vst/build/galactic.so
  arm-linux-gnueabihf-strip vst/build/galactic.so
  echo "exported: $(arm-linux-gnueabihf-readelf --dyn-syms -W vst/build/galactic.so | grep " GLOBAL " | grep -v UND | awk "{print \$8}" | tr "\n" " ")"
  echo "needs: $(arm-linux-gnueabihf-readelf -d vst/build/galactic.so | grep NEEDED | grep -o "\[.*\]" | tr "\n" " ")"
  echo "highest glibc: $(arm-linux-gnueabihf-readelf -V vst/build/galactic.so | grep -o "GLIBC_[0-9.]*" | sort -uV | tail -1) (device has 2.39)"
'
cp "$B/galactic.so" "$SKIN/galactic.so"
md5 -q "$SKIN/galactic.so" 2>/dev/null || md5sum "$SKIN/galactic.so"
mkdir -p "$HERE/dist"
python3 "$MV/tools/release.py" --so "$B/galactic.so" --skin "$SKIN" --entry "$B/pluginlist-entry.xml" \
    --version 1.0.0 --id airwindows-galactic --license MIT --repo mmiroshnikov/mpc-airwindows \
    --about "Airwindows Galactic (MIT), as an MPC insert effect." -o "$HERE/dist" >/dev/null
echo "packed dist/Galactic-1.0.0-mpc-armv7.zip"
