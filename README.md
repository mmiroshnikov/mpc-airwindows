# Airwindows for MPC OS

[Airwindows](https://www.airwindows.com/) effects as native insert-effect plugins for Akai MPC OS / Force
(MPC Live, MPC One, MPC X, Force; armv7), each with its own touch skin: a cosmic backdrop, the controls on a dark
see-through panel, and the current Q-Link bank outlined.

Air3, ButterComp2, Chamber2, ChorusEnsemble, Console7Channel, Density2, Galactic, Galactic2, Galactic3, GalacticVibe,
Infinity2, MatrixVerb, PitchDelay, TapeDelay2, ToVinyl4, Verbity2, ZAcidLowpass, ZLowpass2, kAlienSpaceship,
kCathedral5, kCosmos.

## Install on a device

Each `dist/<Name>-1.0.0-mpc-armv7.zip` holds the plugin folder and an `install.sh`. Copy the unpacked folder to the
device (SSH as root) and run it:

```sh
sh install.sh -y        # installs into /sdcard/Synths, registers the plugin and restarts MPC
sh install.sh -y -n     # batch: install without restarting (stop/start acvs yourself once)
```

## Build

Needs Docker, a C compiler and Python 3 with Pillow and numpy.

```sh
./build_aw.sh                 # every port in ports/ -> dist/*.zip
./build_aw.sh kCosmos Air3    # just these
./build.sh                    # Galactic (vst/) -> vst/build/skin/
tests/run_aw.sh [Name ...]    # offline render test under ASan (run on Linux, e.g. in node:19-bullseye)
```

`build_aw.sh` draws each skin on this computer (backdrop from `tools/aw_backdrop.py`, layout and filmstrips from
`mpc-vst/tools`), cross-compiles the `.so` in the `mpc-armhf-cross` Docker image (glibc <= 2.31, libstdc++ static)
and packs the release zip.

## Add an Airwindows plugin

1. Copy its LinuxVST sources into `src/airwindows/<Name>/` (`<Name>.cpp`, `<Name>.h`, `<Name>Proc.cpp`).
2. `python3 tools/aw_port.py <Name>` writes `ports/<Name>/vst.json` and `params.json`.
3. `./build_aw.sh <Name>`.

## Layout

- `src/` — the Airwindows sources (`src/airwindows/`, MIT) and the engine glue (`aw_engine.cpp`, `shim/`).
- `ports/<Name>/` — per-plugin `vst.json` (uid, .so name, skin theme) and `params.json`.
- `tools/` — `aw_port.py` (port generator), `aw_backdrop.py` (skin backdrops).
- `mpc-vst/` — the parts of the mpc-vst-plugins toolchain this repo builds with: the VST2 wrapper, skin generator
  (`gen_vst.py`, `shadow_skin.py`, `shadow_art.c`) and release packager.

## License

MIT (`LICENSE`). Airwindows code: MIT, Chris Johnson (`src/airwindows/LICENSE`). force-shadow renderer: MIT
(`mpc-vst/tools/vendor/force-shadow/LICENSE`). Titillium Web font: SIL OFL 1.1 (`mpc-vst/tools/html_art/fonts/OFL.txt`).
