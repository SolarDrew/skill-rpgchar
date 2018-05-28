"""
Docstring
"""

import yaml
import logging
from os.path import join

from opsdroid.matchers import match_regex

from .constants.regex_constants import *
from .picard import load_from_memory, save_new_to_memory, update_memory, get_roomname


@match_regex(f"!goto ((?P<filename>\d\d-\w+.yaml)|(?P<exit>\w+))( !usemem (?P<memroom>\w+))?")
async def load_scene(opsdroid, config, message):
    """Load information about a scene or location from the specified file."""
    match = message.regex.group
    fname = match('filename')
    newscene = match('exit')
    room = match('memroom')
    room = room if room else message.room

    dm_scenes = await load_from_memory(opsdroid, 'main', 'scenes')
    roomname = get_roomname(opsdroid, room)
    current_scene = dm_scenes.get(roomname, None)
    if not fname:
        fname = current_scene['exits'][newscene]
    folder = join('scenes', config['campaigns'][roomname]['name'])
    if opsdroid.config.get('module-path', None):
        folder = join(opsdroid.config['module-path'], folder)
    fname = join(folder, fname)
    with open(fname) as f:
        scene_info = yaml.safe_load(f)

    # Check the scene against previously visited scenes and do things if it's new
    previous_scenes = await load_from_memory(opsdroid, room, 'prev_scenes', {'scenes': []})
    if scene_info['name'] not in previous_scenes['scenes']:
        intro = scene_info['intro_text']
        if isinstance(intro, dict):
            await message.respond(intro['players'], room=roomname)
            await message.respond(intro['dm'], room='main')
        else:
            await message.respond(intro, room=roomname)

        if 'characters' in scene_info.keys():
            # Load all the characters
            chars = await load_from_memory(opsdroid, room, 'chars')
            for charname, info in scene_info['characters'].items():
                nchars = info['number'] if 'number' in info.keys() else 1
                name = charname+'_' if nchars > 1 else charname
                chardir = 'characters'
                if opsdroid.config.get('module-path', None):
                    chardir = join(opsdroid.config['module-path'], chardir)
                loadfile = join(chardir, info['loadfile'])
                for i in range(nchars):
                    with open(loadfile) as f:
                        charstats = yaml.safe_load(f)
                    if nchars > 1:
                        name = name[:-1]+str(i+1)
                    charstats['name'] = name
                    chars[name] = charstats
            await update_memory(opsdroid, room, 'chars', chars)

    # Store the defined info for the DM in the DM room
    dm_info = scene_info['dm_info']
    if 'loadfile' in dm_info.keys():
        loadfile = join(folder, dm_info.pop('loadfile'))
        with open(loadfile) as f:
            loaded = yaml.safe_load(f)
        dm_info.update(loaded['dm_info'])
    # DM will likely be dealing with several scenes across adventures, so they'll need to be stored
    # per-room
    dm_scenes.update({roomname: dm_info})
    await save_new_to_memory(opsdroid, 'main', 'scenes', dm_scenes)
    previous_scenes['scenes'].append(scene_info['name'])
    await update_memory(opsdroid, room, 'prev_scenes', previous_scenes)

    # Reporting is useful
    name = scene_info['name']
    features = '\t\t'.join(dm_info.keys())
    await message.respond(f"Moved to scene '{name}'\nFeatures of this scene:\n{features}",
                          room='main')


@match_regex(f"!info (?P<group>\w+)( (?P<key>\D+))?")
async def get_info(opsdroid, config, message):
    match = message.regex.group
    room = match('group')
    key = match('key')
    info = await load_from_memory(opsdroid, 'main', 'scenes')
    info = info[room]

    if key:
        keys = key.split('/')
        for key in keys:
            info = info[key]
    if isinstance(info, dict):
        info = '\t'.join(info.keys())
    elif isinstance(info, list):
        info = info[0]
        await message.respond(f"{info['name']}")
        info = info['info']
    await message.respond(f"{info}")
