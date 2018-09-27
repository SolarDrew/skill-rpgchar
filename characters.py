"""
Docstring
"""

import re
import yaml
import logging
from os.path import join
from random import randint
from functools import partial
from collections import OrderedDict as od

from opsdroid.matchers import match_regex

from .matchers import match_gm
from .constants.regex_constants import *
from .picard import load_from_memory, save_new_to_memory, update_memory, get_roomname


level_XPs = [0, 300, 900, 2700, 6500,
             14000, 23000, 34000, 48000, 64000,
             85000, 100000, 120000, 140000, 165000,
             195000, 225000, 265000, 305000, 355000]

# TODO come up with a subclass system for different character classes.
class Character:
    def __init__(self, name, level, max_hp, race, class_, AC, abilities,
                 XP=0, current_hp=None, weapons=None, unconscious=False,
                 death_saves={'success': 0, 'fail': 0}):
        self.name = name
        self.level = level # Change this to XP and calculate level
        self.race = race
        self.class_ = class_
        self.max_hp = max_hp
        self.AC = AC # Replace this with a property that calculates AC
        self.abilities = abilities

        self.XP = XP
        if current_hp:
            self.current_hp = current_hp
        else:
            self.current_hp = max_hp
        self.weapons = weapons

        self.unconscious = unconscious
        self.death_saves = death_saves

    def __repr__(self):
        return f"{self.name} ({self.race} {self.class_} {self.level})"

    async def take_damage(self, ndamage, opsdroid, message):
        """Handle removing of health from the character by e.g. a weapon attack."""
        # Damage happens
        self.current_hp -= ndamage

        # Need to handle cases in which damage causes unconsciousness or death
        # if self.current_hp <= self.max_hp / 2:
        #     self.die(opsdroid)
        # elif self.current_hp < 0:
        #     self.unconscious = True
        if self.current_hp < 0:
            await self.die(opsdroid, message)
        else:
            await put_character(self, opsdroid, message.room)

    def heal(self, nhealth):
        """Add health to the character up to their maximum hit points."""
        self.current_hp = min(self.max_hp, self.current_hp+nhealth)

    def gain_xp(self, nXP):
        self.XP += nXP
        if self.XP >= level_XPs[self.level]:
            self.level += 1
            return True
        return False

    def modifier(self, ability):
        """Return the modifier for a given ability"""
        return (self.abilities[ability]-10) // 2

    async def die(self, opsdroid, message):
        """Remove the character from the game without pissing off the player"""
        # Here because it's a circular import otherwise. Consider refactoring
        from .initiative import remove_from_initiative

        await remove_from_initiative(self.shortname(), opsdroid, message.room)
        chars = await load_from_memory(opsdroid, message.room, 'chars')
        chars.pop(self.shortname())
        await save_new_to_memory(opsdroid, message.room, 'chars', chars)
        await message.respond(f"{self.shortname()} died!")

    @property
    def proficiency(self):
        """Return the character's proficiency bonus as determined by level"""
        proficiencies = [2, 3, 4, 5, 6]
        return proficiencies[(int(self.level) - 1) // 4]

    def ability_check(self, ability, passive=False):
        """Make a check for the specified ability and return the roll, modifier and total"""
        base_roll = 10 if passive else randint(1, 20)
        check_roll = [base_roll, self.modifier(ability)]
        check_total = sum(check_roll)

        return check_total, check_roll

    def skill_check(self, skill, passive=False):
        """Make a check for the specified skill and return the roll, modifier and total"""
        # TODO No proficiency here, need to add that
        # TODO Also replace this big ugly if block with a dictionary somewhere.
        if skill.lower() == 'athletics':
            ability = 'Str'
        elif skill.lower() in ['acrobatics', 'sleight of hand', 'stealth']:
            ability = 'Dex'
        elif skill.lower() in ['arcana', 'history', 'investigation', 'nature', 'religion']:
            ability = 'Int'
        elif skill.lower() in ['animal handling', 'insight', 'medicine', 'perception', 'survival']:
            ability = 'Wis'
        elif skill.lower() in ['deception', 'intimidation', 'performance', 'persuasion']:
            ability = 'Cha'

        return self.ability_check(ability, passive=passive)

    async def attack(self, target, weapon_name, message, adv=None):
        weapon = self.weapons[weapon_name]
        # Get basic modifiers which apply to attack rolls generally
        mods = od({weapon['modifier']: self.modifier(weapon['modifier']),
                   'proficiency': self.proficiency})
        # Resolve any other conditions which would affect the roll

        if adv:
            a, b = randint(1, 20), randint(1, 20)
            base_roll = abs(max(a*adv, b*adv))
        else:
            base_roll = randint(1, 20)

        atk_roll = od()
        atk_roll['roll'] = base_roll
        atk_roll.update(mods)
        atk_total = sum(atk_roll.values())

        # Report result of the attack
        hitmiss = 'misses'
        critmod = ' critically ' if base_roll in [1, 20] else ' '
        if atk_total >= target.AC or base_roll == 20 and base_roll != 1:
            hitmiss = 'hits'
        hitmiss = 'critically ' + hitmiss if base_roll in [1, 20] else hitmiss
        await message.respond(f"{self.shortname()} {hitmiss} {target.shortname()}"
            f" with a roll of {atk_total}!")
        await message.respond(f"({', '.join([f'{name}: {val}' for name, val in atk_roll.items()])})")

        return atk_roll, atk_total

    async def roll_damage(self, target, weapon_name, message, opsdroid, critical=False):
        weapon = self.weapons[weapon_name]

        mods = od({weapon['modifier']: self.modifier(weapon['modifier'])})

        match = re.match("(?P<ndice>\d+)?(?:d(?P<dice>\d+))", weapon['damage'])
        ndice = match.group('ndice')
        ndice = int(ndice) if ndice else 1
        ndice = ndice * 2 if critical else ndice
        dice = int(match.group('dice'))

        dmg_roll = od()
        dmg_roll['roll'] = list(map(partial(randint, 1), [dice]*ndice))
        dmg_roll.update(mods)
        dmg_total = sum(dmg_roll['roll']) + sum(mods.values())

        await target.take_damage(dmg_total, opsdroid, message)

        await message.respond(f"{target.name} takes {dmg_total} damage!")
        await message.respond(f"({', '.join([f'{name}: {val}' for name, val in dmg_roll.items()])})")

        return dmg_roll, dmg_total

    def shortname(self):
        return self.name.split()[0] if ' ' in self.name else self.name


async def get_character(name, opsdroid, config, message, room=None):

    # Remove burden of case-sensitivity from the user
    # name = name.title()

    room = room if room else message.room

    # Ensure that a list of the characters exists
    chars = await load_from_memory(opsdroid, room, 'chars')

    logging.debug((name, chars.keys()))
    if name not in chars.keys():
        conn = opsdroid.default_connector
        for connroom in conn.rooms:
            if room == connroom or room == conn.room_ids[connroom]:
                roomname = connroom
                break
        if opsdroid.config.get('module-path', None):
            charstats = join(opsdroid.config['module-path'], 'characters',
                             config['campaigns'][roomname]['characters'][name])
        else:
            charstats = join('characters', config['campaigns'][roomname]['characters'][name])
        if isinstance(charstats, str):
            with open(charstats) as f:
                charstats = yaml.safe_load(f)
        elif 'loadfile' in charstats:
            file_ = charstats.pop('loadfile')
            with open(file_) as f:
                defaults = yaml.safe_load(f)
                defaults.update(charstats)
                charstats = defaults
            # defaults.update(charstats)
        logging.debug(charstats)
        char = Character(**charstats)
        await put_character(char, opsdroid, room, chars)
        await message.respond(f"Character {name} not in memory - loaded from config.")
        return char

    charstats = chars[name]
    return Character(**charstats)


@match_regex(f'!load( !usemem (?P<memroom>\w+))? ((?P<name>\D+)|((?P<n>\d)x)) (?P<file>.*)',
             case_sensitive=False)
@match_gm
async def load_character(opsdroid, config, message):
    match = message.regex.group
    name = match('name')
    ntimes = int(match('n')) if match('n') else 1
    room = match('memroom')
    room = room if room else message.room
    loadfile = match('file')

    # Remove burden of case-sensitivity from the user
    if name:
        name = name.title()
    else:
        name = loadfile.split('/')[1].title()+'_'
    if not loadfile[-5:] == '.yaml':
        loadfile += '.yaml'

    # Ensure that a list of the characters exists
    chars = await load_from_memory(opsdroid, room, 'chars')

    logging.debug((name, chars.keys()))
    if opsdroid.config.get('module-path', None):
        loadfile = join(opsdroid.config['module-path'], loadfile)
    for n in range(ntimes):
        with open(loadfile) as f:
            charstats = yaml.safe_load(f)
        if ntimes > 1:
            name = name[:-1] + str(n+1)
        charstats['name'] = name
        logging.debug(charstats)
        chars[name] = charstats
    await update_memory(opsdroid, room, 'chars', chars)
    await message.respond(f"Character loaded from config.")


@match_regex(f'!remove {OBJECT}( !usemem (?P<memroom>\w+))?', case_sensitive=False)
@match_gm
async def remove_character(opsdroid, config, message):
    match = message.regex.group
    name = match('object').title()
    room = match('memroom')
    room = room if room else message.room

    chars = await load_from_memory(opsdroid, room, 'chars')
    chars.pop(name)
    await save_new_to_memory(opsdroid, room, 'chars', chars)


@match_regex(f'!list characters( !usemem (?P<memroom>\w+))?', case_sensitive=False)
async def list_characters(opsdroid, config, message):
    room = message.regex.group('memroom')
    room = room if room else message.room
    chars = await load_from_memory(opsdroid, room, 'chars')
    await message.respond('\n'.join(
        [f'{Character(**chars[char])}' for char in chars])) # Could do with clearer var names here..


async def put_character(char, opsdroid, room, chars=None):
    """Save a character into memory"""
    if not chars:
        chars = await load_from_memory(opsdroid, room, 'chars')
    chars[char.name] = char.__dict__
    await update_memory(opsdroid, room, 'chars', chars)


@match_regex('who am I', case_sensitive=False)
async def whoami(opsdroid, config, message):
    """Basic reporting of character identity"""

    if message.user == config['game_master']:
        await message.respond(f"You're the Game Master! You don't have a character, silly!")
    else:
        char = await get_character(message.user, opsdroid, config, message)

        await message.respond(f"You are {char}, a fearless adventurer!")


@match_regex(f"how('?s| am| is) {SUBJECT}( !usemem (?P<memroom>\w+))?", case_sensitive=False)
async def howami(opsdroid, config, message):
    """Basic reporting of characters' current health."""
    name = message.regex.group('subject')
    if name.upper() == 'I':
        name = message.user
        prefix = "You're"
    else:
        prefix = "They're"
    room = message.regex.group('memroom')
    room = room if room else message.room

    char = await get_character(name, opsdroid, config, message, room)

    state = char.current_hp / char.max_hp
    if state == 1:
        state_message = 'completely unharmed!'
    elif state > 0.5:
        state_message = 'feeling alright'
    elif state > 0.1:
        state_message = 'not feeling great'
    else:
        state_message = 'in mortal peril!'

    msg_text =  f"{prefix} {state_message}" # ({char.current_hp}/{char.max_hp})"
    players = await get_players(opsdroid, config, message.room)
    if get_roomname(opsdroid, message.room) == 'main' or name.upper == 'I' or name in players:
        msg_text += f" ({char.current_hp}/{char.max_hp})"

    await message.respond(msg_text)


async def get_players(opsdroid, config, room):
    roomname = get_roomname(opsdroid, room)
    try:
        players = config['campaigns'][roomname]['characters'].keys()
    except KeyError:
        players = []

    return players


async def grant_xp(charname, nXP, opsdroid, config, message):
    char = await get_character(charname, opsdroid, config, message)
    levelup = char.gain_xp(match('nXP'))
    if levelup:
        await message.respond(f'{charname}, you have reached level {char.level}! Hooray!')


@match_regex(f'{OBJECT} {GAIN_VERB} (?P<nXP>\d+) XP', case_sensitive=False)
@match_gm
async def parse_xp(opsdroid, config, message):

    match = message.regex.group

    # Get character(s)
    charname = match('object')
    XP = match('nXP')

    # Handle granting XP to the whole group
    if charname.lower() in ['everyone', 'you all', 'the party', 'the group']:
        chars = await load_from_memory(opsdroid, message.room, 'chars')
        for charname in chars.keys():
            grant_xp(charname, XP, opsdroid, config, message)
    # Single character
    else:
        grant_xp(charname, XP, opsdroid, config, message)


@match_regex(f'{OBJECT},? makes? an? (?P<p>passive )?(?P<skill>\w+) check( !usemem (?P<memroom>\w+))?',
             case_sensitive=False)
async def make_check(opsdroid, config, message):
    match = message.regex.group
    charname = match('object')
    passive = match('p')
    room = match('memroom')
    room = room if room else message.room
    if charname.upper() == 'I':
        charname = message.user
    skill = match('skill').title()

    char = await get_character(charname, opsdroid, config, message, room)
    if skill in ['Str', 'Dex', 'Con', 'Int', 'Wis', 'Cha']:
        total, rolls = char.ability_check(skill, passive=passive)
    else:
        total, rolls = char.skill_check(skill, passive=passive)

    await message.respond(f"{charname} gets {total} ({' + '.join(str(r) for r in rolls)})!")


@match_regex(f'!setvalue {OBJECT} (?P<attribute>\w+) (?P<value>\d+)( !usemem (?P<memroom>\w+))?',
             case_sensitive=False)
@match_gm
async def set_value(opsdroid, config, message):
    match = message.regex.group
    charname = match('object')
    room = match('memroom')
    room = room if room else message.room

    char = await get_character(charname, opsdroid, config, message, room)
    setattr(char, match('attribute'), int(match('value')))
    await put_character(char, opsdroid, room)

@match_regex(f'!changevalue {OBJECT} (?P<attribute>\w+) (?P<value>(\+|-)\d+)'
             f'( !usemem (?P<memroom>\w+))?', case_sensitive=False)
@match_gm
async def _value(opsdroid, config, message):
    match = message.regex.group
    charname = match('object')
    attr = match('attribute')
    room = match('memroom')
    room = room if room else message.room

    char = await get_character(charname, opsdroid, config, message, room)
    setattr(char, attr, getattr(char, attr)+int(match('value')))
    await put_character(char, opsdroid, room)
