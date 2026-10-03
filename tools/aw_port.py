#!/usr/bin/env python3
"""Generate an mpc-vst-plugins port (ports/<Name>/vst.json + params.json) for each vendored Airwindows plugin.

    tools/aw_port.py Galactic2 MatrixVerb ...      (sources must already be in src/airwindows/<Name>/)

Parameter names and defaults are read from the plugin's own <Name>.cpp (getParameterName and the constructor),
so the MPC side matches what the DSP starts with. Values are 0..100 % on the MPC, 0..1 inside Airwindows.
"""
import json
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAKEN_UIDS = {"AwGl"}   # Galactic (vst/vst.json)
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def parse(name):
    src = open(os.path.join(HERE, "src/airwindows", name, name + ".cpp"), encoding="utf-8", errors="replace").read()
    hdr = open(os.path.join(HERE, "src/airwindows", name, name + ".h"), encoding="utf-8", errors="replace").read()
    letters = re.findall(r"\bkParam([A-Z])\s*=\s*\d+", hdr)
    if not letters:
        sys.exit("%s: no kParam enum" % name)
    body = src[src.index("::getParameterName("):]
    body = body[:body.index("\n}")]
    names = dict(re.findall(r'case\s+kParam([A-Z])\s*:\s*vst_strncpy\s*\(\s*text\s*,\s*"([^"]*)"', body))
    ctor = src[src.index(name + "::" + name + "("):]
    ctor = ctor[:ctor.index("\n}")]
    defaults = {}
    for letter, value in re.findall(r"^\s*([A-Z])\s*=\s*([0-9.]+)\s*;", ctor, re.M):
        defaults.setdefault(letter, float(value))
    params = []
    for i, letter in enumerate(letters):
        if letter not in names or letter not in defaults:
            sys.exit("%s: parameter %s has no name or default" % (name, letter))
        params.append({"key": "p%d" % i, "name": names[letter], "min": 0, "max": 100, "unit": "%",
                       "default": round(defaults[letter] * 100, 4)})
    return params


def uid(name):
    h = zlib.crc32(name.encode())
    while True:
        u = "Aw" + B62[h % 62] + B62[(h // 62) % 62]
        if u not in TAKEN_UIDS:
            TAKEN_UIDS.add(u)
            return u
        h += 1


def main():
    names = sys.argv[1:]
    if not names:
        sys.exit(__doc__)
    for name in names:
        params = parse(name)
        d = os.path.join(HERE, "ports", name)
        os.makedirs(d, exist_ok=True)
        json.dump({"name": name, "params": params}, open(os.path.join(d, "params.json"), "w"), indent=1)
        cfg = {
            "name": name, "vendor": "Airwindows", "uid": uid(name), "version": 1000,
            "so": name.lower() + ".so", "params": "params.json", "effect": True,
            # cosmic backdrop (tools/aw_backdrop.py, written by build_aw.sh) and 30% larger text
            "skin_theme": ["label_scale=1.5", "backdrop=build/backdrop.png"],
            "build": {
                "root": "../..",
                "sources": ["src/aw_engine.cpp", "src/airwindows/%s/%s.cpp" % (name, name),
                            "src/airwindows/%s/%sProc.cpp" % (name, name)],
                # -fwrapv: older plugins' denormal-noise generators rely on int multiplication wrapping
                "cflags": ["-Isrc/shim", "-Isrc/airwindows/" + name, "-DAW_CLASS=" + name, "-fwrapv",
                           "-include", "src/airwindows/%s/%s.h" % (name, name)],
                "libs": ["-lm"],
            },
        }
        json.dump(cfg, open(os.path.join(d, "vst.json"), "w"), indent=1)
        print("%-16s %s  %s" % (name, cfg["uid"], ", ".join("%s=%g" % (p["name"], p["default"]) for p in params)))


if __name__ == "__main__":
    main()
