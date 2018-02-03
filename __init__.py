import logging
from opsdroid.matchers import match_always, match_regex

class Character:
    def __init__(self, name, max_hp, race, class_, current_hp=None, weapons=[]):
        self.name = name
        self.race = race
        self.class_ = class_
        self.max_hp = max_hp
        if current_hp:
            self.current_hp = current_hp
        else:
            self.current_hp = max_hp
        weapons = weapons

    def __repr__(self):
        return f"{self.name} ({self.race} {self.class_})"

    def take_damage(self, n):
        self.current_hp -= n

    def heal(self, n):
        self.current_hp = min(self.max_hp, self.current_hp+n)


def setup(opsdroid):
    logging.debug("Loaded rpgchar module")


@match_always
async def confirm_existence(opsdroid, config, message):
    mem_pcs = await opsdroid.memory.get('pcs')
    if not mem_pcs:
        mem_pcs = {}

    if message.user not in mem_pcs.keys():
        await message.respond(f"Character {message.user} not in memory - creating from config.")
        charstats = config['pcs'][message.user]
        mem_pcs[message.user] = charstats

    await opsdroid.memory.put('pcs', mem_pcs)


@match_regex('who am I', case_sensitive=False)
async def whoami(opsdroid, config, message):
    pcs = await opsdroid.memory.get('pcs')
    char = Character(**pcs[message.user])

    await message.respond(f"You are {char}, a fearless adventurer!")


@match_regex('how (am|is) (?P<name>.*)', case_sensitive=False)
# @match_rasanlu('hp-status')
async def howami(opsdroid, config, message):
    pcs = await opsdroid.memory.get('pcs')
    name = message.regex.group('name')
    if name.upper() == 'I':
        char = Character(**pcs[message.user])
    else:
        char = Character(**pcs[name])

    state = char.current_hp / char.max_hp
    if state == 1:
        state_message = 'completely unharmed!'
    elif state > 0.5:
        state_message = 'feeling alright'
    elif state > 0.1:
        state_message = 'not feeling great'
    else:
        state_message = 'in mortal peril!'

    await message.respond(f"You're {state_message} ({char.current_hp}/{char.max_hp})")

