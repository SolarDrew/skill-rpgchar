import logging

from opsdroid.helper import get_opsdroid

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

