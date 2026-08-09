#!/usr/bin/env python3
"""Additive generator: Act I Chapter 3 "The Scarlands" + the Ascendancy
Cache reward table. Writes NEW files and APPENDS to lang/en_us.snbt.
Never touches existing chapters. One-shot like its sibling: run once,
then retire; hand-edit the SNBT afterward.
"""
import os, io

from afterlight_quests import SnbtLong, ftb_safe_id

OUT = os.path.join(os.path.dirname(__file__), '..', 'config', 'ftbquests', 'quests')
STORY_GROUP = '4525BB3160467FCB'
CH2_CAPSTONE_DEP = None  # chapter-level availability; ch3 quests depend on ch2's last quest id below
CH2_LAST = None
LANG = []
_used = set()

def hid():
    while True:
        i = ftb_safe_id(os.urandom(8).hex().upper())
        if i not in _used:
            _used.add(i)
            return i

def esc(s):
    return s.replace('"', '\\"')

def lang(k, v):
    LANG.append((k, v))

CHIT = 'kubejs:requisition_chit'
ch3 = hid()
table_id = hid()

# find ch2's final quest id (The Scarred Door) from the committed chapter file
ch2_file = os.path.join(OUT, 'chapters', '4C01977EF77930A6.snbt')
import re
ids = re.findall(r'^\t\t\tid: "([0-9A-F]{16})"', open(ch2_file).read(), re.M)
CH2_LAST = ids[-1]

Q = []
def quest(x, y, deps, tasks_snbt, rewards_snbt, title, subtitle, desc, shape=None, size=None):
    qid = hid()
    lang(f'quest.{qid}.title', title)
    if subtitle: lang(f'quest.{qid}.quest_subtitle', subtitle)
    if desc: lang(f'quest.{qid}.quest_desc', desc)
    Q.append((qid, x, y, deps, tasks_snbt, rewards_snbt, shape, size))
    return qid

def t_item(item, count=1, total=None):
    i = hid(); total = total or count
    return f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {total}L\n\t\t\t\tconsume_items: false }}'

def t_structure(s):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "structure"\n\t\t\t\tstructure: "{s}" }}'

def t_biome(b):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "biome"\n\t\t\t\tbiome: "{b}" }}'

def t_kill(e, n):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "kill"\n\t\t\t\tentity: "{e}"\n\t\t\t\tvalue: {n}L }}'

def t_dim(d):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "dimension"\n\t\t\t\tdimension: "{d}" }}'

def r_item(item, count=1):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {count} }}'

def r_xp(xp):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "xp"\n\t\t\t\txp: {xp} }}'

def r_loot():
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "loot"\n\t\t\t\ttable_id: {SnbtLong.from_hex(table_id).value}L }}'

a = quest(0.0, 0.0, [CH2_LAST], [t_biome('#minecraft:is_badlands')], [r_item(CHIT, 4)],
    'The Scarlands',
    'Where the map admits defeat.',
    ["The Cascade did not spread evenly. It pooled. The scarlands are one of the pools.",
     "Stand in the wound and look around. Everything that grows here grows in spite."])
b = quest(2.0, -1.0, [a], [t_structure('#minecraft:mineshaft')], [r_item(CHIT, 5), r_xp(80)],
    'Veins of the Old World',
    'Their mines run under everything.',
    ["The Ascendancy mined this continent hollow before they ever looked up at the stars. Find one of their shafts.",
     "Mind the supports. Four hundred years is a long shift without maintenance."])
c = quest(2.0, 1.0, [a], [t_kill('minecraft:skeleton', 15)], [r_item(CHIT, 5)],
    'Marksmen of Nothing',
    'Fifteen archers, retired.',
    ["Bone remembers posture. These remember guard duty. Whatever they are guarding now, it is not for you to inherit unchallenged."])
d = quest(4.0, 0.0, [b, c], [t_item('minecraft:diamond', 1, 5)], [r_item(CHIT, 8), r_xp(120)],
    'Pressure and Time',
    'Five diamonds out of the deep dark.',
    ["Carbon under pressure becomes the only currency the old world respected.",
     "You will need more than five, eventually. The Gate schematics I cannot fully read yet keep mentioning lattice cores. Start the habit."])
e = quest(6.0, 0.0, [d], [t_dim('minecraft:the_nether')], [r_loot(), r_item(CHIT, 10), r_xp(150)],
    'Through the Scarred Door',
    'Memory fragment on the far side.',
    ["Going through, then. I will hold the connection as far as the portal threshold.",
     "&d[MEMORY FRAGMENT 02 RESTORED]&r",
     "&7...evacuation routes C through F collapsed when the sky inverted. The Undercurrent was not coming FROM the breach. It was coming from everywhere. The breach was just where we finally noticed...&r",
     "&8Take the cache. The Ascendancy stocked them for a return that never happened.&r"],
    shape='hexagon', size=1.4)
Q_final = e

buf = io.StringIO(); w = buf.write
w('{\n')
w('\tdefault_hide_dependency_lines: false\n')
w('\tdefault_quest_shape: ""\n')
w(f'\tfilename: "{ch3}"\n')
w(f'\tgroup: "{STORY_GROUP}"\n')
w('\ticon: { id: "minecraft:netherrack" }\n')
w(f'\tid: "{ch3}"\n')
w('\timages: [ ]\n')
w('\torder_index: 2\n')
w('\tquest_links: [ ]\n')
w('\tquests: [\n')
for qid, x, y, deps, tasks, rewards, shape, size in Q:
    w('\t\t{\n')
    w(f'\t\t\tid: "{qid}"\n')
    if deps:
        w('\t\t\tdependencies: [' + ', '.join(f'"{d_}"' for d_ in deps) + ']\n')
    w(f'\t\t\tx: {x}d\n\t\t\ty: {y}d\n')
    if shape: w(f'\t\t\tshape: "{shape}"\n')
    if size: w(f'\t\t\tsize: {size}d\n')
    w('\t\t\ttasks: [\n\t\t\t\t' + tasks[0] + '\n\t\t\t]\n' if isinstance(tasks, list) and len(tasks)==1 else '')
    if isinstance(tasks, list) and len(tasks) > 1:
        w('\t\t\ttasks: [\n')
        for t in tasks: w('\t\t\t\t' + t + '\n')
        w('\t\t\t]\n')
    w('\t\t\trewards: [\n')
    for r in rewards: w('\t\t\t\t' + r + '\n')
    w('\t\t\t]\n')
    w('\t\t}\n')
w('\t]\n}\n')
lang(f'chapter.{ch3}.title', 'The Scarlands')
open(os.path.join(OUT, 'chapters', ch3 + '.snbt'), 'w').write(buf.getvalue())

# Ascendancy Cache reward table + loot crate
os.makedirs(os.path.join(OUT, 'reward_tables'), exist_ok=True)
tbl = io.StringIO(); w = tbl.write
w('{\n')
w(f'\tid: "{table_id}"\n')
w('\torder_index: 0\n')
w(f'\tfilename: "ascendancy_cache"\n')
w('\ticon: { id: "minecraft:chiseled_tuff_bricks" }\n')
w('\tloot_size: 3\n')
w('\tuse_title: true\n')
w('\tloot_crate: {\n')
w('\t\tstring_id: "ascendancy_cache"\n')
w('\t\tglow: true\n')
w('\t\tcolor: 4890847\n')
w('\t\tdrops: { boss: 0, monster: 0, passive: 0 }\n')
w('\t}\n')
w('\trewards: [\n')
for item, count, weight in [
    ('kubejs:requisition_chit', 6, 30.0), ('minecraft:iron_block', 3, 25.0),
    ('minecraft:golden_apple', 2, 15.0), ('minecraft:diamond', 3, 12.0),
    ('create:brass_ingot', 8, 12.0), ('mekanism:alloy_infused', 6, 12.0),
    ('minecraft:experience_bottle', 12, 20.0), ('minecraft:netherite_scrap', 1, 4.0),
    ('minecraft:enchanted_golden_apple', 1, 2.0)]:
    i = hid()
    w(f'\t\t{{ id: "{i}"\n\t\t\ttype: "item"\n\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\tcount: {count}\n\t\t\tweight: {weight}f }}\n')
w('\t]\n')
w('\ttitle: "Ascendancy Cache"\n')
w('}\n')
open(os.path.join(OUT, 'reward_tables', 'ascendancy_cache.snbt'), 'w').write(tbl.getvalue())

# append lang
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
print(f'ch3={ch3} table={table_id} quests={len(Q)} lang+={len(LANG)}')
