import logging
from opsdroid.matchers import match_always, match_regex

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


@match_regex('how (am|is) (?P<name>.*)', case_sensitive=False)
# @match_rasanlu('hp-status')
async def howami(opsdroid, config, message):
    pcs = await opsdroid.memory.get('pcs')
    name = message.regex.group('name')
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


@match_regex('deals? (?P<ndamage>\d+) damage to (?P<target>.*)', case_sensitive=False)
async def damage(opsdroid, config, message):
    match = message.regex.group
    ndamage = int(match('ndamage'))
    target = match('target')

    pcs = await opsdroid.memory.get('pcs')
    char = await get_character(target, opsdroid, config, message)

    char.take_damage(ndamage)
    pcs[target] = char.__dict__
    await message.respond(f"Something is dealing {ndamage} to {target}")
    await put_character(defender, opsdroid)
