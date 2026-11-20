"""Дороги первой главы по координатам и соседям из mapdata.dat."""
import re
from html import escape


def route_map(project, roster):
    data = (project/"work/raw/dat/mapdata.dat.txt").read_text("utf8")
    blocks = re.split(r"(?m)^ \(const\) %\[", data)[1:]
    records = {int(re.search(r'"index" => (\d+)', b)[1]):b for b in blocks}
    steps = (0,2,1,3,4,5,6,7,8,12,10,9,11)
    towns = {
        0:("Оулу","Лагерь на равнинах Оулу"), 1:("Курикка","Лес Курикка"),
        2:("Варкаус","Варкаус"), 3:("Паркано","Берег озера Паркано"),
        4:("Нокиа","Лес Нокиа"), 5:("Лоймаа","Берег озера Лоймаа"),
        6:("Иматра","Иматра"), 7:("Меркарвиа","Холм Меркарвиа"),
        8:("Босния","Река Босния"), 9:("Турку","Столица Турку"),
        10:("Лильендаль","Лильендаль"), 11:("Котка","Лагерь на равнинах Котки"),
        12:("Хамина","Берег озера Хамина"), 14:("Валтимо","Небесное ущелье Валтимо"),
        66:("Эребру","Небесное ущелье Эребру")}
    positions, roads = {}, set()
    for i in towns:
        b = records[i]
        y,x = map(int,re.search(r'"y" => (\d+),\s*"x" => (\d+)', b).groups())
        positions[i] = (x-770,y-460)
        adjacent = re.search(r'"node".*?\[(.*?)\]', b, re.S)[1]
        for other in map(int,re.findall(r"-?\d+",adjacent)):
            if other in towns:
                roads.add(tuple(sorted((i,other))))
    lines = []
    for i,j in sorted(roads):
        x,y = positions[i]
        xx,yy = positions[j]
        lines.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}"/>')
    nodes = []
    for i,(short,full) in towns.items():
        x,y = positions[i]
        number = str(steps.index(i)) if i in steps else "•"
        target = "#first-camp" if i == 0 else f"#edda-{i}"
        if i:
            cell = f"<td>{escape(full)}</td>"
            if cell not in roster:
                raise ValueError(f"Земля отсутствует в таблице гарнизонов: {full}")
            roster = roster.replace(cell, f'<td id="edda-{i}">{escape(full)}</td>',1)
        # Отнести подписи тесной центральной группы на разные стороны дорог.
        offset = -22 if i in (2,5,7,8,9,10,12,66) else 31
        if i == 66:
            offset = 31
        nodes.append(f'<a href="{target}" data-land="{i}" aria-label="{escape(full)}"><title>{escape(full)}</title>'
                     f'<circle cx="{x}" cy="{y}" r="14"/><text x="{x}" y="{y+5}">{number}</text>'
                     f'<text class="edda-label" x="{x}" y="{y+offset}">{short}</text></a>')
    figure = ('<figure class="edda-map"><svg viewBox="0 0 890 550" role="group" aria-label="Дороги Эдды">'
              +''.join(lines+nodes)+'</svg><figcaption>Круги отмечают земли, линии — прямые дороги. '
              'Номер совпадает с шагом в таблице захватов. Точками отмечены ущелья, которые в этом маршруте остаются Эдде. '
              'Название земли ведёт к её гарнизону.</figcaption></figure>')
    neighbors = {i: sorted(b if a==i else a for a,b in roads if i in (a,b)) for i in towns}
    options = ''.join(f'<option value="{i}" data-roads="{",".join(map(str,neighbors[i]))}" '
                      f'data-power="{3 if i==9 else 1}">{escape(full)}</option>'
                      for i,(_,full) in towns.items() if i)
    planner = ('<section class="edda-planner" hidden><h3>Свой маршрут</h3>'
               '<p>В списке появляются земли, до которых есть дорога из владений Локи. '
               'Каждый шаг засчитывает полный захват. Гарнизоны и потери в бою здесь не рассчитываются.</p>'
               '<label>Следующая земля <select>'+options+'</select></label> '
               '<button type="button" data-capture>Захватить</button> '
               '<button type="button" data-undo>Отменить ход</button>'
               '<p role="status" aria-live="polite"></p><ol></ol></section>')
    return figure+planner,roster
