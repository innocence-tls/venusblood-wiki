"""Обновить data/frontier из проекта перевода в vn_kit.

Сборка вики читает только этот снимок, поэтому собирается на GitHub без vn_kit.
В снимок попадает минимум: написания терминов с публичной частью пояснений
(сам glossary.yaml с методикой в репозиторий не попадает), досье, игровые таблицы и короткие реплики,
которые реально цитируются на страницах. Полный перевод сценария сюда не копируется.

    python tools/import_frontier.py [--project путь/к/vn_kit/projects/vbfrontier]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--project", type=Path, default=ROOT.parent / "vn_kit/projects/vbfrontier")
project = parser.parse_args().project
dest = ROOT / "data/frontier"

# Файлы, которые нужны сборке целиком.
for name in ("vndb.txt", "work/raw/dat/mapitemlist.dat.txt",
             "work/raw/dat/mapdata.dat.txt", "work/translation/chapter_titles.md"):
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project / name, target)

# Из system.txt — только названия построек, которые есть в mapitemlist.
items = (project / "work/raw/dat/mapitemlist.dat.txt").read_text(encoding="utf8")
buildings = {n.replace("\\'", "'") for n in re.findall(r'"name" => "([^"]+)"', items)} | {"Brothel"}
system = [line for line in (project / "text/orig/system.txt").read_text(encoding="utf-8-sig").splitlines()
          if " = " in line and line.split(" = ", 1)[0] in buildings]
(dest / "text/orig").mkdir(parents=True, exist_ok=True)
(dest / "text/orig/system.txt").write_text("\n".join(system) + "\n", encoding="utf-8")

# Реплики: кандидаты в цитаты для словарных статей и реплики к портретам.
glossary = yaml.safe_load((project / "glossary.yaml").read_text(encoding="utf-8-sig")) or {}
aliases = {e["src"] for section in ("terms", "characters") for e in glossary.get(section) or []
           if e.get("src") and not e.get("regex") and len(e["src"]) > 1 and re.search(r"[ぁ-龯]", e["src"])}
VOICES = {"s001#0031", "s001#0032", "s001#0033", "s001#0057", "s001#0061", "s001#0097", "s001#0101",
          "s101#0001", "s101#0084", "s101#0152", "s101#0462", "s101#0464", "s101#0469", "s101#0475", "s203#0158"}
SCENES = {"s001", "s101", "s102", "s200", "s201", "s202"}
kept = []
for path in sorted((project / "work/translation/proof").glob("batch_[0-9][0-9][0-9].jsonl")):
    for line in path.read_text(encoding="utf8").splitlines():
        r = json.loads(line)
        ref = r["orig"].split("/")[-1].replace(".txt", "")
        quote = (r["scene"] in SCENES and 25 <= len(r["ru"]) <= 210 and "[" not in r["ru"]
                 and any(a in r["jp"] for a in aliases))
        if quote or ref in VOICES:
            kept.append({k: r[k] for k in ("orig", "scene", "speaker_en", "jp", "ru")})
(dest / "quotes.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
# Словарь: только то, что и так видно на сайте. Написания терминов и одно публичное
# пояснение на статью. Описания персонажей и рабочие пометки переводчиков не выносятся.
PRIVATE = re.compile(r"\b(?:[a-z]{1,3}\d{2,}|JP|EN|RU)\b|\.(?:ks|txt)|[гГ]лоссари|[пП]еревод|батч|[пП]ол в репликах"
                     r"|[пП]ерсонаж (?:мужского|женского) пола|[пП]одпись|[нН]аписани|[сС]ценари|[вВ]ариант строки|[сС]ловар")
people = yaml.safe_load((ROOT / "content/people.yaml").read_text(encoding="utf-8"))
person_names = {p["key"] for p in people} | {p["name"] for p in people if p["name"]} | {p["name"].split()[0] for p in people if p["name"].strip()}
terms, noted = [], set()
for e in glossary.get("terms") or []:
    if not (e.get("src") and e.get("dst")) or e.get("regex"):
        continue
    public = " ".join(t for t in re.split(r"(?<=[.!?])\s+", e.get("info") or "") if t and not PRIVATE.search(t))
    if public and (e["dst"] in noted or e["dst"] in person_names or e["src"] in person_names):
        public = ""
    if public:
        noted.add(e["dst"])
    terms.append({"src": e["src"], "dst": e["dst"], "info": public})
(dest / "terms.yaml").write_text(yaml.safe_dump({"terms": terms}, allow_unicode=True, sort_keys=False, width=10**6), encoding="utf-8")
print(f"data/frontier обновлён: {len(terms)} терминов, {len(kept)} кандидатов в цитаты, {len(system)} построек.")
# Сборка отмечает, какие реплики реально попали на страницы; остальные выбрасываются.
subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "build.py"), "--trim-quotes"], check=True)
