import logging
from opsdroid.matchers import match_always, match_regex

class Character:
    def __init__(self, name, max_hp, race, charclass, current_hp=None):
        self.name = name
        self.race = race
        self.class_ = charclass
        self.max_health = max_hp
        if current_hp:
            self.current_hp = current_hp
        else:
            self.current_hp = max_hp

    def __repr__(self):
        return f"{self.name} ({self.race} {self.class_})"


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


@match_regex('who am I')
async def whoami(opsdroid, config, message):
    pcs = await opsdroid.memory.get('pcs')
    char = Character(**pcs[message.user])

    await message.respond(f"You are {char}, a fearless adventurer!")
