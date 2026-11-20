"""Авторские материалы и верстка читательских разделов."""
from datetime import date
from html import escape
from pathlib import Path
import re

import yaml

HERE = Path(__file__).resolve().parent.parent / "content"


def load_articles():
    """Статьи из content/articles/*.md: шапка YAML, анонс, разделы ##, картинки ![подпись](путь)."""
    essays, pictures = [], {}
    files = []
    for path in (HERE / "articles").glob("*.md"):
        head, text = re.fullmatch(r"---\n(.*?)\n---\n(.*)", path.read_text(encoding="utf-8-sig"), re.S).groups()
        meta = yaml.safe_load(head)
        files.append((meta.get("order", 10**6), path.stem, meta, text))
    for _, slug, meta, text in sorted(files, key=lambda f: (f[0], f[1])):
        blocks = [" ".join(b.split()) for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
        intro, sections = [], []
        for block in blocks:
            if block.startswith("## "):
                sections.append([block[3:]])
            elif picture := re.fullmatch(r"!\[(.*)\]\((.+)\)", block):
                pictures[slug] = (len(sections) - 1, picture[2], picture[1])
            elif sections:
                sections[-1].append(block)
            else:
                intro.append(block)
        essays.append((slug, meta["category"], meta["title"], meta.get("card", ""), " ".join(intro),
                       [tuple(part) for part in sections]))
    return essays, pictures


ESSAYS, ILLUSTRATIONS = load_articles()

def illustration(image, caption):
    return (f'<figure class="article-illustration"><a href="art/{image}.webp">'
            f'<img loading="lazy" src="art/{image}.webp" alt="{escape(caption)}"></a>'
            f'<figcaption>{escape(caption)}</figcaption></figure>')

def lore_cards(items=None):
    return '<div class="journal-cards">'+''.join(
        f'<a href="{slug}.html"><img loading="lazy" src="art/{image}.webp" alt=""><div><small>{category} · Frontier</small><strong>{title}</strong><p>{intro}</p></div></a>'
        for slug,category,title,image,intro,_ in (ESSAYS if items is None else items))+'</div>'

def articles(page, register):
    for slug,category,title,image,intro,sections in ESSAYS:
        after, art, caption = ILLUSTRATIONS.get(slug, (None, None, None))
        body = ''.join('<section><h2>'+escape(part[0])+'</h2>'+''.join('<p>'+escape(p)+'</p>' for p in part[1:])+'</section>'
                       + (illustration(art,caption) if index==after else '') for index,part in enumerate(sections))
        page(slug+'.html',title,'atlas.html',f'<div class="wrap essay"><div class="crumb"><a href="frontier.html">Frontier</a> / Мир и история</div><article><small>{category}</small><h1>{title}</h1><p class="lead">{intro}</p>{body}</article><h2>Ещё об Иггдрасиле</h2>'+lore_cards([e for e in ESSAYS if e[0]!=slug][:3])+'</div>')
        register(title,slug+'.html',category,intro)

def feed():
    items=yaml.safe_load((HERE/'news.yaml').read_text(encoding='utf8'))
    html=[]
    for item in sorted(items,key=lambda e:(e['kind']=='Релиз перевода',e['date']),reverse=True):
        when=date.fromisoformat(item['date'])
        kind=escape(item['kind'])
        style='release' if kind=='Релиз перевода' else ''
        html.append(f'<li class="{style}"><time datetime="{when}">{when:%d.%m.%Y}</time><div><small>{kind}</small><a href="{escape(item["url"])}">{escape(item["title"])}</a><p>{escape(item["text"])}</p></div></li>')
    recent = '<ol class="newsfeed">'+''.join(html[:3])+'</ol>'
    archive = '<details><summary>Все обновления ('+str(len(html))+')</summary><ol class="newsfeed">'+''.join(html[3:])+'</ol></details>' if len(html)>3 else ''
    return recent+archive
