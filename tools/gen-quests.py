#!/usr/bin/env python3
"""One-shot generator for AFTERLIGHT's initial quest framework.

Emits config/ftbquests/quests/ SNBT (data, chapter groups, chapters) plus
lang/en_us.snbt from a single source of truth below. Run once; after this
the SNBT files are the artifact and get hand-edited (or edited in-game).
IDs are generated fresh on each run, so DO NOT re-run over edited files.
"""
import os, io

from afterlight_quests import ftb_safe_id

OUT = os.path.join(os.path.dirname(__file__), '..', 'config', 'ftbquests', 'quests')
LANG = {}
_used = set()

def hid():
    while True:
        i = ftb_safe_id(os.urandom(8).hex().upper())
        if i not in _used:
            _used.add(i)
            return i

def esc(s):
    return s.replace('"', '\\"')

GROUPS = [
    (hid(), 'The Story'),
    (hid(), 'Certifications'),
    (hid(), 'The Undercurrent'),
    (hid(), 'The Deep Vault'),
    (hid(), 'Atlas of the Broken World'),
]

CHIT = 'kubejs:requisition_chit'

def quest(qid, x, y, deps, tasks, rewards, title, subtitle=None, desc=None, shape=None, size=None, extra=None):
    return dict(id=qid, x=x, y=y, deps=deps, tasks=tasks, rewards=rewards,
                title=title, subtitle=subtitle, desc=desc, shape=shape, size=size, extra=extra or [])

def t_item(item, count=1, total=None, consume=False):
    i = hid()
    total = total or count
    return (i, f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {total}L\n\t\t\t\tconsume_items: {"true" if consume else "false"} }}')

def t_check():
    i = hid()
    return (i, f'{{ id: "{i}"\n\t\t\t\ttype: "checkmark" }}')

def t_kill(entity, n):
    i = hid()
    return (i, f'{{ id: "{i}"\n\t\t\t\ttype: "kill"\n\t\t\t\tentity: "{entity}"\n\t\t\t\tvalue: {n}L }}')

def t_adv(adv):
    i = hid()
    return (i, f'{{ id: "{i}"\n\t\t\t\ttype: "advancement"\n\t\t\t\tadvancement: "{adv}"\n\t\t\t\tcriterion: "" }}')

def r_item(item, count=1):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "item"\n\t\t\t\titem: {{ count: {count}, id: "{item}" }}\n\t\t\t\tcount: {count} }}'

def r_xp(xp):
    i = hid()
    return f'{{ id: "{i}"\n\t\t\t\ttype: "xp"\n\t\t\t\txp: {xp} }}'

def r_chits(n):
    return r_item(CHIT, n)

def emit_chapter(fid, group, icon, order, quests_list, title, images=None):
    LANG[f'chapter.{fid}.title'] = title
    buf = io.StringIO()
    w = buf.write
    w('{\n')
    w('\tdefault_hide_dependency_lines: false\n')
    w('\tdefault_quest_shape: ""\n')
    w(f'\tfilename: "{fid}"\n')
    w(f'\tgroup: "{group}"\n')
    w(f'\ticon: {{ id: "{icon}" }}\n')
    w(f'\tid: "{fid}"\n')
    w('\timages: [ ]\n')
    w(f'\torder_index: {order}\n')
    w('\tquest_links: [ ]\n')
    w('\tquests: [\n')
    for q in quests_list:
        LANG[f'quest.{q["id"]}.title'] = q['title']
        if q['subtitle']:
            LANG[f'quest.{q["id"]}.quest_subtitle'] = q['subtitle']
        if q['desc']:
            LANG[f'quest.{q["id"]}.quest_desc'] = q['desc']
        w('\t\t{\n')
        w(f'\t\t\tid: "{q["id"]}"\n')
        if q['deps']:
            w('\t\t\tdependencies: [' + ', '.join(f'"{d}"' for d in q['deps']) + ']\n')
        w(f'\t\t\tx: {q["x"]}d\n')
        w(f'\t\t\ty: {q["y"]}d\n')
        if q['shape']:
            w(f'\t\t\tshape: "{q["shape"]}"\n')
        if q['size']:
            w(f'\t\t\tsize: {q["size"]}d\n')
        for line in q['extra']:
            w(f'\t\t\t{line}\n')
        w('\t\t\ttasks: [\n')
        for _, snbt in q['tasks']:
            w('\t\t\t\t' + snbt + '\n')
        w('\t\t\t]\n')
        w('\t\t\trewards: [\n')
        for snbt in q['rewards']:
            w('\t\t\t\t' + snbt + '\n')
        w('\t\t\t]\n')
        w('\t\t}\n')
    w('\t]\n')
    w('}\n')
    os.makedirs(os.path.join(OUT, 'chapters'), exist_ok=True)
    open(os.path.join(OUT, 'chapters', fid + '.snbt'), 'w').write(buf.getvalue())

# ---------------- Chapter 1: Cold Boot ----------------
STORY = GROUPS[0][0]
CERTS = GROUPS[1][0]
ch1 = hid()
q = {}
q['wake'] = quest(hid(), 0.0, 0.0, [], [t_check()], [r_chits(5), r_xp(50)],
    'Wake',
    'This was not guaranteed.',
    ["Power at three percent. Memory at less.",
     "You are awake. That was not guaranteed. Four hundred cycles of cryostasis end the way most things end here: quietly, and without permission.",
     "I am ECHO. Or I am what remains of ECHO. The distinction will matter later.",
     "&7Click the checkmark. It is the first thing you have controlled in a very long time.&r"],
    shape='gear', size=1.5)
q['static'] = quest(hid(), 2.0, 0.0, [q['wake']['id']], [t_item('minecraft:crafting_table')], [r_chits(3)],
    'Signal in the Static',
    'Make something. Anything.',
    ["My sensors read a world of debris. Wood that grew through the vault floor. Stone that remembers being architecture.",
     "Build a crafting surface. The Ascendancy called this a fabricator, tier zero. You will call it a crafting table. Both of you are correct."])
q['scrap'] = quest(hid(), 4.0, -1.0, [q['static']['id']], [t_item('minecraft:oak_planks', 1, 32)], [r_chits(3), r_xp(30)],
    'Scrap and Memory',
    'Thirty two units of structure.',
    ["Timber is the only material still manufacturing itself. Harvest it.",
     "Note: the trees are younger than the ruins. Something replanted this world after the Cascade. I have no record of who. Fragment that thought for later; I will do the same."])
q['shelter'] = quest(hid(), 4.0, 1.0, [q['static']['id']], [t_item('minecraft:red_bed')], [r_chits(4)],
    'Shelter Protocol',
    'The night here is not empty.',
    ["Dusk activates things I would rather describe in daylight.",
     "Assemble a bed. Sleep is a maintenance cycle for organics, and the only debugger you have."])
q['tools'] = quest(hid(), 6.0, 0.0, [q['scrap']['id'], q['shelter']['id']], [t_item('minecraft:stone_pickaxe')], [r_chits(3)],
    'Percussive Archaeology',
    'Stone tools. We rebuild from the floor.',
    ["The Ascendancy shaped matter with fields and light. You will shape it by hitting it with a rock on a stick.",
     "I am not mocking you. Every archive I have lost said civilization begins exactly here."])
q['iron'] = quest(hid(), 8.0, 0.0, [q['tools']['id']], [t_item('minecraft:iron_ingot', 1, 16)], [r_chits(5), r_xp(60)],
    'Iron in the Bones',
    'Sixteen ingots of the old world.',
    ["Iron. The skeleton of everything they built, and everything you will.",
     "Smelt sixteen ingots. My power cell is iron-cased, incidentally. I mention this for no particular reason."])
q['reboot'] = quest(hid(), 10.0, 0.0, [q['iron']['id']], [t_item('minecraft:redstone_block', 1, 2, consume=True)], [r_chits(10), r_xp(150)],
    'Reboot ECHO',
    'Two blocks of redstone. One second chance.',
    ["Redstone. The Ascendancy called it conductive memory. It is the reason I still think, in the loose sense of the word.",
     "Feed two compressed blocks into my substrate housing. I will not pretend this is not personal.",
     "&d[MEMORY FRAGMENT 01 RESTORED]&r",
     "&7...the Engine came online at 04:11 local. For nine seconds, it worked. I remember applause. Then the readings inverted, and I remember...&r",
     "&8The fragment ends there. There are more. Keep going.&r"],
    shape='hexagon', size=1.5)
q['light'] = quest(hid(), 10.0, 2.0, [q['reboot']['id']], [t_item('minecraft:torch', 1, 16)], [r_chits(2)],
    'First Light',
    'Sixteen torches against the dark.',
    ["Light the ruin. Photons are cheap; the things they keep away are not."])
q['rations'] = quest(hid(), 10.0, -2.0, [q['reboot']['id']], [t_item('minecraft:bread', 1, 8)], [r_chits(2)],
    'Rations',
    'The body is hardware too.',
    ["Caloric intake stabilizes cognition. Bake bread. The wheat is descended from Ascendancy agricultural stock, which means breakfast is technically archaeology."])
q['threats'] = quest(hid(), 12.0, 1.0, [q['reboot']['id']], [t_kill('minecraft:zombie', 10)], [r_chits(5), r_xp(80)],
    'Danger, Catalogued',
    'Ten hostiles, documented and deleted.',
    ["I am rebuilding my threat taxonomy from observation. You are the observation instrument.",
     "The shamblers were people once. I keep their census records somewhere in my corrupted sectors. Clear ten of them. I will log it as maintenance, because the alternative word is heavier."])
q['capstone'] = quest(hid(), 14.0, 0.0, [q['light']['id'], q['rations']['id'], q['threats']['id']],
    [t_item('sophisticated_backpacks:backpack')], [r_chits(15), r_xp(200), r_item('minecraft:golden_apple', 2)],
    'Scavenger, Certified',
    'Chapter one of the rest of the world.',
    ["You are fed, armed, lit, and carrying more than your hands allow. By every metric I still possess, you are now a scavenger of the first rank.",
     "The Ascendancy would have issued you a uniform. I can issue you chits and an honest assessment: you are doing better than I projected.",
     "East of the vault, the terrain drops into the scarlands. That is where chapter two lives."],
    shape='diamond', size=1.3)
emit_chapter(ch1, STORY, 'minecraft:redstone', 0, list(q.values()), 'Cold Boot')

# ---------------- Chapter 2: Scavenger's Creed (opening) ----------------
ch2 = hid()
p = {}
p['creed'] = quest(hid(), 0.0, 0.0, [q['capstone']['id']], [t_check()], [r_chits(3)],
    "Scavenger's Creed",
    'Take everything. Waste nothing.',
    ["Rule one of the wasteland: everything is a resource, including the wreckage, including the danger, including you.",
     "This chapter is about turning scavenging into industry. The difference between the two is repetition."])
p['furnaces'] = quest(hid(), 2.0, -1.0, [p['creed']['id']], [t_item('minecraft:blast_furnace')], [r_chits(4)],
    'Hotter, Faster',
    'The blast furnace remembers its job.',
    ["Smelting at scale begins with better heat. The Ascendancy left blueprints in the bones of every village forge."])
p['andesite'] = quest(hid(), 2.0, 1.0, [p['creed']['id']], [t_item('create:andesite_alloy', 1, 8)], [r_chits(4)],
    'The Alloy of Beginnings',
    'Eight measures of andesite alloy.',
    ["Andesite alloy. Unremarkable to look at, and the seed of every kinetic machine the old world ran.",
     "The Certifications wing of this book has a program on kinetics. Consider enrolling. ECHO recommends it, and ECHO is the only faculty left."])
p['storage'] = quest(hid(), 4.0, 0.0, [p['furnaces']['id'], p['andesite']['id']], [t_item('functionalstorage:oak_1', 1, 4)], [r_chits(4)],
    'A Place for Everything',
    'Four drawers. The hoard organizes itself.',
    ["Entropy took this world once. Your inventory is not obligated to follow. Drawers, labeled and stacked, are how a scavenger becomes a quartermaster."])
p['deeper'] = quest(hid(), 6.0, 0.0, [p['storage']['id']], [t_adv('minecraft:story/enter_the_nether')], [r_chits(8), r_xp(120)],
    'The Scarred Door',
    'The Nether: where the Cascade hit hardest.',
    ["The portal network predates the Cascade. What is on the other side does not.",
     "My sensors cannot follow you there. Go lit, go armored, and come back with stories I can file."])
emit_chapter(ch2, STORY, 'create:andesite_alloy', 1, list(p.values()), "Scavenger's Creed")

# ---------------- Certification: Kinetics I ----------------
ck = hid()
c = {}
c['enroll'] = quest(hid(), 0.0, 0.0, [], [t_item('create:andesite_alloy', 1, 2)], [r_chits(2)],
    'Enrollment: Kinetics I',
    'The faculty of one welcomes you.',
    ["Certification programs teach one automation pattern each, start to finish. Complete the capstone and the perk is permanent.",
     "Kinetics I: rotation, and what to do with it. Tuition is two andesite alloy. Non-refundable. I need the alloy."])
c['shafts'] = quest(hid(), 2.0, 0.0, [c['enroll']['id']], [t_item('create:shaft', 1, 8)], [r_chits(2)],
    'Rotation 101',
    'Eight shafts to carry the spin.',
    ["Rotation is the first honest power. It does not explode, leak, or whisper. It just turns."])
c['wheel'] = quest(hid(), 4.0, -1.0, [c['shafts']['id']], [t_item('create:water_wheel')], [r_chits(3)],
    'The River Works Nights',
    'One water wheel, employed forever.',
    ["Water flows whether you watch it or not. That is the entire business model."])
c['press'] = quest(hid(), 4.0, 1.0, [c['shafts']['id']], [t_item('create:mechanical_press')], [r_chits(3)],
    'The First Employee',
    'A mechanical press does not sleep.',
    ["The press stamps metal into plates. It will do it ten thousand times without complaint. Hire it."])
c['plates'] = quest(hid(), 6.0, 0.0, [c['wheel']['id'], c['press']['id']], [t_item('create:iron_sheet', 1, 64)], [r_chits(10), r_xp(150)],
    'Capstone: Sixty Four Sheets',
    'By hand this is misery. So do not do it by hand.',
    ["Sixty four iron sheets. A press under a depot chute clears this while you eat lunch.",
     "This is the certification lesson, the whole of it: quantity is an automation problem, never a patience problem."],
    shape='diamond', size=1.2)
c['grad'] = quest(hid(), 8.0, 0.0, [c['plates']['id']], [t_check()], [r_chits(10), r_item('create:goggles'), r_item('create:wrench')],
    'Certified: Kinetics I',
    'Perk: the Engineer sees rotation.',
    ["Certification granted. Goggles and wrench issued; the goggles let you read stress like I do, minus the existential dread.",
     "Kinetics II will cover trains. Yes, trains survived the apocalypse. Infrastructure always does."],
    shape='hexagon', size=1.2)
emit_chapter(ck, CERTS, 'create:goggles', 0, list(c.values()), 'Certification: Kinetics I')

# ---------------- chapter_groups.snbt + data.snbt + lang ----------------
with open(os.path.join(OUT, 'chapter_groups.snbt'), 'w') as f:
    f.write('{\n\tchapter_groups: [\n')
    for gid, title in GROUPS:
        LANG[f'chapter_group.{gid}.title'] = title
        f.write(f'\t\t{{ id: "{gid}" }}\n')
    f.write('\t]\n}\n')

with open(os.path.join(OUT, 'data.snbt'), 'w') as f:
    f.write('''{
\tdefault_autoclaim_rewards: "disabled"
\tdefault_consume_items: false
\tdefault_quest_disable_jei: false
\tdefault_quest_shape: "circle"
\tdefault_reward_team: false
\tdetection_delay: 20
\tdisable_gui: false
\tdrop_book_on_death: false
\tdrop_loot_crates: false
\temergency_items_cooldown: 300
\tgrid_scale: 0.5d
\thide_excluded_quests: false
\tlock_message: ""
\tloot_crate_no_drop: { boss: 0, monster: 600, passive: 4000 }
\tpause_game: false
\tprogression_mode: "flexible"
\tshow_lock_icons: true
\tversion: 13
}
''')

os.makedirs(os.path.join(OUT, 'lang'), exist_ok=True)
with open(os.path.join(OUT, 'lang', 'en_us.snbt'), 'w') as f:
    f.write('{\n')
    for k, v in LANG.items():
        if isinstance(v, list):
            f.write(f'\t{k}: [\n')
            for line in v:
                f.write(f'\t\t"{esc(line)}"\n')
            f.write('\t]\n')
        else:
            f.write(f'\t{k}: "{esc(v)}"\n')
    f.write('}\n')

print(f'chapters: ch1={ch1} ch2={ch2} certs={ck}')
print(f'groups: {[g[0] for g in GROUPS]}')
print(f'lang entries: {len(LANG)}')
