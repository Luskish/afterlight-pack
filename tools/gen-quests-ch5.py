#!/usr/bin/env python3
"""Additive one-shot: Act II Chapter 5 "The Engine Room" (Mekanism entry).
Append-only lang pattern. Run once, then retire."""
import os, io, re

OUT = os.path.join(os.path.dirname(__file__), '..', 'config', 'ftbquests', 'quests')
STORY_GROUP = '4525BB3160467FCB'
CACHE_TABLE_INT = int('9369E4AACBCDF5A1', 16)
LANG = []
_used = set()

def hid():
    while True:
        i = os.urandom(8).hex().upper()
        if i not in _used:
            _used.add(i); return i

def esc(s): return s.replace('"', '\\"')
def lang(k, v): LANG.append((k, v))

CHIT = 'kubejs:requisition_chit'
ch5 = hid()
ch4_files = [f for f in os.listdir(os.path.join(OUT, 'chapters'))]
ch4_file = os.path.join(OUT, 'chapters', 'C5491A24F6B8C192.snbt')
CH4_LAST = re.findall(r'^\t\t\tid: "([0-9A-F]{16})"', open(ch4_file).read(), re.M)[-1]

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

def r_item(item, count=1):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {count} }}'

def r_xp(xp):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "xp"\n\t\t\t\txp: {xp} }}'

def r_loot():
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "loot"\n\t\t\t\ttable_id: {CACHE_TABLE_INT}L }}'

a = quest(0.0, 0.0, [CH4_LAST], [t_item('mekanism:ingot_osmium', 1, 8)], [r_item(CHIT, 5)],
    'The Engine Room',
    'Osmium: the Ascendancy loved it too.',
    ["Act Two. The vault taught you to survive; the Engine Room teaches you to multiply.",
     "Osmium first. Dense, obedient, everywhere under the scarlands. Every machine ahead of you eats it."])
b = quest(2.0, 0.0, [a], [t_item('mekanism:steel_casing', 1, 4)], [r_item(CHIT, 5)],
    'Casings',
    'Four frames for four futures.',
    ["A steel casing is a promise: whatever goes inside will be a machine, not a campfire with opinions.",
     "Four of them. You will spend them faster than you think."])
c = quest(4.0, -1.0, [b], [t_item('mekanism:metallurgic_infuser')], [r_item(CHIT, 4)],
    'The Infuser',
    'Where alloys begin.',
    ["Carbon into iron, redstone into osmium. The metallurgic infuser is the Engine Room's front door.",
     "The Ascendancy had a saying: every empire is an alloy. They were engineers; subtlety was not the discipline."])
d = quest(4.0, 1.0, [b], [t_item('mekanism:enrichment_chamber')], [r_item(CHIT, 6), r_xp(120)],
    'One Becomes Two',
    'The enrichment chamber doubles ore.',
    ["Listen carefully, because this is the sentence that changes your economy: one raw ore, two ingots.",
     "The chamber pays for itself by lunch. After this, mining is a choice, not a chore."])
e = quest(6.0, 0.0, [c, d], [t_item('mekanism:basic_universal_cable', 1, 16)], [r_item(CHIT, 4)],
    'Arteries',
    'Sixteen cables. The base gets a pulse.',
    ["Current wants to travel. Cables are how your generator stops being furniture and starts being infrastructure.",
     "Wire the infuser. Wire the chamber. Wire everything. I will pretend not to notice the mess."])
f = quest(8.0, 0.0, [e], [t_item('mekanism:energized_smelter')], [r_loot(), r_item(CHIT, 12), r_xp(200)],
    'The Room Hums',
    'Smelting without fire. Fragment recovered.',
    ["An energized smelter: heat with no flame, output with no ash. The Engine Room is officially online.",
     "&d[MEMORY FRAGMENT 04 RESTORED]&r",
     "&7...the Engine Room crews called their machines the choir. On shift-change recordings you can hear it: four hundred infusers in harmonic, singing the same note. The note was E. I have not heard E since the Cascade...&r",
     "&8Somewhere in your base, a machine just hummed. I logged the frequency. It is a start.&r"],
    shape='hexagon', size=1.5)

buf = io.StringIO(); w = buf.write
w('{\n\tdefault_hide_dependency_lines: false\n\tdefault_quest_shape: ""\n')
w(f'\tfilename: "{ch5}"\n\tgroup: "{STORY_GROUP}"\n')
w('\ticon: { id: "mekanism:steel_casing" }\n')
w(f'\tid: "{ch5}"\n\timages: [ ]\n\torder_index: 4\n\tquest_links: [ ]\n')
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
lang(f'chapter.{ch5}.title', 'The Engine Room')
open(os.path.join(OUT, 'chapters', ch5 + '.snbt'), 'w').write(buf.getvalue())

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
print(f'ch5={ch5} quests={len(Q)} lang+={len(LANG)}')
