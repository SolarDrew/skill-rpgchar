"""
Definitions of regexes for matching common useful sentence parts.
"""

# Regex definitions
OBJECT = '(?P<obname>.*)' # in grammatical sense - person who is acting
SUBJECT = '(?P<subname>.*)' # acted upon
ATK_VERB = '(hits?|attacks?|swings? at)'
WEAPON = '(?P<weapon>.*)'
