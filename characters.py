"""
Docstring
"""

import yaml
import logging
from os.path import join
from random import randint

from opsdroid.matchers import match_regex
from opsdroid.message import Message

from .constants.regex_constants import *


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

    async def take_damage(self, ndamage, opsdroid):
        """Handle removing of health from the character by e.g. a weapon attack."""
        # Damage happens
        self.current_hp -= ndamage

        # Need to handle cases in which damage causes unconsciousness or death
        # if self.current_hp <= self.max_hp / 2:
        #     self.die(opsdroid)
        # elif self.current_hp < 0:
        #     self.unconscious = True
        if self.current_hp < 0:
            await self.die(opsdroid)

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

    async def die(self, opsdroid):
        """Remove the character from the game without pissing off the player"""
        # Here because it's a circular import otherwise. Consider refactoring
        from .initiative import remove_from_initiative

        await remove_from_initiative(self.name, opsdroid)
        conn = opsdroid.connector
        msg = Message("", None, conn.default_room, conn)
        msg.respond(f"{self.name} died!")

    @property
    def proficiency(self):
        """Return the character's proficiency bonus as determined by level"""
        proficiencies = [2, 3, 4, 5, 6]
        return proficiencies[(self.level - 1) // 4]

    def ability_check(self, ability):
        """Make a check for the specified ability and return the roll, modifier and total"""
        base_roll = randint(1, 20)
        check_roll = [base_roll, self.modifier(ability)]
        check_total = sum(check_roll)

        return check_total, check_roll

    def skill_check(self, skill):
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

        return self.ability_check(ability)


async def get_character(name, opsdroid, config, message):

    # Remove burden of case-sensitivity from the user
    name = name.title()

    # Ensure that a list of the characters exists
    chars = await opsdroid.memory.get('chars')
    if not chars:
        chars = {}
        await opsdroid.memory.put('chars', chars)

    logging.debug((name, chars.keys()))
    if name not in chars.keys():
        if opsdroid.config.get('module-path', None):
            charstats = join(opsdroid.config['module-path'],
                             # 'opsdroid-modules', 'skill', 'rpgchar',
                             config['chars'][name])
        else:
            charstats = config['chars'][name]
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
        await put_character(char, opsdroid)
        await message.respond(f"Character {name} not in memory - loaded from config.")
        return char

    charstats = chars[name]
    return Character(**charstats)


@match_regex(f'!load (?P<name>\w+) (?P<file>.*)', case_sensitive=False)
async def load_character(opsdroid, config, message):
    match = message.regex.group
    name = match('name')
    loadfile = match('file')
    if not loadfile[-5:] == '.yaml': loadfile += '.yaml'

    # Remove burden of case-sensitivity from the user
    name = name.title()

    # Ensure that a list of the characters exists
    chars = await opsdroid.memory.get('chars')
    if not chars:
        chars = {}
        await opsdroid.memory.put('chars', chars)

    logging.debug((name, chars.keys()))
    if opsdroid.config.get('module-path', None):
        loadfile = join(opsdroid.config['module-path'], loadfile)
    with open(loadfile) as f:
        charstats = yaml.safe_load(f)
        charstats['name'] = name
    logging.debug(charstats)
    char = Character(**charstats)
    await put_character(char, opsdroid)
    await message.respond(f"Character loaded from config.")
    return char


async def put_character(char, opsdroid):
    """Save a character into memory"""
    chars = await opsdroid.memory.get('chars')
    chars[char.name.split()[0]] = char.__dict__
    await opsdroid.memory.put('chars', chars)


@match_regex('who am I', case_sensitive=False)
async def whoami(opsdroid, config, message):
    """Basic reporting of character identity"""

    if message.user == config['game_master']:
        await message.respond(f"You're the Game Master! You don't have a character, silly!")
    else:
        char = await get_character(message.user, opsdroid, config, message)

        await message.respond(f"You are {char}, a fearless adventurer!")


@match_regex(f"how ('?s|am|is) {SUBJECT}", case_sensitive=False)
async def howami(opsdroid, config, message):
    """Basic reporting of characters' current health."""
    name = message.regex.group('subject')
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

    msg_text =  f"{prefix} {state_message} ({char.current_hp}/{char.max_hp})"
    # if room == DM-private:
    #     msg_text += f"({char.current_hp}/{char.max_hp})"

    await message.respond(msg_text)


async def grant_xp(charname, nXP, opsdroid, config, message):
    char = await get_character(charname, opsdroid, config, message)
    levelup = char.gain_xp(match('nXP'))
    if levelup:
        await message.respond(f'{charname}, you have reached level {char.level}! Hooray!')


@match_regex(f'{OBJECT} {GAIN_VERB} (?P<nXP>\d+) XP', case_sensitive=False)
async def parse_xp(opsdroid, config, message):

    match = message.regex.group

    # Get character(s)
    charname = match('object')
    XP = match('nXP')

    # Handle granting XP to the whole group
    if charname.lower() in ['everyone', 'you all', 'the party', 'the group']:
        chars = await opsdroid.memory.get('chars', {})
        for charname in chars.keys():
            if charname.lower() == '_id':
                continue
            grant_xp(charname, XP, opsdroid, config, message)
    # Single character
    else:
        grant_xp(charname, XP, opsdroid, config, message)


@match_regex(f'{OBJECT},? makes? a (?P<skill>\w+) check', case_sensitive=False)
async def make_check(opsdroid, config, message):
    match = message.regex.group
    charname = match('object')
    skill = match('skill').title()

    char = await get_character(charname, opsdroid, config, message)
    if skill in ['Str', 'Dex', 'Con', 'Int', 'Wis', 'Cha']:
        total, rolls = char.ability_check(skill)
    else:
        total, rolls = char.skill_check(skill)

    await message.respond(f"{charname} gets {total} ({' + '.join(str(r) for r in rolls)})!")


@match_regex(f'!setvalue {OBJECT} (?P<attribute>\w+) (?P<value>\d+)', case_sensitive=False)
async def set_value(opsdroid, config, message):
    match = message.regex.group
    charname = match('object')

    char = await get_character(charname, opsdroid, config, message)
    char.set_attr(match('attribute'), match('value'))
    await put_character(char, opsdroid)
