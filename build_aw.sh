#!/usr/bin/env bash
# Build Airwindows ports into installable MPC OS plugin zips.
#   ./build_aw.sh [Name ...]      default: every ports/*/
# Per port: skin (on this computer), armhf .so (Debian bullseye cross compiler in Docker, libstdc++ static, glibc <= 2.31),
# then dist/<Name>-1.0.0-mpc-armv7.zip via mpc-vst/tools/release.py.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MV="$(cd "${MPC_VST:-$HERE/mpc-vst}" && pwd)"
IMAGE=mpc-armhf-cross
VERSION=1.0.0
names=("$@")
[ ${#names[@]} -gt 0 ] || names=($(ls "$HERE/ports"))

docker image inspect $IMAGE >/dev/null 2>&1 || docker build -q -t $IMAGE -f "$HERE/docker/armhf.Dockerfile" "$HERE/docker"

ART="$HERE/build/shadow_art"
mkdir -p "$HERE/build"
[ -x "$ART" ] || cc -O2 -I"$MV/tools/vendor/force-shadow/tools" -o "$ART" "$MV/tools/shadow_art.c" -lm
for n in "${names[@]}"; do
  mkdir -p "$HERE/ports/$n/build" && python3 "$HERE/tools/aw_backdrop.py" "$n" -o "$HERE/ports/$n/build/backdrop.png"
done
for n in "${names[@]}"; do
  SHADOW_ART="$ART" python3 "$MV/tools/gen_vst.py" "$HERE/ports/$n/vst.json" >/dev/null
done

docker run --rm -v "$HERE":/b -v "$MV":/mv:ro -w /b $IMAGE bash -euc '
  F="-O2 -fPIC -fvisibility=hidden -fwrapv -w"
  for n in '"${names[*]}"'; do
    P=ports/$n; O=$P/build/arm; A=src/airwindows/$n; so=$(echo $n | tr A-Z a-z).so
    mkdir -p $O
    X="$F -std=gnu++11 -Isrc/shim -I$A -DAW_CLASS=$n -include $A/$n.h"
    arm-linux-gnueabihf-g++ $X -c src/aw_engine.cpp -o $O/engine.o
    arm-linux-gnueabihf-g++ $X -c $A/$n.cpp -o $O/plugin.o
    arm-linux-gnueabihf-g++ $X -c $A/${n}Proc.cpp -o $O/proc.o
    arm-linux-gnueabihf-gcc $F -std=gnu11 -I$P/build -c /mv/wrapper/vst2_wrap.c -o $O/vst2_wrap.o
    arm-linux-gnueabihf-g++ -shared -fPIC -fvisibility=hidden -static-libstdc++ -static-libgcc -Wl,--exclude-libs,ALL \
        -Wl,--no-undefined $O/engine.o $O/plugin.o $O/proc.o $O/vst2_wrap.o -lm -o $P/build/$so
    arm-linux-gnueabihf-strip $P/build/$so
    ex=$(arm-linux-gnueabihf-readelf --dyn-syms -W $P/build/$so | grep " GLOBAL " | grep -v UND | awk "{print \$8}" | tr "\n" " ")
    gl=$(arm-linux-gnueabihf-readelf -V $P/build/$so | grep -o "GLIBC_[0-9.]*" | sort -uV | tail -1)
    [ "$ex" = "VSTPluginMain " ] || { echo "$n: unexpected exports: $ex"; exit 1; }
    echo "built $n ($so, $gl)"
  done
'

mkdir -p "$HERE/dist"
for n in "${names[@]}"; do
  P="$HERE/ports/$n/build"; so="$(echo "$n" | tr 'A-Z' 'a-z').so"
  python3 "$MV/tools/release.py" --so "$P/$so" --skin "$P/skin/Airwindows - VST - $n" --entry "$P/pluginlist-entry.xml" \
      --version $VERSION --id "airwindows-$(echo "$n" | tr 'A-Z' 'a-z')" --license MIT --repo mmiroshnikov/mpc-airwindows \
      --about "Airwindows $n (MIT), as an MPC insert effect." -o "$HERE/dist" >/dev/null
  echo "packed dist/$n-$VERSION-mpc-armv7.zip"
done
