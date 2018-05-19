"""
Definitions of regexes for matching common useful sentence parts.
"""

# Regex definitions
OBJECT = '(?P<object>\w+)' # in grammatical sense - person who is acting
SUBJECT = '(?P<subject>\w+)' # acted upon
POSSESSIVE = '(a|my|his|her|their)'

ATK_VERB = '(hits?|attacks?|swings? at|shoots?)'
WEAPON = '(?P<weapon>\w+)'

GAIN_VERB = '(gets?|gains?)'
