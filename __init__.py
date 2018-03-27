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


def setup(opsdroid):
    logging.debug("Loaded rpgchar module - ready to play Role-Playing Games!")


class Character:
    def __init__(self, name, level, max_hp, race, class_, AC, abilities,
                 current_hp=None, weapons=None, unconscious=False,
                 death_saves={'success': 0, 'fail': 0}):
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

        self.unconscious = unconscious
        self.death_saves = death_saves

    def __repr__(self):
        return f"{self.name} ({self.race} {self.class_} {self.level})"

    def take_damage(self, ndamage):
        """Handle removing of health from the character by e.g. a weapon attack."""
        # Damage happens
        self.current_hp -= ndamage

        # Need to handle cases in which damage causes unconsciousness or death
        if self.current_hp <= self.max_hp / 2:
            self.die()
        elif self.current_hp < 0:
            self.unconscious = True

    def heal(self, nhealth):
        """Add health to the character up to their maximum hit points."""
        self.current_hp = min(self.max_hp, self.current_hp+nhealth)

    def modifier(self, ability):
        """Return the modifier for a given ability"""
        return (self.abilities[ability]-10) // 2

    def die(self):
        """Remove the character from the game without pissing off the player"""
        pass

    @property
    def proficiency(self):
        """Return the character's proficiency bonus as determined by level"""
        return 2 # this obviously needs to change


async def get_character(name, opsdroid, config, message):

    # Remove burden of case-sensitivity from the user
    name = name.title()

    # Ensure that a list of the characters exists
    chars = await opsdroid.memory.get('chars')
    if not chars:
        chars = {}
        await opsdroid.memory.put('chars', chars)

    if name not in chars.keys():
        charinfo = config['chars'][name]
        if isinstance(config['chars'][name], str):
            with open(charinfo) as f:
                charinfo = yaml.safe_load(f)
        charstats = charinfo
        char = Character(**charstats)
        await put_character(char, opsdroid)
        await message.respond(f"Character {name} not in memory - loaded from config.")
        return char

    charstats = chars[name]
    return Character(**charstats)


async def put_character(char, opsdroid):
    """Save a character into memory"""
    chars = await opsdroid.memory.get('chars')
    chars[char.name.split()[0]] = char.__dict__
    await opsdroid.memory.put('chars', chars)


@match_regex('who am I', case_sensitive=False)
async def whoami(opsdroid, config, message):
    """Basic reporting of character identity"""
    char = await get_character(message.user, opsdroid, config, message)

    await message.respond(f"You are {char}, a fearless adventurer!")


@match_regex(f"how ('?s|am|is) {SUBJECT}", case_sensitive=False)
async def howami(opsdroid, config, message):
    """Basic reporting of characters' current health."""
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


def weapon_attack(attacker, defender, weapon):
    """
    Mechanical crunchy bits of actually making a weapon attack.
    Die rolls, damage, all that fun stuff
    """
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


@match_regex(f'{OBJECT} {ATK_VERB} {SUBJECT} with (my|a) {WEAPON}', case_sensitive=False)
async def attack(opsdroid, config, message):
    """
    Detect when a character is attacking another character.
    Just handles the overall flow of the interaction, rolls are dealt with elsewhere.
    """
    match = message.regex.group

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


@match_regex(f'(you|we) (take|have) a long rest', case_sensitive=False)
async def long_rest(opsdroid, config, message):
    """
    Do all the long rest things.
    At the moment this consists solely of giving everyone their hit points back.
    """

    chars = await opsdroid.memory.get('chars')
    for charname in chars.keys():
        if charname.lower() == '_id':
            continue
        char = await get_character(charname, opsdroid, config, message)
        char.current_hp = char.max_hp
        await put_character(char, opsdroid)
