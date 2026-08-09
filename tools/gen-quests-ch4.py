#!/usr/bin/env python3
"""Additive one-shot: Act I Chapter 4 "Foothold" (act finale). Same
append-only pattern as gen-quests-ch3.py. Run once, then retire."""
import os, io, re

from afterlight_quests import SnbtLong, ftb_safe_id

OUT = os.path.join(os.path.dirname(__file__), '..', 'config', 'ftbquests', 'quests')
STORY_GROUP = '4525BB3160467FCB'
CACHE_TABLE_INT = SnbtLong.from_hex('1369E4AACBCDF5A1').value
LANG = []
_used = set()

def hid():
    while True:
        i = ftb_safe_id(os.urandom(8).hex().upper())
        if i not in _used:
            _used.add(i); return i

def esc(s): return s.replace('"', '\\"')
def lang(k, v): LANG.append((k, v))

CHIT = 'kubejs:requisition_chit'
ch4 = hid()
ch3_file = os.path.join(OUT, 'chapters', '770DAD173D9C234B.snbt')
CH3_LAST = re.findall(r'^\t\t\tid: "([0-9A-F]{16})"', open(ch3_file).read(), re.M)[-1]

Q = []
def quest(x, y, deps, tasks, rewards, title, subtitle, desc, shape=None, size=None):
    qid = hid()
    lang(f'quest.{qid}.title', title)
    if subtitle: lang(f'quest.{qid}.quest_subtitle', subtitle)
    if desc: lang(f'quest.{qid}.quest_desc', desc)
    Q.append((qid, x, y, deps, tasks, rewards, shape, size))
    return qid

def t_item(item, count=1, total=None):
    i = hid(); total = total or count
    return f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {total}L\n\t\t\t\tconsume_items: false }}'

def t_check():
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "checkmark" }}'

def t_energy(v):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "forge_energy"\n\t\t\t\tvalue: {v}L }}'

def r_item(item, count=1):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {count} }}'

def r_xp(xp):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "xp"\n\t\t\t\txp: {xp} }}'

def r_loot():
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "loot"\n\t\t\t\ttable_id: {CACHE_TABLE_INT}L }}'

a = quest(0.0, 0.0, [CH3_LAST], [t_check()], [r_item(CHIT, 4)],
    'Foothold',
    'Stop surviving. Start staying.',
    ["A scavenger passes through. An engineer stays and makes the ground obey.",
     "Claim your territory with the map tools (the Ascendancy called this cadastral registration; the map calls it claiming chunks). Then we build like we mean it."])
b = quest(2.0, -1.0, [a], [t_item('immersiveengineering:workbench')], [r_item(CHIT, 4)],
    "The Engineer's Bench",
    'Blueprints want a proper table.',
    ["The Ascendancy field manuals were printed on tin. They survive. An engineer's workbench reads them.",
     "This is where improvised ends and manufactured begins."])
c = quest(2.0, 1.0, [a], [t_item('immersiveengineering:coke_oven')], [r_item(CHIT, 5)],
    'Slow Fire',
    'The coke oven asks for patience.',
    ["Coal into coke, wood into charcoal, time into value. The oven is a multiblock; build it whole.",
     "Nothing about the old world was fast at first. Remember that when the reactors come."])
d = quest(4.0, 0.0, [b, c], [t_item('immersiveengineering:ingot_steel', 1, 12)], [r_item(CHIT, 8), r_xp(150)],
    'Steel Yourself',
    'Twelve ingots of intent.',
    ["Steel is iron that graduated. Twelve ingots says your foothold has a spine.",
     "The blast furnace remembers the recipe even when I do not. Trust the bricks."])
e = quest(6.0, -1.0, [d], [t_item('mekanismgenerators:heat_generator')], [r_item(CHIT, 5)],
    'First Current',
    'Electricity, rediscovered.',
    ["A heat generator: lava in, current out. Crude by Ascendancy standards. Miraculous by wasteland ones.",
     "This is the moment the lights start coming back on. I have waited four hundred years to log it."])
f = quest(6.0, 1.0, [d], [t_energy(100000)], [r_item(CHIT, 6), r_xp(100)],
    'Power Draw',
    'One hundred thousand units, banked.',
    ["Store one hundred thousand units of energy. Production without storage is a campfire; storage is a grid.",
     "ECHO logs every joule. Old habit. The auditors are dead, but standards are standards."])
g = quest(8.0, 0.0, [e, f], [t_check()], [r_loot(), r_item(CHIT, 20), r_xp(300)],
    'Act One: Foothold Secured',
    'The vault is behind you now.',
    ["Assessment: shelter, industry, steel, current. You are no longer a survivor of the Cascade. You are a participant in what comes after.",
     "&d[MEMORY FRAGMENT 03 RESTORED]&r",
     "&7...the evacuation boards listed every name in the sector. I have found my own maintenance designation on the list, marked STAYS WITH THE FACILITY. I did not remember volunteering. I am choosing to believe I did...&r",
     "&8Act Two is the Engine Room: Mekanism, logistics, the lattice. The Ascendancy's real toolbox. Rest first. Then we go deeper.&r"],
    shape='hexagon', size=1.6)

buf = io.StringIO(); w = buf.write
w('{\n\tdefault_hide_dependency_lines: false\n\tdefault_quest_shape: ""\n')
w(f'\tfilename: "{ch4}"\n\tgroup: "{STORY_GROUP}"\n')
w('\ticon: { id: "immersiveengineering:ingot_steel" }\n')
w(f'\tid: "{ch4}"\n\timages: [ ]\n\torder_index: 3\n\tquest_links: [ ]\n')
w('\tquests: [\n')
for qid, x, y, deps, tasks, rewards, shape, size in Q:
    w('\t\t{\n')
    w(f'\t\t\tid: "{qid}"\n')
    if deps:
        w('\t\t\tdependencies: [' + ', '.join(f'"{d_}"' for d_ in deps) + ']\n')
    w(f'\t\t\tx: {x}d\n\t\t\ty: {y}d\n')
    if shape: w(f'\t\t\tshape: "{shape}"\n')
    if size: w(f'\t\t\tsize: {size}d\n')
    w('\t\t\ttasks: [\n')
    for t in (tasks if isinstance(tasks, list) else [tasks]):
        w('\t\t\t\t' + t + '\n')
    w('\t\t\t]\n\t\t\trewards: [\n')
    for r_ in rewards:
        w('\t\t\t\t' + r_ + '\n')
    w('\t\t\t]\n\t\t}\n')
w('\t]\n}\n')
lang(f'chapter.{ch4}.title', 'Foothold')
open(os.path.join(OUT, 'chapters', ch4 + '.snbt'), 'w').write(buf.getvalue())

lp = os.path.join(OUT, 'lang', 'en_us.snbt')
s = open(lp).read().rstrip()
assert s.endswith('}')
s = s[:-1]
for k, v in LANG:
    if isinstance(v, list):
        s += f'\t{k}: [\n'
        for line in v:
            s += f'\t\t"{esc(line)}"\n'
        s += '\t]\n'
    else:
        s += f'\t{k}: "{esc(v)}"\n'
s += '}\n'
open(lp, 'w').write(s)
print(f'ch4={ch4} quests={len(Q)} lang+={len(LANG)}')
