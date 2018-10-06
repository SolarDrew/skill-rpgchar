"""
Docstring
"""
import re
import logging
from functools import partial
from random import randint
from collections import OrderedDict as od

from opsdroid.matchers import match_regex

from .constants.regex_constants import *
from .characters import get_character, put_character
from .matchers import match_active_player


async def weapon_attack(attacker, defender, weapon, opsdroid, config, message):
    """
    Mechanical crunchy bits of actually making a weapon attack.
    Die rolls, damage, all that fun stuff
    """
    # Info
    atkr_name = attacker.name.split()[0] if ' ' in attacker.name else attacker.name
    def_name = defender.name.split()[0] if ' ' in defender.name else defender.name
    hitmiss = 'misses'

    # Make attack roll
    base_roll = randint(1, 20)
    mod = attacker.modifier(weapon['modifier'])
    atk_roll = [base_roll, attacker.proficiency, mod]
    atk_total = sum(atk_roll)
    if atk_total >= defender.AC or base_roll == 20 and base_roll != 1:
        hitmiss = 'hits'
        match = re.match("(?P<ndice>\d+)?(?:d(?P<dice>\d+))", weapon['damage'])
        ndice = match.group('ndice')
        ndice = int(ndice) if ndice else 1
        ndice = ndice * 2 if base_roll == 20 else ndice
        dice = int(match.group('dice'))

        rolls = list(map(partial(randint, 1), [dice]*ndice)) + [mod]
        total_damage = sum(rolls)

        await defender.take_damage(total_damage, opsdroid, config, message)
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


@match_regex(f'{OBJECT} {ATK_VERB} {SUBJECT} with {POSSESSIVE} {WEAPON}'
             f'( with (?P<adv>advantage|disadvantage))?',
             case_sensitive=False)
@match_active_player
async def attack(opsdroid, config, message):
    """
    Detect when a character is attacking another character.
    Just handles the overall flow of the interaction, rolls are dealt with elsewhere.
    """
    match = message.regex.group

    # Get characters
    atkr_name = match('object')
    if atkr_name.upper() == 'I':
        atkr_name = message.user
    attacker = await get_character(atkr_name, opsdroid, config, message)
    def_name = match('subject')
    defender = await get_character(def_name, opsdroid, config, message)
    weapon = match('weapon')
    adv = match('adv')
    if adv:
        adv = -1 if 'dis' in adv else 1
    logging.debug(adv)

    atk_roll, atk_total = await attacker.attack(defender, weapon,  message, adv)
    roll = atk_roll['roll']
    if atk_total >= defender.AC or roll == 20 and roll != 1:
        dmg_roll, dmg_total = await attacker.roll_damage(defender, weapon, message, opsdroid,
                                                         critical=(roll==20))


@match_regex(f'{OBJECT} {SPL_VERB} {HEAL_SPELL} on {SUBJECT}',
             case_sensitive=False)
@match_active_player
async def castheal(opsdroid, config, message):
    """
    Detect when a character is healing another character.
    Just handles the overall flow of the interaction, rolls are dealt with elsewhere.
    """
    match = message.regex.group

    # Get characters
    atkr_name = match('object')
    if atkr_name.upper() == 'I':
        atkr_name = message.user
    attacker = await get_character(atkr_name, opsdroid, config, message)
    def_name = match('subject')
    defender = await get_character(def_name, opsdroid, config, message)
    weapon = match('HEAL_SPELL')

    dmg_roll, dmg_total = await attacker.roll_heal(defender, weapon, message, opsdroid)


@match_regex(f'{OBJECT} {SPL_VERB} {ATK_SPELL} on {SUBJECT} '
             f'( with (?P<adv>advantage|disadvantage))?',
             case_sensitive=False)
@match_active_player
async def castdmg(opsdroid, config, message):
    """
    Detect when a character is attacking another character with a spell.
    Just handles the overall flow of the interaction, rolls are dealt with elsewhere.
    """
    match = message.regex.group

    # Get characters
    atkr_name = match('object')
    if atkr_name.upper() == 'I':
        atkr_name = message.user
    attacker = await get_character(atkr_name, opsdroid, config, message)
    def_name = match('subject')
    defender = await get_character(def_name, opsdroid, config, message)
    weapon = match('ATK_SPELL')
    adv = match('adv')
    if adv:
        adv = -1 if 'dis' in adv else 1
    logging.debug(adv)

    atk_roll, atk_total = await attacker.attack(defender, weapon, message, adv)
    roll = atk_roll['roll']
    if atk_total >= defender.AC or roll == 20 and roll != 1:
        dmg_roll, dmg_total = await attacker.roll_spelldamage(defender, weapon, message, opsdroid,
                                                              critical=(roll==20))
