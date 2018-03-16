"""
Docstring
"""
import logging
import re
from functools import partial

from numpy.random import randint
import yaml
from opsdroid.matchers import match_regex

from .constants.regex_constants import *
# from .combat import attack
# from .characters import whoami, howami


class Character:
    def __init__(self, name, level, max_hp, race, class_, AC, abilities, current_hp=None, weapons={}):
        self.name = name
        self.level = level # Change this to XP and calculate level
        self.race = race
        self.class_ = class_
        self.max_hp = max_hp
        self.AC = AC # Replace this with a property that calculates AC
        self.abilities = abilities

        if current_hp:
            self.current_hp = current_hp
        else:
            self.current_hp = max_hp
        self.weapons = weapons

        self.unconscious = False
        self.death_saves = {'success': 0, 'fail': 0}

    def __repr__(self):
        return f"{self.name} ({self.race} {self.class_} {self.level})"

    def take_damage(self, n):
        self.current_hp -= n
        if self.current_hp <= self.max_hp / 2:
            self.die()
        elif self.current_hp < 0:
            self.unconscious = True

    def heal(self, n):
        self.current_hp = min(self.max_hp, self.current_hp+n)

    def modifier(self, ability):
        return (self.abilities[ability]-10) // 2

    @property
    def proficiency(self):
        return 2 # this obviously needs to change


def setup(opsdroid):
    logging.debug("Loaded rpgchar module")


async def get_character(name, opsdroid, config, message):

    # Remove burden of case-sensitivity from the user
    name = name.title()

    # Ensure that a list of the PCs exists
    pcs = await opsdroid.memory.get('pcs')
    if not pcs:
        pcs = {}
        await opsdroid.memory.put('pcs', pcs)

    if name not in pcs.keys():
        pcinfo = config['pcs'][name]
        if isinstance(config['pcs'][name], str):
            with open(pcinfo) as f:
                pcinfo = yaml.safe_load(f)
        charstats = pcinfo
        char = Character(**charstats)
        await put_character(char, opsdroid)
        await message.respond(f"Character {name} not in memory - loaded from config.")
        return char

    charstats = pcs[name]
    return Character(**charstats)


async def put_character(char, opsdroid):
    pcs = await opsdroid.memory.get('pcs')
    pcs[char.name.split()[0]] = char.__dict__
    await opsdroid.memory.put('pcs', pcs)


@match_regex('who am I', case_sensitive=False)
async def whoami(opsdroid, config, message):
    char = await get_character(message.user, opsdroid, config, message)

    await message.respond(f"You are {char}, a fearless adventurer!")


@match_regex(f"how ('?s|am|is) {SUBJECT}", case_sensitive=False)
# @match_rasanlu('hp-status')
async def howami(opsdroid, config, message):
    pcs = await opsdroid.memory.get('pcs')
    name = message.regex.group('subname')
    if name.upper() == 'I':
        name = message.user
        prefix = "You're"
    else:
        prefix = "They're"
    char = await get_character(name, opsdroid, config, message)

    state = char.current_hp / char.max_hp
    if state == 1:
        state_message = 'completely unharmed!'
    elif state > 0.5:
        state_message = 'feeling alright'
    elif state > 0.1:
        state_message = 'not feeling great'
    else:
        state_message = 'in mortal peril!'

    await message.respond(f"{prefix} {state_message} ({char.current_hp}/{char.max_hp})")


@match_regex(f'{OBJECT} {ATK_VERB} {SUBJECT} with (my|a) {WEAPON}', case_sensitive=False)
async def attack(opsdroid, config, message):
    match = message.regex.group
    pcs = await opsdroid.memory.get('pcs')

    # Get characters
    atkr_name = match('obname')
    if atkr_name.upper() == 'I':
        atkr_name = message.user
    attacker = await get_character(atkr_name, opsdroid, config, message)
    def_name = match('subname')
    defender = await get_character(def_name, opsdroid, config, message)
    weapon = attacker.weapons[match('weapon')]

    atk_report, defender = weapon_attack(attacker, defender, weapon)

    await put_character(defender, opsdroid)
    for msg in atk_report:
        await message.respond(msg)


def weapon_attack(attacker, defender, weapon):
    # Info
    atkr_name = attacker.name.split()[0] if ' ' in attacker.name else attacker.name
    def_name = defender.name.split()[0] if ' ' in defender.name else defender.name
    hitmiss = 'misses'

    # Make attack roll
    base_roll = randint(1, 21)
    mod = attacker.modifier('Str')
    atk_roll = [base_roll, attacker.proficiency, mod]
    atk_total = sum(atk_roll)
    if atk_total >= defender.AC or base_roll == 20 and base_roll != 1:
        hitmiss = 'hits'
        match = re.match("(?P<ndice>\d+)?(?:d(?P<dice>\d+))", weapon)
        ndice = match.group('ndice')
        ndice = int(ndice) if ndice else 1
        ndice = ndice * 2 if base_roll == 20 else ndice
        dice = int(match.group('dice'))

        rolls = list(map(partial(randint, 1), [dice+1]*ndice)) + [mod]
        total_damage = sum(rolls)

        defender.take_damage(total_damage)
    else:
        total_damage = 0
    critmod = ' critically ' if base_roll in [1, 20] else ' '

    # Report basic result of the attack
    report = [f"{atkr_name}{critmod}{hitmiss} {def_name}! "]
    # Add the roll, modifiers and total
    report[0] += f"({' + '.join(str(n) for n in atk_roll)} = {sum(atk_roll)}) !"
    # Add damage roll, modifiers and total, if any
    if total_damage > 0:
        report.append(f"{def_name.title()} takes {total_damage} damage ")
        report[1] += f"({' + '.join(str(r) for r in rolls)}) !"

    return report, defender
