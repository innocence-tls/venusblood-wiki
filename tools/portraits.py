"""Собрать портреты из тех же слоёв и координат, что использует Frontier."""
from pathlib import Path
from io import BytesIO
import argparse
import re
import sys
from PIL import Image

root = Path(__file__).resolve().parent.parent
kit = root.parent / "vn_kit"
sys.path.insert(0, str(kit))
from engines.kirikiri.xp3 import read_index, read_file

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
archive = parser.parse_args().archive
project = kit / "projects/vbfrontier"
layout = (project / "work/raw/u8/userfunctions.tjs").read_text(encoding="utf-8-sig")
sprites = dict(tyrca="01_a110", freya="02_a110", thor="03_a110", rigret="04_a110",
               odin="05_a110", loki="06_a110", hvedrung="06_b110", fena="07_110",
               garm="08_110", ymir="09_110", hel="10_110", fenrir="11_110",
               jorm="12_110", surt="13_110", menia="14_110")
dest = root / "static/art/portraits"
dest.mkdir(exist_ok=True)
assets = {Path(i["name"]).stem: i for i in read_index(archive)}
with archive.open("rb") as stream:
    def load(stem):
        return Image.open(BytesIO(read_file(stream, assets[stem]))).convert("RGBA")
    for key, number in sprites.items():
        stem = "cb" + number
        rule = re.search(r"case '" + stem + r"':([^\n]+)", layout)[1]
        dx, dy, sw, sh = [int(re.search(r"mp\." + param + r"=(\d+)",rule)[1]) for param in ("dx","dy","sw","sh")]
        face = load(re.search(r"mp.face='([^']+)'", rule)[1])
        body = load(stem)
        body.alpha_composite(face.crop((sw, 0, sw * 2, sh)), (dx, dy))
        # Кадрировать относительно лица: размеры полей у спрайтов различаются.
        cx, cy = dx + sw/2, dy + sh/2
        for suffix, width, height, head in [("",620,670,4.2),("-card",460,270,3.05)]:
            scale = max(sw/width*head, sh/height*1.8)
            w, ht = width*scale, height*scale
            cropped = body.crop((round(cx-w/2), round(cy-ht*.38), round(cx+w/2), round(cy+ht*.62)))
            cropped.resize((width,height),Image.Resampling.LANCZOS).save(dest/(key+suffix+".webp"),quality=87)
