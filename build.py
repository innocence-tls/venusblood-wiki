"""Собрать вики в _site/: python build.py

Тексты и данные — в content/, снимок материалов перевода — в data/frontier
(обновляется tools/import_frontier.py), стили и картинки — в static/.
"""
import argparse
import shutil
import sys
import json
import os
import re
from collections import defaultdict
from hashlib import sha256
from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from editorial import ESSAYS, articles, lore_cards, feed, illustration
from combat_guides import guides
from campaign import campaign_pages
from edda import edda_page
from edda_timing import timing_page
from screen_guides import screen_guides

CONTENT = ROOT / "content"
OUT = ROOT / "_site"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--trim-quotes", action="store_true", help="оставить в quotes.jsonl только реплики, которые попали на страницы")
parser.add_argument("--project", type=Path, default=ROOT / "data/frontier")
args = parser.parse_args()
project = args.project
used_quotes = []
shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(ROOT / "static", OUT)
profiles = (project / "vndb.txt").read_text(encoding="utf-8-sig")
glossary_file = project / "terms.yaml"
glossary = (yaml.safe_load(glossary_file.read_text(encoding="utf-8-sig")) or {}) if glossary_file.exists() else {}
entries = {}
for section in ("terms", "characters"):
    for entry in glossary.get(section, []) or []:
        src, dst = entry.get("src"), entry.get("dst")
        if src and dst and not entry.get("regex"):
            entries[src] = dst

def load(name):
    return yaml.safe_load((CONTENT / f"{name}.yaml").read_text(encoding="utf-8"))

def h(value):
    return escape(str(value), quote=True)

def write(filename, content):
    path = OUT / filename
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(content, encoding="utf-8")
    os.replace(pending, path)

published = {}

def page(filename, title, active, body):
    published[filename] = title
    sections = [("index.html","Главная"),("index.html#games","Игры"),("index.html#worlds","Мир Frontier"),("index.html#news","Новости"),("find.html","Поиск")]
    nav = "".join(f'<a href="{url}" {"aria-current=page" if filename == url else ""}>{text}</a>' for url,text in sections)
    topics = [("frontier.html","Об игре"),("story.html","Сюжет"),("people.html","Персонажи"),("atlas.html","Атлас"),("mechanics.html","Механика"),("walkthrough.html","Прохождение")]
    subnav = ""
    if active in dict(topics) and filename != "frontier.html":
        subnav = '<div class="subnav"><nav aria-label="Материалы Frontier">'+''.join(f'<a href="{url}" {"aria-current=page" if active==url else ""}>{text}</a>' for url,text in topics)+'</nav></div>'
    write(filename, f'''<!DOCTYPE html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)} · VenusBlood</title><link rel="stylesheet" href="style.css"><script defer src="search.js"></script>
<body><a class="skip" href="#main">К содержанию</a><header><div class="bar"><a class="brand" href="index.html"><i aria-hidden="true">✥</i> VenusBlood <small>ВИКИ</small></a><nav aria-label="Разделы">{nav}</nav></div></header>{subnav}<main id="main">{body}</main><footer><span>VenusBlood <b> / </b> Русская энциклопедия</span><a href="stats.html">Статистика статей</a><a href="sources.html">Об энциклопедии</a></footer></body></html>''')

def label(text):
    return f'<div class="label">{h(text)}</div>'

people = {}
for person in load("people"):
    key, fallback, role, bio, related = person["key"], person["name"], person["role"], person["bio"], person["related"]
    match = re.search(r"^(" + key + r"(?: Muspelheim)?)([ァ-ヿ＝]+)\s*$", profiles, re.M)
    if not match:
        raise ValueError(f"Нет профиля {key}")
    en, jp = match.groups()
    short_jp = jp.split("＝")[0]
    ru = next((entries[k] for k in (en, jp, key, short_jp) if k in entries), fallback)
    people[key] = dict(en=en, jp=jp, ru=ru, name=ru or key, role=role, bio=bio, related=related.split())

def link(key):
    return f'<a href="{key.lower()}.html">{h(people[key]["name"])}</a>'

regions = [
    ("Tyrca", "Восток", "Весна", "Edda", "На восточных лугах сходятся торговые пути. Страна живёт обменом и скотоводством. Именно сюда прибывает воздушный корабль претендента на трон."),
    ("Thor", "Юг", "Лето", "Thrudheim", "В южных лесах охотятся, в рудниках добывают металл. Военным делом ведает сама богиня, и её авторитет держится в том числе на личной храбрости."),
    ("Freya", "Запад", "Осень", "Folk", "Самая богатая и густонаселённая человеческая страна кормится земледелием. Зерно для её городов мелют башни-ветряки. Здесь записывают историю, изучают науки и чтят искусства."),
    ("Rigret", "Север", "Зима", "Glads", "Снежные бури определяют жизнь севера. Рыбная ловля и ремёсла помогают пережить долгие холода, а песни сохраняют местные традиции.")
]
places = {"Yggdrasil": "ユグドラシル", "Edda": "エッダ", "Thrudheim": "トルドハイム",
          "Folk": "フォルク", "Glads": "グラーズ", "Valhalla": "ヴァルハラ"}

def place_ru(name):
    return entries.get(name) or entries.get(places[name]) or ("Иггдрасиль" if name == "Yggdrasil" else "")

def place_name(name):
    return place_ru(name) or name

world = place_name("Yggdrasil")
def hero(kicker, heading, intro, art, action=""):
    return f'<section class="hero"><div>{label(kicker)}<h1>{heading}</h1><p>{intro}</p>{action}</div><img src="art/{art}.webp" alt="" class="heroart"></section>'

def cards():
    return '<div class="cards">' + "".join(f'<a class="card {key.lower()}" href="{key.lower()}.html"><img src="art/{key.lower()}.webp" alt=""><span>{label(direction+" · "+season)}<strong>{h(people[key]["name"])}</strong><small>{h(place_name(region))}</small></span></a>' for key,direction,season,region,_ in regions) + '</div>'

def topic_strip(items, name):
    return f'<nav class="topic-strip" aria-label="{h(name)}">'+''.join(
        f'<a href="{url}"><img src="art/{art}.webp" alt=""><span>{title}</span></a>' for title,url,art in items)+'</nav>'

world_topics=[
    ("Земли Иггдрасиля","atlas.html","atlas"),("Боги и люди","people-of-yggdrasil.html","portraits/odin-card"),
    ("Двор Утгарда","utgard.html","portraits/surt-card"),("Вера и культы","faith-in-yggdrasil.html","portraits/rigret-card"),
    ("Божественное оружие","thors-mjolnir.html","portraits/thor-card"),("Демоны и чудовища","names.html","portraits/fenrir-card")]
game_topics=[("Сюжет","story.html","chapters/a"),("Персонажи","people.html","portraits/loki-card"),
             ("Механика","mechanics.html","recruit"),("Прохождение","walkthrough.html","atlas")]
game_nav=topic_strip(game_topics,"Разделы игры")
page("frontier.html","VenusBlood Frontier","frontier.html",f"""<div class="wrap gamewiki"><div class="crumb"><a href="index.html#games">Игры серии</a> / Frontier</div><div class="gamecolumns"><article class="maincopy">
<h1>VenusBlood Frontier</h1>
<p>Владыка демонов Сурт обещает престол тому из своих внуков, кто добудет Сердце Иггдрасиля. Реликвию хранят богини на парящем континенте, где нашли приют люди после Рагнарёка. У наследников есть флот, войска и полная свобода расправляться друг с другом. Локи, сын казнённого мятежника, вступает в гонку на одном старом корабле «Синмара».</p>
{game_nav}
<h2>О кампании</h2>
<p>Frontier — шестая часть VenusBlood. Игрок ведёт армию Локи по владениям четырёх богинь времён года. В Эдде принца встречает воздушная конница Тирки. Когда восточный плацдарм закреплён, можно выбирать следующее направление вторжения. От этого выбора зависит, с кем Локи встретится раньше и какие силы окажутся в его распоряжении.</p>
<p>Между боями Локи набирает солдат и собирает из них отряды. Медальоны позволяют дать новобранцу титул с дополнительным навыком. В самой битве важно даже место бойца в строю: удачная засада может вывести противника из тыла под удар. <a href="mechanics.html#ambush">Как работает засада →</a></p>
<h2>Порядок и Хаос</h2><p>Захват столицы решает судьбу территории, но судьбу пленённой богини определяет Локи. Он может добиться её доверия или сломить сопротивление и обратить её силу против прежних союзниц. От выбора в сценах меняются показатели Порядка и Хаоса, а у героинь есть собственные концовки. Подробные условия разбираются в <a href="walkthrough.html">прохождении со спойлерами</a>.</p><p>Тем, кому интереснее история, лёгкая сложность позволяет пропускать бои с мгновенной победой. После первого прохождения открывается отдельный режим для тех, кто хочет сосредоточиться на стратегии. <a href="https://store.steampowered.com/app/1189440/">Описание International в Steam ↗</a></p>
<h2>Мир и герои</h2><p>Сурт посылает на Иггдрасиль пятерых внуков. Первой из богинь с Локи встречается Тирка: её всадники замечают над Эддой летучий корабль.</p>
<ul class="reading-list"><li><a href="utgard.html">Совет наследников Сурта</a> — кто поддержал Локи на совете наследников.</li><li><a href="sinmara.html">Летучий корабль «Синмара»</a> — почему Фена и Гарм согласились лететь в Эдду.</li><li><a href="people-of-yggdrasil.html">Четыре страны Иггдрасиля</a> — четыре страны под защитой Один и её дочерей.</li></ul></article>
<aside class="gamebox"><img src="art/cover-frontier.webp" alt="Оригинальная обложка Frontier"><dl><dt>Разработчик</dt><dd>Dual Tail</dd><dt>Жанр</dt><dd>Пошаговая стратегия, визуальная новелла</dd><dt>Первое издание</dt><dd>27 апреля 2012</dd><dt>International</dt><dd>20 декабря 2019</dd><dt>Steam</dt><dd>7 февраля 2020</dd></dl><div id="russian"><img class="poster" src="art/frontier-ru-poster.webp" alt="Постер русской версии: Локи и Тирка на фоне парящих островов"><b>Русский перевод вышел 21 ноября 2026</b><a href="https://t.me/innocence_translations/667">Скачать ↗</a></div><a href="https://ninetail.info/tde10/">Официальный сайт ↗</a></aside></div></div>""")
def heading(kicker,title,desc):
    return f'<div class="intro">{label(kicker)}<h1>{h(title)}</h1><p>{h(desc)}</p></div>'

def search(prompt):
    return f'<div class="filter" hidden><label for="query">Поиск</label><input type="search" id="query" placeholder="{prompt}"></div><p role="status" id="count"></p>'

groups = [("Поход принца",["Loki","Fena","Garm"]),("Хранительницы континента",["Odin","Tyrca","Thor","Freya","Rigret"]),("Императорский двор",["Surt","Hel","Fenrir","Jorm","Ymir","Menia"]),("Бог конца света",["Hvedrung"])]
relations = {
    "Fena": {"Loki":"Воспитанник", "Menia":"Старшая сестра-близнец", "Garm":"Спутник в походе"},
    "Menia": {"Fena":"Младшая сестра-близнец", "Surt":"Государь, которому служит"},
    "Loki": {"Fena":"Наставница по магии и этикету", "Garm":"Стрелок его отряда", "Surt":"Дед"},
    "Garm": {"Loki":"Командир, сын его прежнего господина", "Fena":"Спутница в походе"},
    "Surt": {**dict.fromkeys(["Loki","Hel","Fenrir","Jorm","Ymir"],"Претендент на престол"), "Menia":"Секретарь и защитница"},
    "Odin": dict.fromkeys(["Tyrca","Thor","Freya","Rigret"],"Одна из четырёх богинь, созданных Один"),
    "Hel": {"Fenrir":"Младшая сестра","Jorm":"Младшая сестра","Loki":"Двоюродный брат и соперник"},
    "Fenrir": {"Hel":"Старшая сестра","Jorm":"Младшая сестра"},
    "Jorm": {"Hel":"Старшая сестра","Fenrir":"Старшая сестра"},
    "Ymir": {"Surt":"Дед","Hel":"Соперница в борьбе за престол"},
    "Hvedrung": {"Loki":"Связь раскрывается в сюжетной справке"}
}
for key in ["Tyrca","Thor","Freya","Rigret"]:
    relations[key] = {"Odin":"Создательница", **{k:people[k]["role"]+" · сестра" for k in ["Tyrca","Thor","Freya","Rigret"] if k != key}}

def portrait_card(key, description=None):
    p = people[key]
    return (f'<a class="personcard" data-item href="{key.lower()}.html">'
            f'<div class="portraitframe"><img loading="lazy" src="art/portraits/{key.lower()}-card.webp" alt=""></div>'
            f'<div class="identity"><small>{h(description or p["role"])}</small><strong>{h(p["name"])}</strong>'
            f'<span>{h(p["en"])} · <span lang="ja">{h(p["jp"])}</span></span></div></a>')

catalog = "".join(f'<section data-group><h2>{title}</h2><div class="portraitgrid">'+
                  "".join(portrait_card(k) for k in keys)+'</div></section>' for title,keys in groups)
page("people.html","Персонажи","people.html",'<div class="wrap">'+heading("Frontier / Справочник","Персонажи","Участники борьбы за престол и хранительницы парящего континента.")+search("Имя, роль или японское написание")+catalog+'</div>')
profile_chapters=load("profile-chapters")
character_readings={
    "Loki":["sinmara","utgard"],"Fena":["sinmara"],"Garm":["sinmara","thors-mjolnir"],
    "Tyrca":["tyrca-and-sinmara"],"Thor":["thors-mjolnir"],"Rigret":["faith-in-yggdrasil"],
    "Odin":["people-of-yggdrasil"],"Freya":["people-of-yggdrasil"],"Surt":["utgard"],"Ymir":["utgard","faith-in-yggdrasil"]}
essay_titles={item[0]:item[2] for item in ESSAYS}
profile_art={"Fena":("scenes/fena-vanaheim","Фена раскрывает магический зонт Ванахейм."),"Garm":("scenes/sinmara-deck","С мостика «Синмары» Гарм замечает воздушную конницу Эдды."),"Loki":("scenes/loki-spear","Локи в бою с копьём."),"Surt":("scenes/utgard-audience","Зал аудиенций Сурта в Утгарде.")}
for key,p in people.items():
    region = next((r for r in regions if r[0]==key), None)
    atlaslink = f'<p><a href="atlas.html#{key.lower()}">{region[1]} · {h(place_name(region[3]))} →</a></p>' if region else ""
    faction = next(title for title, keys in groups if key in keys)
    bio = f'<p>{p["bio"]}</p>'
    if key == "Hvedrung":
        bio = '<details><summary>Открыть сюжетную справку</summary>'+bio+'</details>'
    if key in profile_art: bio+=illustration(*profile_art[key])
    for part in profile_chapters.get(key,[]):
        paragraphs="".join("<p>"+h(text)+"</p>" for text in part["paragraphs"])
        title=h(part["title"])
        bio += (f'<details><summary>{title} · спойлеры</summary>{paragraphs}</details>' if part["spoiler"] else f'<h2>{title}</h2>{paragraphs}')
    reading=character_readings.get(key,[])
    if reading:
        bio += '<h2>В истории Frontier</h2><ul>'+''.join(f'<li><a href="{slug}.html">{h(essay_titles[slug])}</a></li>' for slug in reading)+'</ul>'
    links = "".join(portrait_card(k,v) for k,v in relations[key].items())
    page(key.lower()+".html",p["name"],"people.html",
         f'<div class="wrap"><div class="crumb"><a href="frontier.html">Frontier</a> / <a href="people.html">Персонажи</a> / {h(faction)}</div>'
         f'<div class="dossier"><div class="dossierpic"><img src="art/portraits/{key.lower()}.webp" alt="Игровой портрет — {h(p["name"])}"></div>'
         f'<article>{label(faction)}<h1>{h(p["name"])}</h1><div class="role">{h(p["role"])}</div>'
         f'<p class="scripts">{h(p["en"])} · <span lang="ja">{h(p["jp"])}</span></p><h2>Досье</h2>{bio}{atlaslink}'
         '<a href="story.html">Сюжет Frontier →</a></article></div>'
         f'<section class="kin"><h2>Связи с персонажами</h2><div class="portraitgrid">{links}</div></section><a href="people.html">← Все персонажи</a></div>')
atlas = hero("Frontier / Атлас",h(world),"После Рагнарёка уцелевшие люди переселились на парящий континент. Четыре сестры оберегают его края. В центре находится святилище их создательницы.","atlas")
atlas += '<div class="wrap"><div class="sectionhead"><h2>Земли континента</h2></div><div class="regions">'
for key,direction,season,name,body in regions:
    atlas += f'<article id="{key.lower()}">{label(direction+" / "+season)}<h2>{h(place_name(name))}</h2><p>{body}</p>{link(key)} →</article>'
atlas += '</div><section class="reading"><h2>'+h(place_name("Valhalla"))+'</h2><div><p>Из центрального святилища хранительница наблюдает за людьми. Сёстрам она доверила повседневную заботу об их землях, оставив за собой право вмешаться в час бедствия.</p>'+link("Odin")+'</div></section></div>'
page("atlas.html",world,"atlas.html",atlas)
mechanics = """<div class="wrap">""" + heading("Frontier", "Механика Frontier", "От первого хода на карте до столкновения отрядов.") + """
<div class="prose">
<nav class="quick-index" aria-label="Содержание"><a href="#turn">Ходы</a> · <a href="#upkeep">Снабжение</a> · <a href="#moon">Луна</a> · <a href="#recruit">Наём</a> · <a href="#ambush">Засады</a> · <a href="#ailments">Состояния</a></nav>
<h2 id="turn">Шесть действий до боя</h2>
<p>Ход даёт шесть действий. Их тратят, например, на наём бойцов и встречи с героинями. Если начать бой, ход сразу закончится. Поэтому перед атакой удобно заглянуть в гарнизон города на карте, нанять недостающих бойцов и проверить здоровье своего отряда через «План».</p>
<h2 id="upkeep">Чем живёт армия</h2>
<p>У каждого бойца свой вид довольствия — еда или магия. Платить приходится при найме и после каждого боя, в котором он участвовал. Когда запаса не хватает, разницу берут золотом. Тем же золотом вы лечите раненых, строите здания и покупаете снаряжение. Если армия побеждает, а денег на лечение всё меньше, проверьте стоимость выхода отряда в разделе «План».</p>
<p>Постройки в захваченных городах приносят доход в конце хода. Рядом с каждым запасом показан его прирост. Смотрите на оба числа: разовая добыча помогает оплатить один поход, а гарнизоны придётся содержать и дальше.</p>
<h2 id="moon">День, ночь и фазы луны</h2>
<p>После каждого хода день сменяется ночью или ночь днём. После ночного хода луна переходит к следующей стихии. Полный круг проходит через огонь, лёд, ветер, землю, молнию, воду, свет и тьму. В свою фазу боец сильнее, а новый солдат той же стихии обойдётся дешевле и получит лучшие начальные параметры.</p>
<p>Противоположная луна снижает боевые параметры на четверть. Пары стихий — огонь и лёд, ветер и земля, молния и вода, свет и тьма. Перед штурмом посмотрите и на гарнизон: смена фазы может усилить его как раз к вашему приходу.</p>
<h2 id="recruit">Медальоны при найме</h2>
<p>Выберите бойца и проверьте цену. Для найма нужны медальоны и указанный ресурс — еда или магия. Пока боец не принят, ему можно дать титулы, которые меняют его параметры и навыки.</p>
<p>Перетащите медальон в одну из двух ячеек «Доп. медальоны». Стрелками рядом с ним выберите титул. Знак <b>&lt;</b> указывает на левую ячейку, <b>&gt;</b> — на правую. Для титула со знаком <b>&lt;&gt;</b> подходит любая. Нажмите «Нанять». На портрете принятого бойца появится звезда.</p>
<h2 id="ambush">Как срабатывает засада</h2>
<p>Сложите очки «Тактики засады» бойцов одного отряда и вычтите бдительность противника. Каждые полные десять оставшихся очков сдвигают вражеский строй на одну позицию. Например, при 19 очках строй сдвинется на одну позицию, при 20 — на две. Так можно вывести бойца из тыла под удар переднего ряда.</p>
<p>Ночью обе стороны получают по девять дополнительных очков засады. Бдительность противника всё ещё учитывается.</p>
<h2 id="ailments">Паралич, проклятие и чары</h2>
<ul>
<li><b>Паралич.</b> Каждое попадание с соответствующим навыком добавляет цели очки оглушения. Начиная с двух очков, боец теряет возможность действовать и применять тактические навыки. Бойцы стихии молнии невосприимчивы к параличу.</li>
<li><b>Проклятие.</b> Все параметры бойца падают на 10%. Он лишается возможности получать лечение до конца боя.</li>
<li><b>Чары.</b> Действуют на противника противоположного пола и лишают его возможности действовать до конца хода. «Полное очищение» от чар не защищает. Бойцы стихии огня к ним невосприимчивы.</li>
</ul>

</div></div>"""
mechanics = mechanics.replace('<h2 id="ambush">', '<figure class="guidepic"><a href="art/recruit.webp"><img src="art/recruit.webp" alt="Экран найма с ячейками медальонов и кнопкой «Нанять»"></a><figcaption>Экран найма в русском переводе. Нажмите на снимок, чтобы рассмотреть обозначения.</figcaption></figure><h2 id="ambush">')
page("sources.html","Об энциклопедии","","<div class='wrap essay'><article><h1>Об энциклопедии</h1><p>Русская фанатская вики VenusBlood посвящена играм Dual Tail. Здесь можно познакомиться с героями, разобраться в правилах войны и проследить за историей серии.</p><h2>У разработчиков</h2><ul><li><a href='https://ninetail.info/info_about.htm'>Ninetail и Dual Tail · история студии</a></li><li><a href='https://ninetail.info/tde10/'>Frontier · мир, персонажи и ход кампании</a></li><li><a href='https://store.steampowered.com/app/1189440/'>Frontier International в Steam</a></li></ul></article></div>")
series = load("series")
years = [row["year"] for row in series]
edition = {row["slug"]: row["international"] for row in series if row.get("international")}
summaries = {row["slug"]: row.get("summary", "") for row in series}
tiles = []
search_rows = []
def register(title,url,kind,aliases=""):
    search_rows.append([title,url,kind,aliases])

campaign_links = campaign_pages(page, register, illustration, project)
guide_links = guides(page, register, illustration)
screen_links = screen_guides(page, register, illustration)
mechanics = mechanics.replace(
    '<nav class="quick-index"',
    '<h2>Кампания и карта</h2>' + campaign_links + '<h2>Управление армией</h2>' + screen_links + '<h2>Боевые расчёты</h2>' + guide_links + '<nav class="quick-index"',
    1,
)
page("mechanics.html", "Механика Frontier", "mechanics.html", mechanics)
def gametitle(row):
    return row["title"] if row["slug"]=="venusblood" else "VenusBlood "+row["title"]
for idx,(row,year) in enumerate(zip(series,years,strict=True)):
    slug = row["slug"]
    url = "frontier.html" if slug=="frontier" else "game-"+slug+".html"
    title = gametitle(row)
    register(title,url,"Игра",edition.get(slug,""))
    tiles.append(f'<a class="boxart" href="{url}"><img loading="lazy" src="art/cover-{slug}.webp" alt=""><div><small>{year}</small><strong>{h(row["title"])}</strong></div></a>')
    if slug=="frontier": continue
    others = []
    for neighbor in series[max(idx-1,0):idx+2]:
        n=neighbor["slug"]
        if n!=slug: others.append(f'<a href="{("frontier" if n=="frontier" else "game-"+n)}.html">{h(gametitle(neighbor))}</a>')
    ed = f'<p><b>Международное издание</b> · {h(edition[slug])}</p>' if slug in edition else ""
    page(url,title,"index.html",f'<div class="wrap"><div class="crumb"><a href="index.html#games">Игры серии</a> / {h(row["title"])}</div><div class="gameabout"><img src="art/cover-{slug}.webp" alt="Обложка игры"><article>{label(str(year)+" / Dual Tail")}<h1>{h(title)}</h1><p>{h(summaries[slug])}</p>{ed}<p><a href="{h(row["url"])}">Официальная страница игры ↗</a></p><h2>Соседние выпуски</h2><div class="links">{"".join(others)}</div></article></div></div>')
episodes=load("episodes")
spin_sections=[]
for line_name in ("AfterDays","DarkChronicle"):
    episodes_in_line=[r for r in episodes if r["series"]==line_name]
    listing="".join(f'<li><a href="{h(r["url"])}">{r["episode"]}. <span lang="ja">{h(r["title"])}</span> ↗</a></li>' for r in episodes_in_line)
    spin_sections.append(f'<details><summary>{line_name} · {len(episodes_in_line)} эпизодов</summary><ul>{listing}</ul></details>')
international = {
    "FRONTIER":"https://ninetail.info/tde10/","HOLLOW (HYPNO)":"https://ninetail.info/tde12/index.html",
    "GAIA":"https://ninetail.info/CF/VenusBloodGAIA_International/","RAGNAROK":"https://ninetail.info/CF/VenusBloodRAGNAROK_International/index.html",
    "LAGOON":"https://ninetail.info/CF/VenusBloodLagoon_International/home_en.html"}
intl_links = "".join(f'<li><a href="{h(u)}">{h(t)} International ↗</a></li>' for t,u in international.items())
supplements = '<div class="editions"><details><summary>Международные издания</summary><ul>'+intl_links+'</ul></details>'+''.join(spin_sections)+'<details><summary>VenusBlood ORBIT</summary><p>Онлайн-ответвление серии. Сервис работал в 2021–2022 годах. <a href="https://ninetail.info/info_about.htm">Хронология разработчика ↗</a></p></details></div>'
def render_walkthrough():
    sections=load("walkthrough")
    index=[]
    body=[]
    for n,part in enumerate(sections,1):
        title=h(re.sub(r"^\d+\.\s*", "", part["title"]))
        anchor=f"step-{n}"
        index.append(f'<li><a href="#{anchor}">{title}</a></li>')
        paragraphs="".join(f"<p>{h(t)}</p>" for t in part["paragraphs"])
        if n==1:
            paragraphs+=illustration("scenes/campaign-map","Карта кампании. Города соединены дорогами, в нижней панели показаны запасы армии.")
        elif n==2:
            paragraphs+='<p><a href="edda.html">Маршрут, гарнизоны и развилки Эдды →</a></p>'
            paragraphs+=illustration("scenes/division-roster","Расстановка бойцов по отрядам. Выбранного бойца можно перетащить в свободную ячейку.")
        if part["spoiler"]:
            body.append(f'<details id="{anchor}"><summary>{title} · спойлеры</summary>{paragraphs}</details>')
        else:
            body.append(f'<section id="{anchor}"><h2>{title}</h2>{paragraphs}</section>')
    page("walkthrough.html","Прохождение Frontier","walkthrough.html",'<div class="wrap guide-layout"><article><div class="crumb"><a href="frontier.html">Frontier</a> / Прохождение</div><h1>Прохождение Frontier</h1><p><a href="campaign-start.html">Настройки кампании</a> · <a href="first-turn.html">Первый ход в Оулу</a> · <a href="edda.html">Первая глава. Завоевание Эдды</a></p><p>От прибытия в Эдду до выбора маршрута. Условия поздних развилок и концовок спрятаны под спойлер.</p><nav aria-label="Содержание"><ol>'+''.join(index)+'</ol></nav>'+''.join(body)+'</article></div>')
    register("Прохождение Frontier","walkthrough.html","Руководство","главы выбор земли порядок хаос концовки")
render_walkthrough()
edda_page(page, register, project)
timing_page(page, register)
articles(page, register)
page("index.html","Энциклопедия серии","index.html",
     '<div class="wrap library"><div class="welcome-row"><article class="welcome"><h1>VenusBlood</h1><p>VenusBlood — серия японских игр для взрослых от Dual Tail. В большинстве частей главы визуальной новеллы чередуются с пошаговыми сражениями. Игрок набирает бойцов в отряды и командует ими на карте.</p><p>Первая VenusBlood вышла в 2007 году. Во <a href="frontier.html">Frontier</a> наследники демонического трона вторгаются на парящий материк, в <a href="game-gaia.html">GAIA</a> летающий город Энергейя отбивается от драконьей империи.</p><p>Игры серии можно разделить на два лагеря. В играх о падении героинь (DESIRE, EMPIRE, Frontier, HYPNO, RAGNAROK, Savior, VALKYRIE) побеждённые богини и воительницы становятся тёмными версиями себя. В играх о кладке яиц (ABYSS, GAIA, BRAVE, Lagoon) героини не меняются: они откладывают яйца, из которых выходят новые бойцы армии. <a href="https://ninetail.info/info_about.htm">История Dual Tail ↗</a></p></article>'+
     '<aside class="gazette" id="news"><h2>Новости вики</h2>'+feed()+'</aside></div>'+
     '<section id="translated"><h2>Переведённые новеллы</h2><a class="translated-entry" href="frontier.html"><img class="poster" src="art/frontier-ru-poster.webp" alt=""><strong>VenusBlood Frontier International</strong><span>Русский перевод вышел 21 ноября 2026</span></a></section>'+
     '<section id="games"><div class="sectionhead"><h2>Игры серии</h2><span>По году выхода</span></div><div class="shelf">'+''.join(tiles)+'</div>'+supplements+'</section>'+
     '<section id="worlds"><div class="sectionhead"><h2>Мир Frontier</h2><a href="frontier.html">Об игре →</a></div>'+topic_strip(world_topics,"Лор Frontier")+'</section>'+'</div>')
register("Переведённые новеллы","index.html#translated","Новости","локализация")
register("Все части франшизы","index.html#games","Каталог","VenusBlood")
story = [
    ("Полярная ночь","До начала похода","Люди восстали против богов и демонов. Войну, потрясшую небо и землю, назвали Рагнарёком. Человечество оказалось на грани истребления. Выжившие нашли убежище на парящем континенте Иггдрасиль.","Odin","atlas.html","Атлас Иггдрасиля"),
    ("Совет наследников","Пролог","При дворе Утгарда собираются наследники Сурта. Локи приходит без приглашения. После казни отца принц лишился родового оружия, но от своего права на престол не отступил. Чтобы войти в спор, он ставит на кон положение при дворе.","Surt","loki.html","Досье Локи"),
    ("Курс на восток","Начало похода","Воздушный корабль Локи пересекает границу миров. Рядом с принцем Фена и Гарм. Первыми на пути оказываются восточные земли Тирки. Для Локи захват земель — часть борьбы за наследство, а для богини на кону судьба людей, которых она оберегает.","Tyrca","atlas.html#tyrca","Восточные земли")]
body = ""
for title,stage,desc,key,url,caption in story:
    body += f'<section class="episode"><a href="{key.lower()}.html"><img src="art/portraits/{key.lower()}-card.webp" alt="{h(people[key]["name"])}"></a><article>{label(stage)}<h2>{title}</h2><p>{desc}</p><a href="{url}">{caption} →</a></article></section>'
body += """<section class="prose"><h2>Почему поход начинается в Эдде</h2><p>Старой «Синмаре» достаточно один раз выдержать перелёт. Локи заранее решил, что людей и припасы раздобудет на месте. У торговой Эдды есть всё, чего недостаёт его маленькому отряду. Но когда навстречу поднимаются всадники на пегасах, оказывается, что до первого торга ещё надо пережить первую посадку. <a href="sinmara.html">История перелёта →</a></p><details><summary>Переговоры с Тиркой · первая глава</summary><p>Локи даёт Тирке повод самой поддерживать с ним связь. Ей нужны сведения о других наследниках Утгарда, ему — время и возможность освоиться в Эдде. Пока богини собираются у Один и обсуждают намерения пришельца, принц присматривается к местным торговцам и подпольной гильдии. Один и тот же город нужен ему и как рынок, и как опорный пункт в борьбе с родичами.</p></details><h2>После Эдды</h2><p>Людей у Локи хватает лишь на одну кампанию за раз. Из Эдды он может направиться в Фольк, Трудхейм, Гладс или Вальхаллу. В начале пятой главы остаётся последняя из четырёх земель. Поэтому порядок знакомства с их хранительницами у двух игроков может отличаться. Условия выбора и последствия развилок собраны в <a href="walkthrough.html">прохождении</a>.</p></section>"""
story_chapters = load("story-chapters")
chronicle = []
for chapter in story_chapters:
    title = h(chapter["title"])
    paragraphs = "".join(f"<p>{h(text)}</p>" for text in chapter["paragraphs"])
    if image := chapter.get("image"):
        caption = chapter.get("caption", "Игровая иллюстрация к разделу «" + chapter["title"] + "».")
        paragraphs += illustration(image, caption)
    if chapter["spoiler"]:
        chronicle.append(f'<details class="quotation"><summary>{title} · спойлеры</summary>{paragraphs}</details>')
    else:
        chronicle.append(f"<section><h3>{title}</h3>{paragraphs}</section>")
body += '<section class="prose" id="chronicle"><h2>Хроника похода</h2>' + "".join(chronicle) + '</section>'
register("Хроника похода", "story.html#chronicle", "Сюжет Frontier")
chapter_rows = (project / "work/translation/chapter_titles.md").read_text(encoding="utf8").splitlines()
chapter_cards = []
for chapter in chapter_rows:
    columns = [c.strip() for c in chapter.strip("|").split("|")]
    if not re.fullmatch("cap_txt[a-j]",columns[0]):
        continue
    letter = columns[0][-1]
    chapter_cards.append(f'<figure><a href="art/chapters/{letter}.webp"><img loading="lazy" src="art/chapters/{letter}.webp" alt="Заставка главы — {h(columns[3])}"></a><figcaption>{h(columns[3])}</figcaption></figure>')
body += ('<details class="chapterlist"><summary>Названия глав и развилки · сюжетные спойлеры</summary>'
         '<p>После первой главы порядок вторжений определяет, какая из четырёх земель станет следующей. Затем история возвращается к борьбе за ключ. У путей Порядка и Хаоса разные финалы. Последняя заставка относится к отдельному режиму.</p>'
         '<div class="chapters">'+''.join(chapter_cards)+'</div></details>')
page("story.html","Сюжет Frontier","story.html",'<div class="wrap">'+heading("Frontier / Сюжет","Поход на Иггдрасиль","От высадки в Эдде до финалов Порядка и Хаоса.")+body+'</div>')
for k,p in people.items(): register(p["name"],k.lower()+".html","Персонаж",p["en"]+" "+p["jp"]+" "+p["role"])

grouped = defaultdict(list)
for entry in glossary["terms"]:
    if entry.get("src") in entries and not entry.get("regex"):
        grouped[entry["dst"]].append(entry)
personal = {entries[alias]:k for k,p in people.items() for alias in (k,p["en"],p["jp"]) if alias in entries}
personal.update({dst:k for dst in grouped for k,p in people.items() if dst in (p["name"],p["name"].split()[0])})
singular = {"подвластные богини":"подвластная богиня"}
for plural,single in singular.items():
    if plural in grouped and single in grouped: grouped[single].extend(grouped.pop(plural))
urls = {dst:personal[dst].lower()+".html" if dst in personal else "term-"+sha256(items[0]["src"].encode()).hexdigest()[:12]+".html" for dst,items in grouped.items()}

def term_link(source):
    dst = entries.get(source)
    return f'<a href="{urls[dst]}">{h(dst)}</a>' if dst in urls else h(dst or source)

special = {
    "魔王":("В начале Frontier титул носит Сурт. Его наследники борются за престол Утгарда. Сурт объявляет о своём решении перед всем двором.",["Surt","Loki","Menia"]),
    "魔獣":("Адских зверей приручают и выводят в бой. В войске Фенрир они идут впереди демонов. Хель сама ухаживает за своей стаей.",["Fenrir","Hel"]),
    "魔物":("Так называют разных чудовищ. Например, в одной сцене под это определение подпадают и орк, и гоблин.",[]),
    "魔生物":("Так Локи называет существ, которых можно использовать в войне. В его записях рядом упоминаются химеры и огромные жуки.",["Loki"]),
    "魔族":("Общее название демонов как народа. В описании армии Фенрир их отличают от обученных для боя адских зверей.",["Fenrir"])}
# Иллюстративные реплики берём из принятых переводов основного сюжета.
passages=[]
for path in [project / "quotes.jsonl"]:
    for line in path.read_text(encoding="utf8").splitlines():
        record=json.loads(line)
        if record["scene"] in {"s001","s101","s102","s200","s201","s202"} and 25 <= len(record["ru"]) <= 210 and "[" not in record["ru"]:
            passages.append(record)
def public_note(items):
    for item in items:
        note=item.get("info","")
        sentences=re.split(r"(?<=[.!?])\s+",note)
        kept=[t for t in sentences if t and not re.search(r"\b(?:[a-z]{1,3}\d{2,}|JP|EN|RU)\b|\.(?:ks|txt)|[гГ]лоссари|[пП]еревод|батч|[пП]ол в репликах|[пП]ерсонаж (?:мужского|женского) пола|[пП]одпись|[нН]аписани|[сС]ценари|[вВ]ариант строки|[сС]ловар",t)]
        if kept: return " ".join(kept)
    return ""

for dst,items in sorted(grouped.items(),key=lambda pair:pair[0].casefold()):
    aliases=list(dict.fromkeys(e["src"] for e in items))
    url=urls[dst]
    if dst in personal:
        person_record=next(r for r in search_rows if r[1]==url)
        person_record[3]+=" "+" ".join(aliases)
        continue
    picked=next((special[a] for a in aliases if a in special),None)
    place=next((r for r in regions if r[3] in aliases),None)
    detail = picked[0] if picked else (place[4] if place else public_note(items))
    people_keys = picked[1] if picked else [place[0]] if place else [k for k,p in people.items() if re.search(r'(?<!\w)'+re.escape(p["name"].split()[0])+r'(?!\w)', detail)][:3]
    related = ('<h2>Связанные персонажи</h2><div class="portraitgrid">'+''.join(portrait_card(k) for k in people_keys)+'</div>') if people_keys else ''
    if picked: related += '<h2>Смежные понятия</h2><div class="links">'+''.join(term_link(a) for a in special if a not in aliases and a in entries)+'</div>'
    if "ユグドラシルの鍵" in aliases or "ユグドラシルの心臓" in aliases:
        counterpart="ユグドラシルの心臓" if "ユグドラシルの鍵" in aliases else "ユグドラシルの鍵"
        related+='<details class="quotation"><summary>Другое название · сюжетные спойлеры</summary><p>В истории Локи один и тот же предмет фигурирует под двумя именами. '+term_link(counterpart)+' →</p></details>'
    if place: related += f'<p><a href="atlas.html#{place[0].lower()}">Открыть в атласе →</a></p>'
    sample = next((r for r in passages if any(a in r["jp"] for a in aliases if re.search(r"[ぁ-龯]",a) and len(a)>1) and dst.split()[0].lower()[:max(4,len(dst.split()[0])-2)] in r["ru"].lower()),None)
    if sample:
        used_quotes.append(sample)
        excerpt=h(sample["ru"])
        related+=f'<details class="quotation"><summary>Упоминание в начале игры</summary><blockquote>{excerpt}</blockquote></details>'
    
    page(url,dst,"names.html",f'<div class="wrap term"><div class="crumb"><a href="frontier.html">Frontier</a> / Мир игры</div><article>{label("VenusBlood Frontier International")}<h1>{h(dst)}</h1><p class="scripts">{h(" · ".join(aliases))}</p><p class="definition">{h(detail)}</p></article>{related}<p><a href="atlas.html">К атласу Иггдрасиля →</a></p></div>')
utgard_people = load("utgard-people")
demons = []
for section in utgard_people:
    paragraphs = "".join(f"<p>{h(text)}</p>" for text in section["paragraphs"])
    if image := section.get("image"):
        paragraphs += illustration(image, section["caption"])
    demons.append(f'<section><h2>{h(section["title"])}</h2>{paragraphs}</section>')
page("names.html","Демоны Утгарда","atlas.html",
     '<div class="wrap essay"><article><div class="crumb"><a href="frontier.html">Frontier</a> / Народы</div>'
     '<h1>Демоны Утгарда</h1><div id="demons">'+ "".join(demons) +'</div>'
     '<a href="utgard.html">Совет наследников Сурта →</a></article></div>')
for title,url in [("Сюжет Frontier","story.html"),("Атлас Иггдрасиля","atlas.html"),("Персонажи Frontier","people.html"),("Бой и найм","mechanics.html"),("Демоны Утгарда","names.html#demons"),("Медальоны при найме","mechanics.html#recruit"),("Как срабатывает засада","mechanics.html#ambush")]: register(title,url,"Справочник")
results = ''.join(f'<a data-item href="{url}" class="wordrow"><strong>{h(title)}</strong><small>{h(kind)}</small><span>{h(aliases)}</span></a>' for title,url,kind,aliases in search_rows)
page("find.html","Поиск по вики","find.html",'<div class="wrap">'+heading("Энциклопедия","Поиск по вики","Игры, персонажи, статьи и варианты написания на трёх языках.")+search("Имя, часть серии или термин")+'<div class="wordgrid">'+results+'</div></div>')

navigation = {"index.html","find.html","sources.html","people.html"}
terms = {name for name in published if name.startswith("term-")}
full_articles = published.keys() - navigation - terms
games = {name for name in full_articles if name.startswith("game-")} | {"frontier.html"}
profiles_pages = {key.lower()+".html" for key in people}
rules = {"edda-timing.html","campaign-start.html","first-turn.html","construction.html","strategic-report.html","mechanics.html","growth.html","critical.html","tactical.html","damage.html","walkthrough.html","edda.html",
         "army-plan.html","recruitment.html","formation.html","equipment.html","call-events.html"}
groups = [("Игры серии", games), ("Персонажи", profiles_pages), ("Механика и прохождение", rules),
          ("Мир и сюжет", full_articles - games - profiles_pages - rules)]
sections = []
for name, pages in groups:
    links = ''.join(f'<li><a href="{url}">{h(published[url])}</a></li>' for url in sorted(pages,key=published.get))
    sections.append(f'<section><h2>{name} · {len(pages)}</h2><ul>{links}</ul></section>')
page("stats.html","Статистика статей","",f'<div class="wrap essay"><article><h1>Статистика статей</h1><p>Статей в энциклопедии — {len(full_articles)}. Коротких справок по игровым терминам — {len(terms)}.</p>'+''.join(sections)+'</article></div>')

# У каждого портрета — реплика из той же вычитанной версии, что идёт в патч.
voice_ids = {
    "Hel":"s001#0031","Jorm":"s001#0032","Loki":"s001#0033","Fenrir":"s001#0057",
    "Ymir":"s001#0061","Menia":"s001#0097","Surt":"s001#0101","Fena":"s101#0001",
    "Garm":"s101#0084","Tyrca":"s101#0152","Thor":"s101#0462","Odin":"s101#0464",
    "Freya":"s101#0469","Rigret":"s101#0475","Hvedrung":"s203#0158"}
wanted={ref:k for k,ref in voice_ids.items()}
for path in [project / "quotes.jsonl"]:
    if not wanted: break
    for line in path.read_text(encoding="utf8").splitlines():
        record=json.loads(line)
        ref=record["orig"].split("/")[-1].replace(".txt","")
        if ref not in wanted: continue
        key=wanted.pop(ref)
        used_quotes.append(record)
        if record["speaker_en"]!=key: raise ValueError("Неверный говорящий: "+ref)
        filename=key.lower()+".html"
        content=(OUT/filename).read_text(encoding="utf8")
        scene={"s001":"Совет наследников","s101":"Поход на Иггдрасиль","s203":"Сюжетная сцена"}[record["scene"]]
        quote=h(record["ru"].strip("'"))
        box=f'<details class="quotation"><summary>Реплика из игры · {scene}</summary><blockquote>«{quote}»</blockquote></details>'
        write(filename,content.replace('<section class="kin">',box+'<section class="kin">'))
# Первое упоминание в обычном абзаце ведёт к статье. Варианты падежей
# заданы явно, чтобы не путать имена с омонимами и частями других слов.
forms = {
    "Владыки демонов":"魔王","Владыке демонов":"魔王","Владыка демонов":"魔王",
    "Иггдрасиль":"Yggdrasil","Иггдрасиля":"Yggdrasil","Утгарда":"Utgard",
    "Рагнарёком":"Ragnarok","Локи":"Loki","Фена":"Fena","Фены":"Fena","Феной":"Fena",
    "Сурта":"Surt","Сурт":"Surt","Гарм":"Garm","Хель":"Hel","Тирки":"Tyrca","Тирка":"Tyrca",
    "Нибелунг":"Nibelung","Мьёльнир":"Mjolnir","Свати":"Svati","Бликьяндаболь":"Blikjandabol",
    "Мении":"Menia","Фенрир":"Fenrir","Фрейя":"Freya","Тор":"Thor"}
summaries_by_url = {k.lower()+".html": p["role"]+". "+p["bio"].split(". ")[0].rstrip(".")+"." for k,p in people.items()}
patterns = {w:urls[entries[a]] for w,a in forms.items() if a in entries and entries[a] in urls}
for dst, items in grouped.items():
    url = urls[dst]
    if url.startswith("term-"):
        note = public_note(items)
        if note: summaries_by_url[url] = note
    if url in summaries_by_url and len(dst)>3: patterns.setdefault(dst,url)
matcher = re.compile(r"(?<!\w)(?:"+"|".join(re.escape(w) for w in sorted(patterns,key=len,reverse=True))+r")(?!\w)")
for filename in ("frontier","story","atlas","names","walkthrough","mechanics",*(item[0] for item in ESSAYS),*(k.lower() for k in people)):
    name=filename+".html"
    content=(OUT/name).read_text(encoding="utf8")
    def link_paragraph(match):
        seen=set()
        def substitute(m):
            word=m.group()
            target=patterns[word]
            if target==name or target in seen: return word
            seen.add(target)
            tip=summaries_by_url.get(target)
            if tip: return f'<a href="{target}" data-preview="{h(tip)}">{word}</a>'
            return f'<a href="{target}">{word}</a>'
        return "<p>"+matcher.sub(substitute,match[1])+"</p>"
    write(name,re.sub(r"<p>([^<>]+)</p>",link_paragraph,content))

term_pages = {url for url in urls.values() if url.startswith("term-")}
print(f"{len(series)} игр, {len(people)} досье, {len(term_pages)} словарных статей, {len(entries)} исходных написаний.")
if args.trim_quotes:
    lines = [line for line in (project / "quotes.jsonl").read_text(encoding="utf8").splitlines()
             if json.loads(line) in used_quotes]
    (project / "quotes.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    print(f"В quotes.jsonl оставлено {len(lines)} реплик.")
