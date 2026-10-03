#!/usr/bin/env python3
"""Render README screenshots of every plugin's skin (what MPC draws, controls at their defaults).

    python3 tools/screenshots.py [Name ...]      default: every ports/*/ plus Galactic

Builds each skin the way build_aw.sh does (backdrop + gen_vst.py; no Docker, no .so), then composites
docs/screenshots/<Name>.png and docs/screenshots/all.png (a contact sheet). Needs Pillow and numpy.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MV = os.environ.get("MPC_VST") or os.path.join(HERE, "mpc-vst")
FONT = os.path.join(MV, "tools", "html_art", "fonts", "TitilliumWeb-SemiBold.ttf")
OUT = os.path.join(HERE, "docs", "screenshots")


def port_dir(name):
    return os.path.join(HERE, "vst") if name == "Galactic" else os.path.join(HERE, "ports", name)


def build_skin(name, art):
    d = port_dir(name)
    os.makedirs(os.path.join(d, "build"), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(HERE, "tools", "aw_backdrop.py"), name,
                    "-o", os.path.join(d, "build", "backdrop.png")], check=True)
    subprocess.run([sys.executable, os.path.join(MV, "tools", "gen_vst.py"), os.path.join(d, "vst.json")],
                   check=True, stdout=subprocess.DEVNULL, env=dict(os.environ, SHADOW_ART=art))
    return os.path.join(d, "build", "skin", "Airwindows - VST - " + name, "Plugin Skins")


def rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (2, 4, 6))


def render(skin, params):
    """The first page of a built skin: background images, knob filmstrips at each parameter's default,
    Name and Value labels in the device font."""
    t = json.load(open(os.path.join(skin, "TUI.json")))["pageData"]
    defs = {d["key"]: d["value"] for d in t["componentDefinitions"]["localComponentDefinitions"]}
    xywh = lambda b: [int(float(v)) for v in b["bounds"].split()]
    tab = t["tabs"][0]
    im = Image.new("RGBA", tuple(int(v) for v in tab["initialSize"].split()[2:]), (0, 0, 0, 255))
    dr = ImageDraw.Draw(im)
    for c in defs[tab["componentName"]]["componentsData"]:
        cd = c["componentData"]
        x, y, _, _ = xywh(c["bounds"])
        if cd["type"] == "Image":
            img = Image.open(os.path.join(skin, cd["data"]["image"])).convert("RGBA")
            im.alpha_composite(img, (x, y))
            continue
        m = c["handle remapping"]["map"][0]["value"]
        p = params[int(m.split()[-1])]
        norm = (p["default"] - p["min"]) / ((p["max"] - p["min"]) or 1)
        for s in defs[cd["type"]]["componentsData"]:
            sd = s["componentData"]
            sx, sy, sw, sh = xywh(s["bounds"])
            if sd["type"] == "Knob":
                st = Image.open(os.path.join(skin, sd["data"]["filmStrip"])).convert("RGBA")
                fw = st.width
                f = round(norm * sd["data"]["numFrames"])
                im.alpha_composite(st.crop((0, f * fw, fw, (f + 1) * fw)), (x + sx, y + sy))
            elif sd["type"] == "Label":
                ts = sd["data"]["textStyle"]
                text = cd.get("name", "") if sd["data"].get("type") == "Name" else "%d%%" % round(p["default"])
                if ts.get("case") == "Upper Case":
                    text = text.upper()
                font = ImageFont.truetype(FONT, round(ts["font"]["height"]))
                dr.text((x + sx + sw / 2, y + sy + sh / 2), text, font=font, fill=rgb(ts["colour"]), anchor="mm")
    return im.convert("RGB")


def main():
    names = sys.argv[1:] or sorted(os.listdir(os.path.join(HERE, "ports"))) + ["Galactic"]
    art = os.path.join(HERE, "build", "shadow_art")
    if not os.path.exists(art):
        os.makedirs(os.path.dirname(art), exist_ok=True)
        subprocess.run(["cc", "-O2", "-I" + os.path.join(MV, "tools", "vendor", "force-shadow", "tools"), "-o", art,
                        os.path.join(MV, "tools", "shadow_art.c"), "-lm"], check=True)
    os.makedirs(OUT, exist_ok=True)
    shots = []
    for n in names:
        skin = build_skin(n, art)
        params = json.load(open(os.path.join(port_dir(n), "params.json")))
        params = params["params"] if isinstance(params, dict) else params
        im = render(skin, params)
        im.save(os.path.join(OUT, n + ".png"), optimize=True)
        shots.append(im)
        print(n)
    if len(names) > 1:
        cols, tw = 3, 426
        th = round(tw * shots[0].height / shots[0].width)
        gap = 6
        rows = (len(shots) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (0, 0, 0))
        for i, im in enumerate(shots):
            sheet.paste(im.resize((tw, th), Image.LANCZOS), (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
        sheet.save(os.path.join(OUT, "all.png"), optimize=True)


if __name__ == "__main__":
    main()
