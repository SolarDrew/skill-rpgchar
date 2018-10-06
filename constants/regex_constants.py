"""
Definitions of regexes for matching common useful sentence parts.
"""

# Regex definitions
OBJECT = '(?P<object>\w+)' # in grammatical sense - person who is acting
SUBJECT = '(?P<subject>\w+)' # acted upon
POSSESSIVE = '(a|my|his|her|their)'

ATK_VERB = '(hits?|attacks?|swings? at|shoots?)'
WEAPON = '(?P<weapon>\w+)'

SPL_VERB = '(casts?)'
HEAL_SPELL = '(false_life)'
ATK_SPELL = '(firebolt|ray_of_frost|magic_missile)'

GAIN_VERB = '(gets?|gains?)'
