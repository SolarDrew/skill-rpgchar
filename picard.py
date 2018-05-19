import logging

import aiohttp

from matrix_client.errors import MatrixRequestError

_LOGGER = logging.getLogger(__name__)


def get_matrix_connector(opsdroid):
    """
    Return the first configured matrix connector.
    """
    for conn in opsdroid.connectors:
        if conn.name == "ConnectorMatrix":
            return conn


async def room_id_if_exists(api, room_alias):
    """
    Returns the room id if the room exists or `None` if it doesn't.
    """
    if room_alias.startswith('!'):
        return room_alias
    try:
        room_id = await api.get_room_id(room_alias)
        return room_id
    except MatrixRequestError as e:
        if e.code != 404:
            raise e
        return None


async def joined_rooms(api):
    respjson = await api._send("GET", "/joined_rooms")
    return respjson['joined_rooms']


async def is_in_matrix_room(api, room_id):
    rooms = await joined_rooms(api)
    return room_id in rooms


async def intent_self_in_room(opsdroid, room):
    """
    This function should result in the connector user being in the given room.
    Irrespective of if that room existed before.
    """

    connector = get_matrix_connector(opsdroid)

    room_id = await room_id_if_exists(connector.connection, room)

    if room_id is None:
        try:
            respjson = await connector.connection.create_room(alias=room.split(':')[0][1:])
            room_id = respjson['room_id']
        except MatrixRequestError:
            room_id = await connector.connection.get_room_id(room)
        respjson = await connector.connection.join_room(room_id)
    else:
        is_in_room = is_in_matrix_room(connector.connection, room_id)

        if not is_in_room:
            respjson = await connector.connection.join_room(room_id)

    return room_id


async def intent_user_in_room(opsdroid, user, room):
    """
    Ensure a user is in a room.

    If the room doesn't exist or the invite fails, then return None
    """
    connector = get_matrix_connector(opsdroid)
    room_id = await room_id_if_exists(connector.connection, room)

    if room_id is not None:
        try:
            await connector.connection.invite_user(room_id, user)
        except MatrixRequestError as e:
            if "already in the room" in e.content:
                return room_id
            room_id = None

    return room_id


async def admin_of_community(opsdroid, community):
    """
    Ensure the community exists, and the user is admin otherwise return None.
    """

    connector = get_matrix_connector(opsdroid)

    # Check the Python SDK speaks communities
    if not hasattr(connector.connection, "create_group"):
        return None

    # Check community exists
    try:
        profile = await connector.connection.get_group_profile(community)
    except MatrixRequestError as e:
        if e.code != 404:
            raise e
        else:
            group = await connector.connection.create_group(community.split(':')[0][1:])
            return group['group_id']

    # Ensure we are admin
    if profile:
        users = await connector.connection.get_users_in_group(community)
        myself = list(filter(lambda key: key['user_id'] == connector.mxid, users['chunk']))
        if not myself[0]['is_privileged']:
            return None

    return community


async def make_community_joinable(opsdroid, community):
    connector = get_matrix_connector(opsdroid)

    content = {"m.join_policy": {"type": "open"}}
    await connector.connection._send("PUT", f"groups/{community}/settings/m.join_policy",
                                     content=content)



"""
Break up all the power level modifications so we only inject one state event
into the room.
"""


async def set_power_levels(opsdroid, room_alias, power_levels):
    connector = get_matrix_connector(opsdroid)
    room_id = await room_id_if_exists(connector.connection, room_alias)
    return await connector.connection.set_power_levels(room_id, power_levels)


async def get_power_levels(opsdroid, room_alias):
    connector = get_matrix_connector(opsdroid)
    room_id = await room_id_if_exists(connector.connection, room_alias)

    return await connector.connection.get_power_levels(room_id)


async def user_is_room_admin(power_levels, room_alias, mxid):
    """
    Modify power_levels so user is admin
    """
    user_pl = power_levels['users'].get(mxid, None)

    # If already admin, skip
    if user_pl != 100:
        power_levels['users'][mxid] = 100

    return power_levels


async def room_notifications_pl0(power_levels, room_alias):
    """
    Set the power levels for @room notifications to 0
    """

    notifications = power_levels.get('notifications', {})
    notifications['room'] = 0

    power_levels['notifications'] = notifications

    return power_levels


async def configure_room_power_levels(opsdroid, config, room_alias):
    """
    Do all the power level related stuff.
    """
    connector = get_matrix_connector(opsdroid)
    room_id = await room_id_if_exists(connector.connection, room_alias)

    # Get the users to be made admin in the matrix room
    users_as_admin = config.get("users_as_admin", [])

    power_levels = await get_power_levels(opsdroid, room_id)

    # Add admin users
    for user in users_as_admin:
        await intent_user_in_room(opsdroid, user, room_id)
        power_levels = await user_is_room_admin(power_levels, room_id, user)

    room_pl_0 = config.get("room_pl_0", False)
    if room_pl_0:
        power_levels = await room_notifications_pl0(power_levels, room_id)

    # Only actually modify room state if we need to
    if users_as_admin or room_pl_0:
        await set_power_levels(opsdroid, room_id, power_levels)


"""
Helpers for room avatar
"""


async def upload_image_to_matrix(self, image_url):
    """
    Given a URL upload the image to the homeserver for the given user.
    """
    async with aiohttp.ClientSession() as session:
        async with session.request("GET", image_url) as resp:
            data = await resp.read()

    respjson = await self.api.media_upload(data, resp.content_type)

    return respjson['content_uri']


async def set_room_avatar(opsdroid, room_id, avatar_url):
    """
    Set a room avatar.
    """
    connector = get_matrix_connector(opsdroid)

    if not avatar_url.startswith("mxc"):
        avatar_url = await upload_image_to_matrix(avatar_url)

    # Set state event
    content = {
        "url": avatar_url
    }

    return await connector.connection.send_state_event(room_id,
                                                       "m.room.avatar",
                                                       content)
