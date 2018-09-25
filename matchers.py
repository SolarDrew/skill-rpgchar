import logging

from opsdroid.helper import get_opsdroid

from .picard import load_from_memory

_LOGGER = logging.getLogger(__name__)


def match_gm(func):
    """Define GM-matching decorator"""
    async def matcher(opsdroid, config, message):
        """Restrict the use of `func`'s skill to only the Game Master"""
        gm = config['game_master']
        user = message.user
        _LOGGER.debug("Matching user to GM")
        _LOGGER.debug(f'GM: {gm}; User: {user}')

        if user == gm:
            return await func(opsdroid, config, message)
        else:
            return await message.respond("I can't let you do that, Dave. That functionality is reserved for the Game Master")

    return matcher


def match_active_player(func):
    """Define decorator to match the active player"""
    async def matcher(opsdroid, config, message):
        """Restrict the decorated functions actions to the person whose turn it is (and the GM)"""
        gm = config['game_master']
        active_player = await load_from_memory(opsdroid, message.room, 'active_player')
        active_player = active_player['name']
        user = message.user

        _LOGGER.debug("Matching user to active player")
        _LOGGER.debug(f"Active player: {active_player}; User: {user} (GM: {gm})")

        if user in [active_player, gm]:
            return await func(opsdroid, config, message)
        else:
            return await message.respond(f"You wait your damn turn, {user}!")

    return matcher
