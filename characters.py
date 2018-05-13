"""
Docstring
"""

import yaml
import logging
from opsdroid.matchers import match_regex

from .constants.regex_constants import *


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
        proficiencies = [2, 3, 4, 5, 6]
        return proficiencies[(self.level - 1) // 4]


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

    msg_text =  f"{prefix} {state_message}"
    # if room == DM-private:
    #     msg_text += f"({char.current_hp}/{char.max_hp})"

    await message.respond(msg_text)


