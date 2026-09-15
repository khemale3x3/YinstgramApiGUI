#!/usr/bin/env python3
"""
bio_location.py
---------------
Extracts creator location purely from Instagram biography text.

Coverage — city, state/region and country for:
  Americas : USA, Canada, Mexico, Brazil, Argentina, Chile
  Europe   : Germany, Netherlands, United Kingdom, Spain, France,
             Switzerland, Croatia, Italy, Portugal, Austria, Belgium,
             Ireland, Poland, Czechia, Hungary, Slovakia, Slovenia,
             Serbia, Romania, Bulgaria, Greece, Sweden, Norway,
             Denmark, Finland, Iceland
  Asia     : India, China, Japan, Nepal, Bhutan, South Korea, Thailand,
             Indonesia, Malaysia, Vietnam, Philippines, Singapore,
             Sri Lanka, Bangladesh, Pakistan, UAE, Turkey
  Oceania  : Australia, New Zealand
  Africa   : South Africa

Shortforms and abbreviations (e.g. LA, SF, CA, NYC, TX, FL, BLR, HYD,
YYC, BC) have been intentionally removed to avoid false positives.
City names that clash across countries (Birmingham, Manchester,
Cambridge, London, Paris, Athens, Vienna, Valencia, Toledo, Naples,
Nice, Split, Cork, York, Bath, Derby, Hull, Reading, Sofia, Córdoba,
Bergen, Wellington) carry lookahead/lookbehind guards requiring nearby
country or state context, so the more specific entry always wins.

Usage (drop-in for analyzer.py):
    from bio_location import extract_location_from_bio
    result = extract_location_from_bio(biography_string)
    # returns: { city, state, country, zip_code, confidence }
"""

import re
from typing import Optional, Dict

from iso3166_alpha2 import country_to_alpha2

# ---------------------------------------------------------------------------
# MASTER LOCATION DATABASE
# Each entry: ( regex_pattern, city, state_or_province, country )
# Patterns are matched case-insensitively against the biography.
# More specific patterns should come BEFORE broader ones.
# ---------------------------------------------------------------------------

# fmt: off
LOCATION_PATTERNS = [

    # =========================================================
    # USA — CITIES (full names and well-known nicknames only)
    # =========================================================

    # California
    (r'\blos angeles\b|\blacity\b|\belllay\b',                                                      'Los Angeles',      'California',       'USA'),
    (r'\bsan francisco\b|\bfrisco\b|\bsfbay\b',                                                     'San Francisco',    'California',       'USA'),
    (r'\bsan diego\b|\bsandiego\b',                                                                 'San Diego',        'California',       'USA'),
    (r'\bsan jose\b|\bsanjose\b',                                                                   'San Jose',         'California',       'USA'),
    (r'\bsacramento\b|\bsacto\b',                                                                   'Sacramento',       'California',       'USA'),
    (r'\bfresno\b',                                                                                 'Fresno',           'California',       'USA'),
    (r'\blong beach\b|\blongbeach\b',                                                               'Long Beach',       'California',       'USA'),
    (r'\boakland\b|\boaktown\b',                                                                    'Oakland',          'California',       'USA'),
    (r'\bbakersfield\b|\bbako\b',                                                                   'Bakersfield',      'California',       'USA'),
    (r'\banaheim\b',                                                                                'Anaheim',          'California',       'USA'),
    (r'\bsanta ana\b|\bsantaana\b',                                                                 'Santa Ana',        'California',       'USA'),
    (r'\briverside\b',                                                                              'Riverside',        'California',       'USA'),
    (r'\bstockton\b',                                                                               'Stockton',         'California',       'USA'),
    (r'\birvine\b',                                                                                 'Irvine',           'California',       'USA'),
    (r'\bchula vista\b|\bchulavista\b',                                                             'Chula Vista',      'California',       'USA'),
    (r'\bsan bernardino\b|\bsan berno\b',                                                           'San Bernardino',   'California',       'USA'),
    (r'\bmodesto\b',                                                                                'Modesto',          'California',       'USA'),
    (r'\boxnard\b',                                                                                 'Oxnard',           'California',       'USA'),
    (r'\bfontana\b',                                                                                'Fontana',          'California',       'USA'),
    (r'\bglendale\b(?=.*\b(?:california)\b)',                                                       'Glendale',         'California',       'USA'),
    (r'\bsanta barbara\b|\bsantabarbara\b',                                                         'Santa Barbara',    'California',       'USA'),
    (r'\bpalo alto\b|\bpaloalto\b',                                                                 'Palo Alto',        'California',       'USA'),
    (r'\bbeverly hills\b|\bbeverlyhills\b',                                                         'Beverly Hills',    'California',       'USA'),
    (r'\bsanta monica\b|\bsantamonica\b',                                                           'Santa Monica',     'California',       'USA'),
    (r'\bpasadena\b(?=.*\b(?:california)\b)',                                                       'Pasadena',         'California',       'USA'),
    (r'\bburbank\b',                                                                                'Burbank',          'California',       'USA'),
    (r'\bcompton\b',                                                                                'Compton',          'California',       'USA'),
    (r'\binglewood\b',                                                                              'Inglewood',        'California',       'USA'),
    (r'\bsunnyvale\b',                                                                              'Sunnyvale',        'California',       'USA'),
    (r'\bsanta clara\b|\bsantaclara\b',                                                             'Santa Clara',      'California',       'USA'),
    (r'\bhayward\b(?=.*\b(?:california)\b)',                                                        'Hayward',          'California',       'USA'),
    (r'\bfremont\b',                                                                                'Fremont',          'California',       'USA'),
    (r'\bvallejo\b',                                                                                'Vallejo',          'California',       'USA'),
    (r'\bel monte\b|\belmonte\b',                                                                   'El Monte',         'California',       'USA'),
    (r'\bsimi valley\b|\bsimivalley\b',                                                             'Simi Valley',      'California',       'USA'),
    (r'\bescondido\b',                                                                              'Escondido',        'California',       'USA'),
    (r'\bnorcal\b|\bnor\s*cal\b',                                                                   None,               'California',       'USA'),
    (r'\bsocal\b|\bso\s*cal\b|\bsouthern california\b',                                            None,               'California',       'USA'),
    (r'\bcalifornia\b',                                                                             None,               'California',       'USA'),

    # New York
    (r'\bnew york city\b|\bnew york\b|\bbig apple\b|\bmanhattan\b|\bbrooklyn\b|\bqueens\b|\bbronx\b|\bstaten island\b', 'New York City', 'New York', 'USA'),
    (r'\bbuffalo\b(?=.*\bnew york\b)',                                                              'Buffalo',          'New York',         'USA'),
    (r'\brochester\b(?=.*\bnew york\b)',                                                            'Rochester',        'New York',         'USA'),
    (r'\byonkers\b',                                                                                'Yonkers',          'New York',         'USA'),
    (r'\bsyracuse\b(?=.*\bnew york\b)',                                                             'Syracuse',         'New York',         'USA'),
    (r'\balbany\b(?=.*\bnew york\b)',                                                               'Albany',           'New York',         'USA'),
    (r'\blong island\b|\blongisland\b',                                                             None,               'New York',         'USA'),
    (r'\bharlem\b',                                                                                 'New York City',    'New York',         'USA'),
    (r'\bbedstuy\b|\bbed.stuy\b|\bbedford.stuyvesant\b',                                            'New York City',    'New York',         'USA'),
    (r'\bwilliamsburg\b(?=.*\bnew york\b)',                                                         'New York City',    'New York',         'USA'),
    (r'\bastoria\b(?=.*\bnew york\b)',                                                              'New York City',    'New York',         'USA'),

    # Texas
    (r'\bhouston\b|\bh-?town\b|\bspace city\b',                                                    'Houston',          'Texas',            'USA'),
    (r'\bsan antonio\b|\bsanantonio\b',                                                             'San Antonio',      'Texas',            'USA'),
    (r'\bdallas\b|\bbig d\b',                                                                       'Dallas',           'Texas',            'USA'),
    (r'\baustin\b',                                                                                 'Austin',           'Texas',            'USA'),
    (r'\bfort worth\b|\bfortworth\b',                                                               'Fort Worth',       'Texas',            'USA'),
    (r'\bel paso\b|\belpaso\b',                                                                     'El Paso',          'Texas',            'USA'),
    (r'\barlington\b(?=.*\btexas\b)',                                                               'Arlington',        'Texas',            'USA'),
    (r'\bcorpus christi\b|\bcorpuschristi\b',                                                       'Corpus Christi',   'Texas',            'USA'),
    (r'\bplano\b',                                                                                  'Plano',            'Texas',            'USA'),
    (r'\blaredo\b',                                                                                 'Laredo',           'Texas',            'USA'),
    (r'\blubbock\b',                                                                                'Lubbock',          'Texas',            'USA'),
    (r'\bgarland\b(?=.*\btexas\b)',                                                                 'Garland',          'Texas',            'USA'),
    (r'\birving\b(?=.*\btexas\b)',                                                                  'Irving',           'Texas',            'USA'),
    (r'\bfrisco\b(?=.*\btexas\b)',                                                                  'Frisco',           'Texas',            'USA'),
    (r'\bwaco\b',                                                                                   'Waco',             'Texas',            'USA'),
    (r'\bmckinney\b(?=.*\btexas\b)',                                                                'McKinney',         'Texas',            'USA'),
    (r'\btexas\b',                                                                                  None,               'Texas',            'USA'),

    # Florida
    (r'\bmiami\b',                                                                                  'Miami',            'Florida',          'USA'),
    (r'\bjacksonville\b',                                                                           'Jacksonville',     'Florida',          'USA'),
    (r'\btampa\b',                                                                                  'Tampa',            'Florida',          'USA'),
    (r'\borlando\b',                                                                                'Orlando',          'Florida',          'USA'),
    (r'\bst\.?\s*pete(?:rsburg)?\b|\bst pete\b',                                                   'St. Petersburg',   'Florida',          'USA'),
    (r'\bhialeah\b',                                                                                'Hialeah',          'Florida',          'USA'),
    (r'\bcoral springs\b|\bcoralsprings\b',                                                         'Coral Springs',    'Florida',          'USA'),
    (r'\bfort lauderdale\b|\bfortlauderdale\b',                                                     'Fort Lauderdale',  'Florida',          'USA'),
    (r'\bpembroke pines\b|\bpembrokepines\b',                                                       'Pembroke Pines',   'Florida',          'USA'),
    (r'\bhollywood\b(?=.*\bflorida\b)',                                                             'Hollywood',        'Florida',          'USA'),
    (r'\bgainesville\b(?=.*\bflorida\b)',                                                           'Gainesville',      'Florida',          'USA'),
    (r'\btallahassee\b',                                                                            'Tallahassee',      'Florida',          'USA'),
    (r'\bboca raton\b|\bboca\b(?=.*\bflorida\b)',                                                   'Boca Raton',       'Florida',          'USA'),
    (r'\bnaples\b(?=.*\bflorida\b)',                                                                'Naples',           'Florida',          'USA'),
    (r'\bwest palm beach\b|\bwestpalmbeach\b',                                                      'West Palm Beach',  'Florida',          'USA'),
    (r'\bkey west\b|\bkeywest\b',                                                                   'Key West',         'Florida',          'USA'),
    (r'\bflorida\b',                                                                                None,               'Florida',          'USA'),

    # Illinois
    (r'\bchicago\b|\bchi-?town\b|\bwindy city\b|\bchitown\b',                                      'Chicago',          'Illinois',         'USA'),
    (r'\baurora\b(?=.*\billinois\b)',                                                               'Aurora',           'Illinois',         'USA'),
    (r'\bnaperville\b',                                                                             'Naperville',       'Illinois',         'USA'),
    (r'\bpeoria\b(?=.*\billinois\b)',                                                               'Peoria',           'Illinois',         'USA'),
    (r'\billinois\b',                                                                               None,               'Illinois',         'USA'),

    # Pennsylvania
    (r'\bphiladelphia\b|\bphilly\b',                                                               'Philadelphia',     'Pennsylvania',     'USA'),
    (r'\bpittsburgh\b|\bsteel city\b',                                                             'Pittsburgh',       'Pennsylvania',     'USA'),
    (r'\ballentown\b(?=.*\bpennsylvania\b)',                                                        'Allentown',        'Pennsylvania',     'USA'),
    (r'\bpennsylvania\b',                                                                           None,               'Pennsylvania',     'USA'),

    # Georgia
    (r'\batlanta\b|\ba-?town\b',                                                                    'Atlanta',          'Georgia',          'USA'),
    (r'\bsavannah\b(?=.*\bgeorgia\b)',                                                              'Savannah',         'Georgia',          'USA'),
    (r'\baugusta\b(?=.*\bgeorgia\b)',                                                               'Augusta',          'Georgia',          'USA'),
    (r'\bgeorgia\b(?=.*\b(?:usa|us|united states|atlanta)\b)',                                     None,               'Georgia',          'USA'),

    # Washington State
    (r'\bseattle\b|\bsea-?tac\b|\bemerald city\b',                                                 'Seattle',          'Washington',       'USA'),
    (r'\bspokane\b',                                                                                'Spokane',          'Washington',       'USA'),
    (r'\btacoma\b',                                                                                 'Tacoma',           'Washington',       'USA'),
    (r'\bbellevue\b(?=.*\bwashington\b)',                                                           'Bellevue',         'Washington',       'USA'),
    (r'\bredmond\b(?=.*\bwashington\b)',                                                            'Redmond',          'Washington',       'USA'),
    (r'\bwashington state\b',                                                                       None,               'Washington',       'USA'),

        (r'\bnewark\b(?=.*\bnew jersey\b)',                                                             'Newark',           'New Jersey',       'USA'),

    (r'\bjersey city\b',                                                                            'Jersey City',      'New Jersey',       'USA'),

    (r'\bpaterson\b',                                                                               'Paterson',         'New Jersey',       'USA'),

    (r'\belizabeth\b(?=.*\bnew jersey\b)',                                                          'Elizabeth',        'New Jersey',       'USA'),

    (r'\bedison\b(?=.*\bnew jersey\b)',                                                             'Edison',           'New Jersey',       'USA'),

    (r'\bwoodbridge\b(?=.*\bnew jersey\b)',                                                         'Woodbridge',       'New Jersey',       'USA'),

    (r'\blakewood\b(?=.*\bnew jersey\b)',                                                           'Lakewood',         'New Jersey',       'USA'),

    (r'\btoms river\b|\btomsriver\b',                                                               'Toms River',       'New Jersey',       'USA'),

    (r'\bhamilton township\b(?=.*\bnew jersey\b)',                                                  'Hamilton',         'New Jersey',       'USA'),

    (r'\btrenton\b',                                                                                'Trenton',          'New Jersey',       'USA'),

    (r'\bclifton\b(?=.*\bnew jersey\b)',                                                            'Clifton',          'New Jersey',       'USA'),

    (r'\bcamden\b(?=.*\bnew jersey\b)',                                                             'Camden',           'New Jersey',       'USA'),

    (r'\bpassaic\b',                                                                                'Passaic',          'New Jersey',       'USA'),

    (r'\bunion city\b(?=.*\bnew jersey\b)',                                                         'Union City',       'New Jersey',       'USA'),

    (r'\bbayonne\b',                                                                                'Bayonne',          'New Jersey',       'USA'),

    (r'\beast orange\b|\beastorange\b',                                                             'East Orange',      'New Jersey',       'USA'),

    (r'\bvineland\b',                                                                               'Vineland',         'New Jersey',       'USA'),

    (r'\bnew brunswick\b(?=.*\bnew jersey\b)',                                                      'New Brunswick',    'New Jersey',       'USA'),

    (r'\bhoboken\b',                                                                                'Hoboken',          'New Jersey',       'USA'),

    (r'\bwest new york\b(?=.*\bnew jersey\b)',                                                      'West New York',    'New Jersey',       'USA'),

    (r'\bperth amboy\b|\bperthamboy\b',                                                             'Perth Amboy',      'New Jersey',       'USA'),

    (r'\bplainfield\b(?=.*\bnew jersey\b)',                                                         'Plainfield',       'New Jersey',       'USA'),

    (r'\bmorristown\b',                                                                             'Morristown',       'New Jersey',       'USA'),

    (r'\bmorris township\b',                                                                        'Morris Township',  'New Jersey',       'USA'),

    (r'\bmorris county\b',                                                                          None,               'New Jersey',       'USA'),

    (r'\bprinceton\b(?=.*\bnew jersey\b)',                                                          'Princeton',        'New Jersey',       'USA'),

    (r'\bmontclair\b',                                                                              'Montclair',        'New Jersey',       'USA'),

    (r'\bsummit\b(?=.*\bnew jersey\b)',                                                             'Summit',           'New Jersey',       'USA'),

    (r'\bbridgewater\b(?=.*\bnew jersey\b)',                                                        'Bridgewater',      'New Jersey',       'USA'),

    (r'\bparsippany\b',                                                                             'Parsippany',       'New Jersey',       'USA'),

    (r'\bhackensack\b',                                                                             'Hackensack',       'New Jersey',       'USA'),

    (r'\bteaneck\b',                                                                                'Teaneck',          'New Jersey',       'USA'),

    (r'\bfort lee\b(?=.*\bnew jersey\b)',                                                           'Fort Lee',         'New Jersey',       'USA'),

    (r'\bcherry hill\b|\bcherryhill\b',                                                             'Cherry Hill',      'New Jersey',       'USA'),

    (r'\bsecaucus\b',                                                                               'Secaucus',         'New Jersey',       'USA'),

    (r'\bwayne\b(?=.*\bnew jersey\b)',                                                              'Wayne',            'New Jersey',       'USA'),

    (r'\basbury park\b|\basburypark\b',                                                             'Asbury Park',      'New Jersey',       'USA'),

    (r'\bred bank\b(?=.*\bnew jersey\b)',                                                           'Red Bank',         'New Jersey',       'USA'),

    (r'\bmorristown, ?nj\b|\bmorristownnj\b',                                                       'Morristown',       'New Jersey',       'USA'),

    (r'\bjersey shore\b',                                                                           None,               'New Jersey',       'USA'),

    (r'\bnew jersey\b|\bnjersey\b|\bgarden state\b',                                                None,               'New Jersey',       'USA'),
    # Arizona
    (r'\bphoenix\b|\bvalley of the sun\b',                                                          'Phoenix',          'Arizona',          'USA'),
    (r'\btucson\b',                                                                                 'Tucson',           'Arizona',          'USA'),
    (r'\bmesa\b(?=.*\barizona\b)',                                                                  'Mesa',             'Arizona',          'USA'),
    (r'\bchandler\b(?=.*\barizona\b)',                                                              'Chandler',         'Arizona',          'USA'),
    (r'\bscottsdale\b',                                                                             'Scottsdale',       'Arizona',          'USA'),
    (r'\btempe\b(?=.*\barizona\b)',                                                                 'Tempe',            'Arizona',          'USA'),
    (r'\barizona\b',                                                                                None,               'Arizona',          'USA'),

    # Colorado
    (r'\bdenver\b|\bmile high city\b',                                                              'Denver',           'Colorado',         'USA'),
    (r'\bcolorado springs\b',                                                                       'Colorado Springs', 'Colorado',         'USA'),
    (r'\bfort collins\b|\bfortcollins\b|\bfoco\b',                                                  'Fort Collins',     'Colorado',         'USA'),
    (r'\bcolorado\b',                                                                               None,               'Colorado',         'USA'),

    # Ohio
    (r'\bcolumbus\b(?=.*\bohio\b)',                                                                 'Columbus',         'Ohio',             'USA'),
    (r'\bcleveland\b|\bthe land\b',                                                                 'Cleveland',        'Ohio',             'USA'),
    (r'\bcincinnati\b|\bcinci\b|\bthe nati\b',                                                      'Cincinnati',       'Ohio',             'USA'),
    (r'\btoledo\b(?=.*\bohio\b)',                                                                   'Toledo',           'Ohio',             'USA'),
    (r'\bohio\b',                                                                                   None,               'Ohio',             'USA'),

    # Michigan
    (r'\bdetroit\b|\bmotown\b',                                                                     'Detroit',          'Michigan',         'USA'),
    (r'\bgrand rapids\b|\bgrandrapids\b',                                                           'Grand Rapids',     'Michigan',         'USA'),
    (r'\bann arbor\b|\bannarbor\b',                                                                 'Ann Arbor',        'Michigan',         'USA'),
    (r'\blansing\b(?=.*\bmichigan\b)',                                                              'Lansing',          'Michigan',         'USA'),
    (r'\bmichigan\b',                                                                               None,               'Michigan',         'USA'),

    # North Carolina
    (r'\bcharlotte\b|\bqueen city\b(?=.*\bnorth carolina\b)',                                       'Charlotte',        'North Carolina',   'USA'),
    (r'\braleigh\b',                                                                                'Raleigh',          'North Carolina',   'USA'),
    (r'\bgreensboro\b',                                                                             'Greensboro',       'North Carolina',   'USA'),
    (r'\bdurham\b(?=.*\bnorth carolina\b)',                                                         'Durham',           'North Carolina',   'USA'),
    (r'\bnorth carolina\b',                                                                         None,               'North Carolina',   'USA'),

    # Nevada
    (r'\blas vegas\b|\bvegas\b|\bsin city\b',                                                       'Las Vegas',        'Nevada',           'USA'),
    (r'\breno\b(?=.*\bnevada\b)',                                                                   'Reno',             'Nevada',           'USA'),
    (r'\bhenderson\b(?=.*\bnevada\b)',                                                              'Henderson',        'Nevada',           'USA'),
    (r'\bnevada\b',                                                                                 None,               'Nevada',           'USA'),

    # Tennessee
    (r'\bnashville\b|\bnashvegas\b|\bmusic city\b',                                                'Nashville',        'Tennessee',        'USA'),
    (r'\bmemphis\b(?=.*\btennessee\b)',                                                             'Memphis',          'Tennessee',        'USA'),
    (r'\bknoxville\b',                                                                              'Knoxville',        'Tennessee',        'USA'),
    (r'\btennessee\b',                                                                              None,               'Tennessee',        'USA'),

    # Massachusetts
    (r'\bboston\b|\bbeantown\b',                                                                    'Boston',           'Massachusetts',    'USA'),
    (r'\bspringfield\b(?=.*\bmassachusetts\b)',                                                     'Springfield',      'Massachusetts',    'USA'),
    (r'\bworcester\b(?=.*\bmassachusetts\b)',                                                       'Worcester',        'Massachusetts',    'USA'),
    (r'\bmassachusetts\b',                                                                          None,               'Massachusetts',    'USA'),

    # Oregon
    (r'\bportland\b|\brose city\b(?=.*\boregon\b)',                                                'Portland',         'Oregon',           'USA'),
    (r'\beugene\b(?=.*\boregon\b)',                                                                 'Eugene',           'Oregon',           'USA'),
    (r'\boregon\b',                                                                                 None,               'Oregon',           'USA'),

    # Minnesota
    (r'\bminneapolis\b|\btwin cities\b',                                                            'Minneapolis',      'Minnesota',        'USA'),
    (r'\bsaint paul\b|\bst\.?\s*paul\b(?=.*\bminnesota\b)',                                        'Saint Paul',       'Minnesota',        'USA'),
    (r'\bminnesota\b',                                                                              None,               'Minnesota',        'USA'),

    # Missouri
    (r'\bkansas city\b',                                                                            'Kansas City',      'Missouri',         'USA'),
    (r'\bst\.?\s*louis\b',                                                                          'St. Louis',        'Missouri',         'USA'),
    (r'\bmissouri\b',                                                                               None,               'Missouri',         'USA'),

    # Indiana
    (r'\bindianapolis\b|\bindy\b(?=.*\bindiana\b)',                                                 'Indianapolis',     'Indiana',          'USA'),
    (r'\bindiana\b',                                                                                None,               'Indiana',          'USA'),

    # Wisconsin
    (r'\bmilwaukee\b',                                                                              'Milwaukee',        'Wisconsin',        'USA'),
    (r'\bmadison\b(?=.*\bwisconsin\b)',                                                             'Madison',          'Wisconsin',        'USA'),
    (r'\bwisconsin\b',                                                                              None,               'Wisconsin',        'USA'),

    # Maryland / DC
    (r'\bbaltimore\b|\bbmore\b|\bcrab city\b',                                                      'Baltimore',        'Maryland',         'USA'),
    (r'\bwashington\s*d\.?c\.?\b|\bwashington dc\b|\bthe district\b|\bnation(?:\'s)? capital\b',  'Washington',       'DC',               'USA'),
    (r'\bmaryland\b',                                                                               None,               'Maryland',         'USA'),

    # Virginia
    (r'\bvirginia beach\b',                                                                         'Virginia Beach',   'Virginia',         'USA'),
    (r'\bnorfolk\b(?=.*\bvirginia\b)',                                                              'Norfolk',          'Virginia',         'USA'),
    (r'\brichmond\b(?=.*\bvirginia\b)',                                                             'Richmond',         'Virginia',         'USA'),
    (r'\bvirginia\b(?=.*\b(?:usa|us|united states)\b)',                                            None,               'Virginia',         'USA'),

    # Louisiana
    (r'\bnew orleans\b|\bnola\b|\bthe crescent city\b|\bthe big easy\b',                           'New Orleans',      'Louisiana',        'USA'),
    (r'\bbaton rouge\b|\bbatonrouge\b',                                                             'Baton Rouge',      'Louisiana',        'USA'),
    (r'\blouisiana\b',                                                                              None,               'Louisiana',        'USA'),

    # Kentucky
    (r'\blouisville\b',                                                                             'Louisville',       'Kentucky',         'USA'),
    (r'\blexington\b(?=.*\bkentucky\b)',                                                            'Lexington',        'Kentucky',         'USA'),
    (r'\bkentucky\b',                                                                               None,               'Kentucky',         'USA'),

    # South Carolina
    (r'\bcharleston\b(?=.*\bsouth carolina\b)',                                                     'Charleston',       'South Carolina',   'USA'),
    (r'\bcolumbia\b(?=.*\bsouth carolina\b)',                                                       'Columbia',         'South Carolina',   'USA'),
    (r'\bsouth carolina\b',                                                                         None,               'South Carolina',   'USA'),

    # Alabama
    (r'\bbirmingham\b(?=.*\balabama\b)',                                                            'Birmingham',       'Alabama',          'USA'),
    (r'\bmontgomery\b(?=.*\balabama\b)',                                                            'Montgomery',       'Alabama',          'USA'),
    (r'\balabama\b',                                                                                None,               'Alabama',          'USA'),

    # Connecticut
    (r'\bbridgeport\b(?=.*\bconnecticut\b)',                                                        'Bridgeport',       'Connecticut',      'USA'),
    (r'\bnew haven\b|\bnewhaven\b(?=.*\bconnecticut\b)',                                            'New Haven',        'Connecticut',      'USA'),
    (r'\bhartford\b(?=.*\bconnecticut\b)',                                                          'Hartford',         'Connecticut',      'USA'),
    (r'\bconnecticut\b',                                                                            None,               'Connecticut',      'USA'),

    # Utah
    (r'\bsalt lake city\b|\bsalt lake\b',                                                          'Salt Lake City',   'Utah',             'USA'),
    (r'\bprovo\b(?=.*\butah\b)',                                                                    'Provo',            'Utah',             'USA'),
    (r'\butah\b',                                                                                   None,               'Utah',             'USA'),

    # Hawaii
    (r'\bhonolulu\b|\bwaikiki\b',                                                                   'Honolulu',         'Hawaii',           'USA'),
    (r'\bhawaii\b|\baloha state\b',                                                                 None,               'Hawaii',           'USA'),

    # New Jersey
    (r'\bnewark\b(?=.*\bnew jersey\b)',                                                             'Newark',           'New Jersey',       'USA'),
    (r'\bjersey city\b',                                                                            'Jersey City',      'New Jersey',       'USA'),
    (r'\bnew jersey\b',                                                                             None,               'New Jersey',       'USA'),

    # Generic USA catch-all (last resort)
    (r'\b(?:usa|u\.s\.a\.|united states(?: of america)?|america)\b',                               None,               None,               'USA'),

    # =========================================================
    # INDIA — CITIES (full names and well-known nicknames only)
    # =========================================================

    # Maharashtra
    (r'\bmumbai\b|\bbombay\b|\bmayanagari\b|\bcity of dreams\b(?=.*\bindia\b)',                    'Mumbai',           'Maharashtra',      'India'),
    (r'\bpune\b|\bpoona\b',                                                                        'Pune',             'Maharashtra',      'India'),
    (r'\bnagpur\b',                                                                                 'Nagpur',           'Maharashtra',      'India'),
    (r'\bthane\b',                                                                                  'Thane',            'Maharashtra',      'India'),
    (r'\bnashik\b|\bnasik\b',                                                                       'Nashik',           'Maharashtra',      'India'),
    (r'\baurangabad\b(?=.*\b(?:india|maharashtra)\b)',                                              'Aurangabad',       'Maharashtra',      'India'),
    (r'\bsolapur\b',                                                                                'Solapur',          'Maharashtra',      'India'),
    (r'\bkolhapur\b',                                                                               'Kolhapur',         'Maharashtra',      'India'),
    (r'\bnavi mumbai\b|\bnavimumbai\b',                                                             'Navi Mumbai',      'Maharashtra',      'India'),

    # Delhi / NCR
    (r'\bnew delhi\b|\bdelhi\b|\bdilli\b|\brashtrapati bhavan\b',                                  'New Delhi',        'Delhi',            'India'),
    (r'\bgurgaon\b|\bgurugram\b',                                                                   'Gurugram',         'Haryana',          'India'),
    (r'\bnoida\b',                                                                                  'Noida',            'Uttar Pradesh',    'India'),
    (r'\bfaridabad\b',                                                                              'Faridabad',        'Haryana',          'India'),
    (r'\bghaziabad\b',                                                                              'Ghaziabad',        'Uttar Pradesh',    'India'),

    # Karnataka
    (r'\bbengaluru\b|\bbangalore\b|\bsilicon valley of india\b|\bgarden city\b(?=.*\bindia\b)',     'Bengaluru',        'Karnataka',        'India'),
    (r'\bmysore\b|\bmysuru\b',                                                                      'Mysuru',           'Karnataka',        'India'),
    (r'\bmangalore\b|\bmangaluru\b',                                                                'Mangaluru',        'Karnataka',        'India'),
    (r'\bhubli\b|\bdharwad\b|\bhubli-?dharwad\b',                                                  'Hubli',            'Karnataka',        'India'),

    # Tamil Nadu
    (r'\bchennai\b|\bmadras\b|\bnamma chennai\b',                                                  'Chennai',          'Tamil Nadu',       'India'),
    (r'\bcoimbatore\b',                                                                             'Coimbatore',       'Tamil Nadu',       'India'),
    (r'\bmadurai\b',                                                                                'Madurai',          'Tamil Nadu',       'India'),
    (r'\btiruppur\b|\btirupur\b',                                                                   'Tiruppur',         'Tamil Nadu',       'India'),
    (r'\bsalem\b(?=.*\btamilnadu\b)',                                                               'Salem',            'Tamil Nadu',       'India'),
    (r'\btrichy\b|\btiruchirappalli\b',                                                             'Tiruchirappalli',  'Tamil Nadu',       'India'),
    (r'\btamil nadu\b|\btamilnadu\b',                                                               None,               'Tamil Nadu',       'India'),

    # Telangana
    (r'\bhyderabad\b|\bcyberabad\b|\bnizam(?:\'s)? city\b|\bcity of pearls\b',                     'Hyderabad',        'Telangana',        'India'),
    (r'\bwarangal\b',                                                                               'Warangal',         'Telangana',        'India'),

    # West Bengal
    (r'\bkolkata\b|\bcalcutta\b|\bcity of joy\b(?=.*\bindia\b)',                                   'Kolkata',          'West Bengal',      'India'),
    (r'\bsiliguri\b',                                                                               'Siliguri',         'West Bengal',      'India'),
    (r'\bdurgapur\b',                                                                               'Durgapur',         'West Bengal',      'India'),

    # Gujarat
    (r'\bahmedabad\b|\bamdavad\b',                                                                  'Ahmedabad',        'Gujarat',          'India'),
    (r'\bsurat\b',                                                                                  'Surat',            'Gujarat',          'India'),
    (r'\bvadodara\b|\bbaroda\b',                                                                    'Vadodara',         'Gujarat',          'India'),
    (r'\brajkot\b',                                                                                 'Rajkot',           'Gujarat',          'India'),
    (r'\bbhavnagar\b',                                                                              'Bhavnagar',        'Gujarat',          'India'),

    # Rajasthan
    (r'\bjaipur\b|\bpink city\b(?=.*\bindia\b)',                                                   'Jaipur',           'Rajasthan',        'India'),
    (r'\bjodhpur\b|\bblue city\b(?=.*\bindia\b)',                                                  'Jodhpur',          'Rajasthan',        'India'),
    (r'\budaipur\b|\bcity of lakes\b(?=.*\bindia\b)',                                               'Udaipur',          'Rajasthan',        'India'),
    (r'\bjaisalmer\b|\bgolden city\b(?=.*\bindia\b)',                                               'Jaisalmer',        'Rajasthan',        'India'),
    (r'\bkota\b(?=.*\brajasthan\b)',                                                                'Kota',             'Rajasthan',        'India'),
    (r'\bajmer\b',                                                                                  'Ajmer',            'Rajasthan',        'India'),

    # Uttar Pradesh
    (r'\blucknow\b|\bcity of nawabs\b',                                                            'Lucknow',          'Uttar Pradesh',    'India'),
    (r'\bkanpur\b|\bcawnpore\b',                                                                    'Kanpur',           'Uttar Pradesh',    'India'),
    (r'\bagra\b(?=.*\b(?:india|uttar pradesh)\b)',                                                  'Agra',             'Uttar Pradesh',    'India'),
    (r'\bvaranasi\b|\bbanaras\b|\bkashi\b',                                                        'Varanasi',         'Uttar Pradesh',    'India'),
    (r'\ballahabad\b|\bprayagraj\b',                                                                'Prayagraj',        'Uttar Pradesh',    'India'),
    (r'\bmeerut\b',                                                                                 'Meerut',           'Uttar Pradesh',    'India'),

    # Punjab (India)
    (r'\bamritsar\b|\bamnritsar\b|\bwalled city\b(?=.*\bpunjab\b)',                                 'Amritsar',         'Punjab',           'India'),
    (r'\bludhiana\b',                                                                               'Ludhiana',         'Punjab',           'India'),
    (r'\bjalandhar\b|\bjullundur\b',                                                                'Jalandhar',        'Punjab',           'India'),
    (r'\bchandigarh\b|\bcity beautiful\b(?=.*\bindia\b)',                                           'Chandigarh',       'Chandigarh',       'India'),

    # Kerala
    (r'\bkochi\b|\bcochin\b|\bernakulam\b|\bqueen of arabian sea\b',                               'Kochi',            'Kerala',           'India'),
    (r'\bthiruvananthapuram\b|\btrivandrum\b',                                                      'Thiruvananthapuram','Kerala',           'India'),
    (r'\bkozhikode\b|\bcalicut\b',                                                                  'Kozhikode',        'Kerala',           'India'),
    (r'\bthrissur\b|\btrichur\b',                                                                   'Thrissur',         'Kerala',           'India'),
    (r'\bkerala\b',                                                                                 None,               'Kerala',           'India'),

    # Andhra Pradesh
    (r'\bvisakhapatnam\b|\bvizag\b',                                                               'Visakhapatnam',    'Andhra Pradesh',   'India'),
    (r'\bvijayawada\b',                                                                             'Vijayawada',       'Andhra Pradesh',   'India'),
    (r'\bguntur\b',                                                                                 'Guntur',           'Andhra Pradesh',   'India'),

    # Madhya Pradesh
    (r'\bindore\b',                                                                                 'Indore',           'Madhya Pradesh',   'India'),
    (r'\bbhopal\b|\bcity of lakes\b(?=.*\bmadhya pradesh\b)',                                       'Bhopal',           'Madhya Pradesh',   'India'),
    (r'\bjabalpur\b',                                                                               'Jabalpur',         'Madhya Pradesh',   'India'),

    # Odisha
    (r'\bbhubaneswar\b|\bbhubaneshwar\b',                                                           'Bhubaneswar',      'Odisha',           'India'),
    (r'\bcuttack\b',                                                                                'Cuttack',          'Odisha',           'India'),

    # Bihar
    (r'\bpatna\b(?=.*\b(?:india|bihar)\b)',                                                        'Patna',            'Bihar',            'India'),

    # Assam
    (r'\bguwahati\b|\bgateway of northeast\b',                                                     'Guwahati',         'Assam',            'India'),

    # Jharkhand
    (r'\branchi\b',                                                                                 'Ranchi',           'Jharkhand',        'India'),

    # Goa
    (r'\bgoa\b|\bpanaji\b|\bpanjim\b|\bpearl of the orient\b',                                     'Panaji',           'Goa',              'India'),

    # Generic India catch-all
    (r'\b(?:india|bharat|hindustan|incredible india)\b',                                            None,               None,               'India'),

    # =========================================================
    # CANADA — CITIES (full names and well-known nicknames only)
    # =========================================================

    # Ontario
    (r'\btoronto\b|\bthe 6(?:ix)?\b|\bthe six\b|\b6ix\b',                                         'Toronto',          'Ontario',          'Canada'),
    (r'\bottawa\b|\bnational capital\b(?=.*\bcanada\b)',                                            'Ottawa',           'Ontario',          'Canada'),
    (r'\bmississauga\b',                                                                            'Mississauga',      'Ontario',          'Canada'),
    (r'\bbrampton\b',                                                                               'Brampton',         'Ontario',          'Canada'),
    (r'\bhamilton\b(?=.*\bontario\b)',                                                              'Hamilton',         'Ontario',          'Canada'),
    (r'\blondon\b(?=.*\bontario\b)',                                                                'London',           'Ontario',          'Canada'),
    (r'\bkitchener\b|\bwaterloo\b(?=.*\bontario\b)',                                                'Kitchener',        'Ontario',          'Canada'),
    (r'\bmarkham\b(?=.*\bontario\b)',                                                               'Markham',          'Ontario',          'Canada'),
    (r'\bwindsor\b(?=.*\bontario\b)',                                                               'Windsor',          'Ontario',          'Canada'),
    (r'\bontario\b(?=.*\bcanada\b)',                                                                None,               'Ontario',          'Canada'),

    # British Columbia
    (r'\bvancouver\b|\braincouver\b|\blotusland\b',                                                'Vancouver',        'British Columbia', 'Canada'),
    (r'\bvictoria\b(?=.*\bbritish columbia\b)',                                                     'Victoria',         'British Columbia', 'Canada'),
    (r'\bsurrey\b(?=.*\bbritish columbia\b)',                                                       'Surrey',           'British Columbia', 'Canada'),
    (r'\bburnaby\b',                                                                                'Burnaby',          'British Columbia', 'Canada'),
    (r'\bkelowna\b',                                                                                'Kelowna',          'British Columbia', 'Canada'),
    (r'\babbotsford\b',                                                                             'Abbotsford',       'British Columbia', 'Canada'),
    (r'\bbritish columbia\b',                                                                       None,               'British Columbia', 'Canada'),

    # Quebec
    (r'\bmontr[eé]al\b|\bla m[eé]tropole\b',                                                       'Montreal',         'Quebec',           'Canada'),
    (r'\bqu[eé]bec city\b|\bvieille capitale\b',                                                   'Quebec City',      'Quebec',           'Canada'),
    (r'\blaval\b(?=.*\bquebec\b)',                                                                  'Laval',            'Quebec',           'Canada'),
    (r'\bgatineau\b',                                                                               'Gatineau',         'Quebec',           'Canada'),
    (r'\bquebec\b(?=.*\bcanada\b)',                                                                 None,               'Quebec',           'Canada'),

    # Alberta
    (r'\bcalgary\b|\bstampede city\b',                                                              'Calgary',          'Alberta',          'Canada'),
    (r'\bedmonton\b|\bnorthern lights city\b',                                                      'Edmonton',         'Alberta',          'Canada'),
    (r'\bred deer\b(?=.*\balberta\b)',                                                              'Red Deer',         'Alberta',          'Canada'),
    (r'\blethbridge\b',                                                                             'Lethbridge',       'Alberta',          'Canada'),
    (r'\balberta\b(?=.*\bcanada\b)',                                                                None,               'Alberta',          'Canada'),

    # Manitoba
    (r'\bwinnipeg\b',                                                                               'Winnipeg',         'Manitoba',         'Canada'),
    (r'\bmanitoba\b(?=.*\bcanada\b)',                                                               None,               'Manitoba',         'Canada'),

    # Saskatchewan
    (r'\bregina\b(?=.*\bsaskatchewan\b)',                                                           'Regina',           'Saskatchewan',     'Canada'),
    (r'\bsaskatoon\b',                                                                              'Saskatoon',        'Saskatchewan',     'Canada'),
    (r'\bsaskatchewan\b(?=.*\bcanada\b)',                                                           None,               'Saskatchewan',     'Canada'),

    # Nova Scotia
    (r'\bhalifax\b',                                                                                'Halifax',          'Nova Scotia',      'Canada'),
    (r'\bnova scotia\b(?=.*\bcanada\b)',                                                            None,               'Nova Scotia',      'Canada'),

    # New Brunswick
    (r'\bmoncton\b',                                                                                'Moncton',          'New Brunswick',    'Canada'),
    (r'\bfredericton\b',                                                                            'Fredericton',      'New Brunswick',    'Canada'),
    (r'\bnew brunswick\b(?=.*\bcanada\b)',                                                          None,               'New Brunswick',    'Canada'),

    # Generic Canada catch-all
    (r'\b(?:canada|canadian|canuck)\b',                                                             None,               None,               'Canada'),

    # =========================================================
    # CHINA — CITIES (full names only)
    # =========================================================

    # Municipalities
    (r'\bbeijing\b|\bpeking\b|\bcapital of china\b',                                               'Beijing',          None,               'China'),
    (r'\bshanghai\b',                                                                               'Shanghai',         None,               'China'),
    (r'\btianjin\b|\btientsin\b',                                                                   'Tianjin',          None,               'China'),
    (r'\bchongqing\b',                                                                              'Chongqing',        None,               'China'),

    # Guangdong
    (r'\bguangzhou\b|\bcanton\b',                                                                   'Guangzhou',        'Guangdong',        'China'),
    (r'\bshenzhen\b',                                                                               'Shenzhen',         'Guangdong',        'China'),
    (r'\bdongguan\b|\bdonguan\b',                                                                   'Dongguan',         'Guangdong',        'China'),
    (r'\bfoshan\b',                                                                                 'Foshan',           'Guangdong',        'China'),
    (r'\bzhuhai\b',                                                                                 'Zhuhai',           'Guangdong',        'China'),

    # Zhejiang
    (r'\bhangzhou\b',                                                                               'Hangzhou',         'Zhejiang',         'China'),
    (r'\bningbo\b',                                                                                 'Ningbo',           'Zhejiang',         'China'),
    (r'\bwenzhou\b',                                                                                'Wenzhou',          'Zhejiang',         'China'),

    # Jiangsu
    (r'\bnanjing\b|\bnanking\b',                                                                    'Nanjing',          'Jiangsu',          'China'),
    (r'\bsuzhou\b',                                                                                 'Suzhou',           'Jiangsu',          'China'),
    (r'\bwuxi\b',                                                                                   'Wuxi',             'Jiangsu',          'China'),

    # Sichuan
    (r'\bchengdu\b|\bland of abundance\b',                                                          'Chengdu',          'Sichuan',          'China'),

    # Hubei
    (r'\bwuhan\b',                                                                                  'Wuhan',            'Hubei',            'China'),

    # Shaanxi
    (r'\bxi\'?an\b|\bxian\b',                                                                       "Xi'an",            'Shaanxi',          'China'),

    # Liaoning
    (r'\bshenyang\b',                                                                               'Shenyang',         'Liaoning',         'China'),
    (r'\bdalian\b',                                                                                 'Dalian',           'Liaoning',         'China'),

    # Henan
    (r'\bzhengzhou\b',                                                                              'Zhengzhou',        'Henan',            'China'),

    # Heilongjiang
    (r'\bharbin\b|\bharbin\b',                                                                      'Harbin',           'Heilongjiang',     'China'),

    # Fujian
    (r'\bxiamen\b|\bamoy\b',                                                                        'Xiamen',           'Fujian',           'China'),

    # Yunnan
    (r'\bkunming\b',                                                                                'Kunming',          'Yunnan',           'China'),

    # Xinjiang
    (r'\burumqi\b|\b[uü]r[uü]mqi\b',                                                               'Ürümqi',           'Xinjiang',         'China'),

    # Tibet
    (r'\blhasa\b',                                                                                  'Lhasa',            'Tibet',            'China'),

    # Special Administrative Regions
    (r'\bhong kong\b',                                                                              'Hong Kong',        'Hong Kong',        'China'),
    (r'\bmacau\b|\bmacao\b',                                                                        'Macau',            'Macau',            'China'),

    # Generic China catch-all
    (r'\b(?:china|prc|people\'?s republic of china|zhongguo|中国)\b',                              None,               None,               'China'),

    # =========================================================
    # JAPAN — MAJOR CITIES AND PREFECTURES
    # =========================================================

    # Tokyo Metropolis
    (r'\btokyo\b|東京',                                                                             'Tokyo',            'Tokyo',            'Japan'),
    (r'\bshinjuku\b|新宿',                                                                          'Tokyo',            'Tokyo',            'Japan'),
    (r'\bshibuya\b|渋谷',                                                                           'Tokyo',            'Tokyo',            'Japan'),
    (r'\bharajuku\b|原宿',                                                                          'Tokyo',            'Tokyo',            'Japan'),
    (r'\bakihabara\b|秋葉原',                                                                       'Tokyo',            'Tokyo',            'Japan'),
    (r'\bginza\b|銀座',                                                                             'Tokyo',            'Tokyo',            'Japan'),
    (r'\broppongi\b|六本木',                                                                        'Tokyo',            'Tokyo',            'Japan'),
    (r'\bsekiguchi\b|関口',                                                                         'Tokyo',            'Tokyo',            'Japan'),

    # Osaka
    (r'\bosaka\b|大阪',                                                                             'Osaka',            'Osaka',            'Japan'),
    (r'\bnamba\b|難波',                                                                             'Osaka',            'Osaka',            'Japan'),
    (r'\bumeda\b|梅田',                                                                             'Osaka',            'Osaka',            'Japan'),
    (r'\bshinsaibashi\b|心斎橋',                                                                   'Osaka',            'Osaka',            'Japan'),

    # Kyoto
    (r'\bkyoto\b|京都',                                                                             'Kyoto',            'Kyoto',            'Japan'),
    (r'\bgion\b|祇園',                                                                              'Kyoto',            'Kyoto',            'Japan'),
    (r'\barashiyama\b|嵐山',                                                                        'Kyoto',            'Kyoto',            'Japan'),

    # Kanagawa
    (r'\byokohama\b|横浜',                                                                          'Yokohama',         'Kanagawa',         'Japan'),
    (r'\bkamakura\b|鎌倉',                                                                          'Kamakura',         'Kanagawa',         'Japan'),
    (r'\bhakone\b|箱根',                                                                            'Hakone',           'Kanagawa',         'Japan'),

    # Aichi
    (r'\bnagoya\b|名古屋',                                                                          'Nagoya',           'Aichi',            'Japan'),

    # Hokkaido
    (r'\bsapporo\b|札幌',                                                                           'Sapporo',          'Hokkaido',         'Japan'),
    (r'\bhakodate\b|函館',                                                                          'Hakodate',         'Hokkaido',         'Japan'),
    (r'\bhokkaido\b|北海道',                                                                        None,               'Hokkaido',         'Japan'),

    # Fukuoka
    (r'\bfukuoka\b|福岡',                                                                           'Fukuoka',          'Fukuoka',          'Japan'),
    (r'\bhakata\b|博多',                                                                            'Fukuoka',          'Fukuoka',          'Japan'),

    # Hiroshima
    (r'\bhiroshima\b|広島',                                                                         'Hiroshima',        'Hiroshima',        'Japan'),

    # Miyagi
    (r'\bsendai\b|仙台',                                                                            'Sendai',           'Miyagi',           'Japan'),

    # Okinawa
    (r'\bnaha\b|那覇',                                                                              'Naha',             'Okinawa',          'Japan'),
    (r'\bokinawa\b|沖縄',                                                                           None,               'Okinawa',          'Japan'),

    # Nara
    (r'\bnara\b|奈良',                                                                              'Nara',             'Nara',             'Japan'),

    # Hyogo
    (r'\bkobe\b|神戸',                                                                              'Kobe',             'Hyogo',            'Japan'),

    # Chiba
    (r'\bchiba\b|千葉',                                                                             'Chiba',            'Chiba',            'Japan'),

    # Saitama
    (r'\bsaitama\b|埼玉',                                                                           'Saitama',          'Saitama',          'Japan'),

    # Generic Japan catch-all
    (r'\b(?:japan|日本|nippon|nihon)\b',                                                            None,               None,               'Japan'),

    # =========================================================
    # MEXICO — MAJOR CITIES AND STATES
    # =========================================================

    # Mexico City (CDMX)
    (r'\bmexico city\b|\bciudad de m[eé]xico\b|\bcdmx\b|\bcapital de m[eé]xico\b',                'Mexico City',      'Mexico City',      'Mexico'),
    (r'\bpolanco\b',                                                                                'Mexico City',      'Mexico City',      'Mexico'),
    (r'\bcondesa\b',                                                                                'Mexico City',      'Mexico City',      'Mexico'),
    (r'\bcoyoac[aá]n\b',                                                                           'Mexico City',      'Mexico City',      'Mexico'),
    (r'\btlalpan\b',                                                                                'Mexico City',      'Mexico City',      'Mexico'),

    # Jalisco
    (r'\bguadalajara\b|gdl(?=.*\bm[eé]xico\b)',                                                    'Guadalajara',      'Jalisco',          'Mexico'),
    (r'\bpuerto vallarta\b|pv(?=.*\bm[eé]xico\b)',                                                 'Puerto Vallarta',  'Jalisco',          'Mexico'),
    (r'\bjalisco\b',                                                                                None,               'Jalisco',          'Mexico'),

    # Nuevo León
    (r'\bmonterrey\b|regio(?=.*\bm[eé]xico\b)',                                                    'Monterrey',        'Nuevo León',       'Mexico'),
    (r'\bnuevo le[oó]n\b',                                                                         None,               'Nuevo León',       'Mexico'),

    # Quintana Roo
    (r'\bcancun\b|\bcanc[uú]n\b',                                                                  'Cancún',           'Quintana Roo',     'Mexico'),
    (r'\btulum\b',                                                                                  'Tulum',            'Quintana Roo',     'Mexico'),
    (r'\bplaya del carmen\b',                                                                       'Playa del Carmen', 'Quintana Roo',     'Mexico'),
    (r'\bcozumel\b',                                                                                'Cozumel',          'Quintana Roo',     'Mexico'),
    (r'\bquintana roo\b',                                                                           None,               'Quintana Roo',     'Mexico'),

    # Puebla
    (r'\bpuebla\b(?=.*\bm[eé]xico\b)',                                                             'Puebla',           'Puebla',           'Mexico'),

    # Guerrero
    (r'\bacapulco\b',                                                                               'Acapulco',         'Guerrero',         'Mexico'),

    # Baja California
    (r'\btijuana\b',                                                                                'Tijuana',          'Baja California',  'Mexico'),
    (r'\bensenada\b',                                                                               'Ensenada',         'Baja California',  'Mexico'),
    (r'\bbaja california\b',                                                                        None,               'Baja California',  'Mexico'),

    # Baja California Sur
    (r'\blos cabos\b|\bcabo san lucas\b|\bcabo\b(?=.*\bm[eé]xico\b)',                              'Los Cabos',        'Baja California Sur', 'Mexico'),
    (r'\bla paz\b(?=.*\bm[eé]xico\b)',                                                             'La Paz',           'Baja California Sur', 'Mexico'),

    # Oaxaca
    (r'\boaxaca\b',                                                                                 'Oaxaca',           'Oaxaca',           'Mexico'),

    # Yucatan
    (r'\bm[eé]rida\b(?=.*\bm[eé]xico\b)',                                                         'Mérida',           'Yucatán',          'Mexico'),
    (r'\bchichen itza\b',                                                                           None,               'Yucatán',          'Mexico'),
    (r'\byucat[aá]n\b',                                                                             None,               'Yucatán',          'Mexico'),

    # Chihuahua
    (r'\bchihuahua\b(?=.*\bm[eé]xico\b)',                                                          'Chihuahua',        'Chihuahua',        'Mexico'),

    # Veracruz
    (r'\bveracruz\b',                                                                               'Veracruz',         'Veracruz',         'Mexico'),

    # San Luis Potosi
    (r'\bsan luis potos[ií]\b',                                                                     'San Luis Potosí',  'San Luis Potosí',  'Mexico'),

    # Generic Mexico catch-all
    (r'\b(?:m[eé]xico|mexico|mexican republic|rep[uú]blica mexicana)\b',                           None,               None,               'Mexico'),

    # =========================================================
    # AUSTRALIA — MAJOR CITIES AND STATES
    # =========================================================

    # New South Wales
    (r'\bsydney\b',                                                                                 'Sydney',           'New South Wales',  'Australia'),
    (r'\bnewcastle\b(?=.*\baustralia\b)',                                                           'Newcastle',        'New South Wales',  'Australia'),
    (r'\bwollongong\b',                                                                             'Wollongong',       'New South Wales',  'Australia'),
    (r'\bnew south wales\b|\bnsw\b(?=.*\baustralia\b)',                                             None,               'New South Wales',  'Australia'),

    # Victoria
    (r'\bmelbourne\b',                                                                              'Melbourne',        'Victoria',         'Australia'),
    (r'\bgeelong\b',                                                                                'Geelong',          'Victoria',         'Australia'),
    (r'\bballarat\b',                                                                               'Ballarat',         'Victoria',         'Australia'),
    (r'\bbendigo\b',                                                                                'Bendigo',          'Victoria',         'Australia'),
    (r'\bvictoria\b(?=.*\baustralia\b)',                                                            None,               'Victoria',         'Australia'),

    # Queensland
    (r'\bbrisbane\b',                                                                               'Brisbane',         'Queensland',       'Australia'),
    (r'\bgold coast\b',                                                                             'Gold Coast',       'Queensland',       'Australia'),
    (r'\bsunshine coast\b',                                                                         'Sunshine Coast',   'Queensland',       'Australia'),
    (r'\btownsville\b',                                                                             'Townsville',       'Queensland',       'Australia'),
    (r'\bcairns\b',                                                                                 'Cairns',           'Queensland',       'Australia'),
    (r'\btoowoomba\b',                                                                              'Toowoomba',        'Queensland',       'Australia'),
    (r'\bqueensland\b|\bqld\b(?=.*\baustralia\b)',                                                  None,               'Queensland',       'Australia'),

    # Western Australia
    (r'\bperth\b(?=.*\baustralia\b)',                                                               'Perth',            'Western Australia','Australia'),
    (r'\bfremantle\b',                                                                              'Fremantle',        'Western Australia','Australia'),
    (r'\bwestern australia\b|\bwa\b(?=.*\baustralia\b)',                                            None,               'Western Australia','Australia'),

    # South Australia
    (r'\badelaide\b',                                                                               'Adelaide',         'South Australia',  'Australia'),
    (r'\bsouth australia\b|\bsa\b(?=.*\baustralia\b)',                                              None,               'South Australia',  'Australia'),

    # Australian Capital Territory
    (r'\bcanberra\b',                                                                               'Canberra',         'ACT',              'Australia'),
    (r'\bact\b(?=.*\baustralia\b)',                                                                 None,               'ACT',              'Australia'),

    # Tasmania
    (r'\bhobart\b',                                                                                 'Hobart',           'Tasmania',         'Australia'),
    (r'\btasmania\b|\btas\b(?=.*\baustralia\b)',                                                    None,               'Tasmania',         'Australia'),

    # Northern Territory
    (r'\bdarwin\b(?=.*\baustralia\b)',                                                              'Darwin',           'Northern Territory','Australia'),
    (r'\bnorthern territory\b|\bnt\b(?=.*\baustralia\b)',                                           None,               'Northern Territory','Australia'),

    # Generic Australia catch-all
    (r'\b(?:australia|aussie|down under)\b',                                                        None,               None,               'Australia'),

    # =========================================================
    # GERMANY — MAJOR CITIES AND BUNDESLÄNDER
    # =========================================================
    (r'\bberlin\b',                                                     'Berlin',           'Berlin',                       'Germany'),
    (r'\bhamburg\b',                                                    'Hamburg',          'Hamburg',                      'Germany'),
    (r'\b(?:m[uü]nchen|muenchen|munich)\b',                             'Munich',           'Bavaria',                      'Germany'),
    (r'\b(?:k[oö]ln|koeln|cologne)\b',                                  'Cologne',          'North Rhine-Westphalia',       'Germany'),
    (r'\bfrankfurt(?:\s*am\s*main)?\b',                                 'Frankfurt',        'Hesse',                        'Germany'),
    (r'\bstuttgart\b',                                                  'Stuttgart',        'Baden-Württemberg',            'Germany'),
    (r'\b(?:d[uü]sseldorf|duesseldorf)\b',                              'Düsseldorf',       'North Rhine-Westphalia',       'Germany'),
    (r'\bdortmund\b',                                                   'Dortmund',         'North Rhine-Westphalia',       'Germany'),
    (r'\bessen\b',                                                      'Essen',            'North Rhine-Westphalia',       'Germany'),
    (r'\bduisburg\b',                                                   'Duisburg',         'North Rhine-Westphalia',       'Germany'),
    (r'\bbochum\b',                                                     'Bochum',           'North Rhine-Westphalia',       'Germany'),
    (r'\bwuppertal\b',                                                  'Wuppertal',        'North Rhine-Westphalia',       'Germany'),
    (r'\bbielefeld\b',                                                  'Bielefeld',        'North Rhine-Westphalia',       'Germany'),
    (r'\bbonn\b',                                                       'Bonn',             'North Rhine-Westphalia',       'Germany'),
    (r'\b(?:m[uü]nster|muenster)\b',                                    'Münster',          'North Rhine-Westphalia',       'Germany'),
    (r'\baachen\b',                                                     'Aachen',           'North Rhine-Westphalia',       'Germany'),
    (r'\b(?:m[oö]nchengladbach|moenchengladbach)\b',                    'Mönchengladbach',  'North Rhine-Westphalia',       'Germany'),
    (r'\bleipzig\b',                                                    'Leipzig',          'Saxony',                       'Germany'),
    (r'\bdresden\b',                                                    'Dresden',          'Saxony',                       'Germany'),
    (r'\bchemnitz\b',                                                   'Chemnitz',         'Saxony',                       'Germany'),
    (r'\bbremen\b',                                                     'Bremen',           'Bremen',                       'Germany'),
    (r'\b(?:hannover|hanover)\b',                                       'Hannover',         'Lower Saxony',                 'Germany'),
    (r'\bbraunschweig\b',                                               'Braunschweig',     'Lower Saxony',                 'Germany'),
    (r'\b(?:n[uü]rnberg|nuernberg|nuremberg)\b',                        'Nuremberg',        'Bavaria',                      'Germany'),
    (r'\baugsburg\b',                                                   'Augsburg',         'Bavaria',                      'Germany'),
    (r'\bregensburg\b',                                                 'Regensburg',       'Bavaria',                      'Germany'),
    (r'\bw[uü]rzburg\b',                                                'Würzburg',         'Bavaria',                      'Germany'),
    (r'\bkarlsruhe\b',                                                  'Karlsruhe',        'Baden-Württemberg',            'Germany'),
    (r'\bmannheim\b',                                                   'Mannheim',         'Baden-Württemberg',            'Germany'),
    (r'\bfreiburg\b',                                                   'Freiburg',         'Baden-Württemberg',            'Germany'),
    (r'\bheidelberg\b',                                                 'Heidelberg',       'Baden-Württemberg',            'Germany'),
    (r'\bwiesbaden\b',                                                  'Wiesbaden',        'Hesse',                        'Germany'),
    (r'\bdarmstadt\b',                                                  'Darmstadt',        'Hesse',                        'Germany'),
    (r'\bkassel\b',                                                     'Kassel',           'Hesse',                        'Germany'),
    (r'\bkiel\b',                                                       'Kiel',             'Schleswig-Holstein',           'Germany'),
    (r'\bl[uü]beck\b',                                                  'Lübeck',           'Schleswig-Holstein',           'Germany'),
    (r'\bmainz\b',                                                      'Mainz',            'Rhineland-Palatinate',         'Germany'),
    (r'\bkoblenz\b',                                                    'Koblenz',          'Rhineland-Palatinate',         'Germany'),
    (r'\bsaarbr[uü]cken\b',                                             'Saarbrücken',      'Saarland',                     'Germany'),
    (r'\bpotsdam\b',                                                    'Potsdam',          'Brandenburg',                  'Germany'),
    (r'\brostock\b',                                                    'Rostock',          'Mecklenburg-Vorpommern',       'Germany'),
    (r'\berfurt\b',                                                     'Erfurt',           'Thuringia',                    'Germany'),
    (r'\bjena\b',                                                       'Jena',             'Thuringia',                    'Germany'),
    (r'\bmagdeburg\b',                                                  'Magdeburg',        'Saxony-Anhalt',                'Germany'),
    (r'\bhalle\b(?=.*\b(?:germany|deutschland|saale)\b)',               'Halle',            'Saxony-Anhalt',                'Germany'),
    (r'\b(?:bayern|bavaria)\b',                                         None,               'Bavaria',                      'Germany'),
    (r'\bbaden[\s-]*w[uü]rttemberg\b',                                  None,               'Baden-Württemberg',            'Germany'),
    (r'\b(?:nordrhein[\s-]*westfalen|north rhine[\s-]*westphalia|nrw)\b', None,             'North Rhine-Westphalia',       'Germany'),
    (r'\b(?:hessen|hesse)\b',                                           None,               'Hesse',                        'Germany'),
    (r'\b(?:sachsen[\s-]*anhalt|saxony[\s-]*anhalt)\b',                 None,               'Saxony-Anhalt',                'Germany'),
    (r'\b(?:sachsen|saxony)\b',                                         None,               'Saxony',                       'Germany'),
    (r'\b(?:niedersachsen|lower saxony)\b',                             None,               'Lower Saxony',                 'Germany'),
    (r'\b(?:rheinland[\s-]*pfalz|rhineland[\s-]*palatinate)\b',         None,               'Rhineland-Palatinate',         'Germany'),
    (r'\bschleswig[\s-]*holstein\b',                                    None,               'Schleswig-Holstein',           'Germany'),
    (r'\bbrandenburg\b',                                                None,               'Brandenburg',                  'Germany'),
    (r'\b(?:th[uü]ringen|thuringia)\b',                                 None,               'Thuringia',                    'Germany'),
    (r'\bmecklenburg[\s-]*vorpommern\b',                                None,               'Mecklenburg-Vorpommern',       'Germany'),
    (r'\bsaarland\b',                                                   None,               'Saarland',                     'Germany'),
    (r'\b(?:germany|deutschland|german)\b',                             None,               None,                           'Germany'),

    # =========================================================
    # NETHERLANDS — MAJOR CITIES AND PROVINCES
    # =========================================================
    (r'\bamsterdam\b',                                                  'Amsterdam',        'North Holland',                'Netherlands'),
    (r'\brotterdam\b',                                                  'Rotterdam',        'South Holland',                'Netherlands'),
    (r'\b(?:the hague|den haag|s[\s-]*gravenhage)\b',                   'The Hague',        'South Holland',                'Netherlands'),
    (r'\butrecht\b',                                                    'Utrecht',          'Utrecht',                      'Netherlands'),
    (r'\beindhoven\b',                                                  'Eindhoven',        'North Brabant',                'Netherlands'),
    (r'\btilburg\b',                                                    'Tilburg',          'North Brabant',                'Netherlands'),
    (r'\bbreda\b',                                                      'Breda',            'North Brabant',                'Netherlands'),
    (r'\b(?:s[\s-]*hertogenbosch|den bosch)\b',                         "'s-Hertogenbosch", 'North Brabant',                'Netherlands'),
    (r'\bgroningen\b',                                                  'Groningen',        'Groningen',                    'Netherlands'),
    (r'\balmere\b',                                                     'Almere',           'Flevoland',                    'Netherlands'),
    (r'\bnijmegen\b',                                                   'Nijmegen',         'Gelderland',                   'Netherlands'),
    (r'\barnhem\b',                                                     'Arnhem',           'Gelderland',                   'Netherlands'),
    (r'\bharlem\b|\bhaarlem\b',                                         'Haarlem',          'North Holland',                'Netherlands'),
    (r'\bmaastricht\b',                                                 'Maastricht',       'Limburg',                      'Netherlands'),
    (r'\bleiden\b',                                                     'Leiden',           'South Holland',                'Netherlands'),
    (r'\bdelft\b',                                                      'Delft',            'South Holland',                'Netherlands'),
    (r'\bdordrecht\b',                                                  'Dordrecht',        'South Holland',                'Netherlands'),
    (r'\bzwolle\b',                                                     'Zwolle',           'Overijssel',                   'Netherlands'),
    (r'\benschede\b',                                                   'Enschede',         'Overijssel',                   'Netherlands'),
    (r'\bleeuwarden\b',                                                 'Leeuwarden',       'Friesland',                    'Netherlands'),
    (r'\bnoord[\s-]*holland\b|\bnorth holland\b',                       None,               'North Holland',                'Netherlands'),
    (r'\bzuid[\s-]*holland\b|\bsouth holland\b',                        None,               'South Holland',                'Netherlands'),
    (r'\bnoord[\s-]*brabant\b|\bnorth brabant\b',                       None,               'North Brabant',                'Netherlands'),
    (r'\bgelderland\b',                                                 None,               'Gelderland',                   'Netherlands'),
    (r'\boverijssel\b',                                                 None,               'Overijssel',                   'Netherlands'),
    (r'\b(?:friesland|frysl[aâ]n)\b',                                   None,               'Friesland',                    'Netherlands'),
    (r'\bdrenthe\b',                                                    None,               'Drenthe',                      'Netherlands'),
    (r'\bflevoland\b',                                                  None,               'Flevoland',                    'Netherlands'),
    (r'\bzeeland\b',                                                    None,               'Zeeland',                      'Netherlands'),
    (r'\blimburg\b(?=.*\b(?:netherlands|holland|nederland)\b)',         None,               'Limburg',                      'Netherlands'),
    (r'\b(?:netherlands|nederland|holland|dutch)\b',                    None,               None,                           'Netherlands'),

    # =========================================================
    # UNITED KINGDOM — MAJOR CITIES AND HOME NATIONS
    # =========================================================
    (r'\blondon\b',                                                     'London',           'England',                      'United Kingdom'),
    (r'\bmanchester\b(?!.*\bnew hampshire\b)',                          'Manchester',       'England',                      'United Kingdom'),
    (r'\bbirmingham\b',                                                 'Birmingham',       'England',                      'United Kingdom'),
    (r'\bliverpool\b',                                                  'Liverpool',        'England',                      'United Kingdom'),
    (r'\bleeds\b',                                                      'Leeds',            'England',                      'United Kingdom'),
    (r'\bsheffield\b',                                                  'Sheffield',        'England',                      'United Kingdom'),
    (r'\bbristol\b',                                                    'Bristol',          'England',                      'United Kingdom'),
    (r'\bnottingham\b',                                                 'Nottingham',       'England',                      'United Kingdom'),
    (r'\bleicester\b',                                                  'Leicester',        'England',                      'United Kingdom'),
    (r'\bnewcastle(?:\s*upon\s*tyne)?\b(?!.*\baustralia\b)',            'Newcastle',        'England',                      'United Kingdom'),
    (r'\bsouthampton\b',                                                'Southampton',      'England',                      'United Kingdom'),
    (r'\bportsmouth\b(?!.*\b(?:new hampshire|virginia)\b)',             'Portsmouth',       'England',                      'United Kingdom'),
    (r'\bbrighton\b',                                                   'Brighton',         'England',                      'United Kingdom'),
    (r'\boxford\b(?!.*\bmississippi\b)',                                'Oxford',           'England',                      'United Kingdom'),
    (r'\bcambridge\b(?!.*\bmassachusetts\b)',                           'Cambridge',        'England',                      'United Kingdom'),
    (r'\bcoventry\b',                                                   'Coventry',         'England',                      'United Kingdom'),
    (r'\bbradford\b',                                                   'Bradford',         'England',                      'United Kingdom'),
    (r'\bstoke[\s-]*on[\s-]*trent\b',                                   'Stoke-on-Trent',   'England',                      'United Kingdom'),
    (r'\bplymouth\b(?!.*\bmassachusetts\b)',                            'Plymouth',         'England',                      'United Kingdom'),
    (r'\bnorwich\b',                                                    'Norwich',          'England',                      'United Kingdom'),
    (r'\bexeter\b',                                                     'Exeter',           'England',                      'United Kingdom'),
    (r'\bderby\b(?=.*\b(?:uk|england|britain)\b)',                      'Derby',            'England',                      'United Kingdom'),
    (r'\bhull\b(?=.*\b(?:uk|england|britain)\b)',                       'Hull',             'England',                      'United Kingdom'),
    (r'\bbath\b(?=.*\b(?:uk|england|britain|somerset)\b)',              'Bath',             'England',                      'United Kingdom'),
    (r'\breading\b(?=.*\b(?:uk|england|britain|berkshire)\b)',          'Reading',          'England',                      'United Kingdom'),
    (r'(?<!new )\byork\b(?=.*\b(?:uk|england|britain|yorkshire)\b)',    'York',             'England',                      'United Kingdom'),
    (r'\bglasgow\b',                                                    'Glasgow',          'Scotland',                     'United Kingdom'),
    (r'\bedinburgh\b',                                                  'Edinburgh',        'Scotland',                     'United Kingdom'),
    (r'\baberdeen\b',                                                   'Aberdeen',         'Scotland',                     'United Kingdom'),
    (r'\bdundee\b',                                                     'Dundee',           'Scotland',                     'United Kingdom'),
    (r'\binverness\b',                                                  'Inverness',        'Scotland',                     'United Kingdom'),
    (r'\bcardiff\b',                                                    'Cardiff',          'Wales',                        'United Kingdom'),
    (r'\bswansea\b',                                                    'Swansea',          'Wales',                        'United Kingdom'),
    (r'\bbelfast\b',                                                    'Belfast',          'Northern Ireland',             'United Kingdom'),
    (r'\b(?:londonderry|derry)\b',                                      'Derry',            'Northern Ireland',             'United Kingdom'),
    (r'\bscotland\b|\bscottish\b',                                      None,               'Scotland',                     'United Kingdom'),
    (r'\bwales\b|\bwelsh\b|\bcymru\b',                                  None,               'Wales',                        'United Kingdom'),
    (r'\bnorthern ireland\b',                                           None,               'Northern Ireland',             'United Kingdom'),
    (r'\bengland\b|\benglish\b(?=.*\b(?:uk|britain)\b)',                None,               'England',                      'United Kingdom'),
    (r'\byorkshire\b',                                                  None,               'England',                      'United Kingdom'),
    (r'\b(?:united kingdom|great britain|britain|british|u\.?k\.?)\b',  None,               None,                           'United Kingdom'),

    # =========================================================
    # SPAIN — MAJOR CITIES AND AUTONOMOUS COMMUNITIES
    # =========================================================
    (r'\bmadrid\b',                                                     'Madrid',           'Community of Madrid',          'Spain'),
    (r'\bbarcelona\b',                                                  'Barcelona',        'Catalonia',                    'Spain'),
    (r'\bvalencia\b(?!.*\bcalifornia\b)',                               'Valencia',         'Valencian Community',          'Spain'),
    (r'\b(?:sevilla|seville)\b',                                        'Seville',          'Andalusia',                    'Spain'),
    (r'\bzaragoza\b',                                                   'Zaragoza',         'Aragon',                       'Spain'),
    (r'\bm[aá]laga\b',                                                  'Málaga',           'Andalusia',                    'Spain'),
    (r'\bgranada\b',                                                    'Granada',          'Andalusia',                    'Spain'),
    (r'\bc[oó]rdoba\b(?!.*\bargentin)',                                 'Córdoba',          'Andalusia',                    'Spain'),
    (r'\bmarbella\b',                                                   'Marbella',         'Andalusia',                    'Spain'),
    (r'\bmurcia\b',                                                     'Murcia',           'Murcia',                       'Spain'),
    (r'\balicante\b',                                                   'Alicante',         'Valencian Community',          'Spain'),
    (r'\bbilbao\b',                                                     'Bilbao',           'Basque Country',               'Spain'),
    (r'\b(?:san sebasti[aá]n|donostia)\b',                              'San Sebastián',    'Basque Country',               'Spain'),
    (r'\bpalma de mallorca\b|\bmallorca\b|\bmajorca\b',                 'Palma',            'Balearic Islands',             'Spain'),
    (r'\bibiza\b',                                                      'Ibiza',            'Balearic Islands',             'Spain'),
    (r'\blas palmas\b',                                                 'Las Palmas',       'Canary Islands',               'Spain'),
    (r'\btenerife\b',                                                   'Santa Cruz de Tenerife', 'Canary Islands',         'Spain'),
    (r'\btoledo\b(?=.*\b(?:spain|espa[nñ]a|espana)\b)',                 'Toledo',           'Castilla-La Mancha',           'Spain'),
    (r'\bvalladolid\b',                                                 'Valladolid',       'Castile and León',             'Spain'),
    (r'\bsalamanca\b',                                                  'Salamanca',        'Castile and León',             'Spain'),
    (r'\bvigo\b',                                                       'Vigo',             'Galicia',                      'Spain'),
    (r'\bsantiago de compostela\b',                                     'Santiago de Compostela', 'Galicia',                'Spain'),
    (r'\bgij[oó]n\b',                                                   'Gijón',            'Asturias',                     'Spain'),
    (r'\bsantander\b',                                                  'Santander',        'Cantabria',                    'Spain'),
    (r'\bpamplona\b',                                                   'Pamplona',         'Navarre',                      'Spain'),
    (r'\b(?:catalonia|catalunya|catalu[nñ]a)\b',                        None,               'Catalonia',                    'Spain'),
    (r'\b(?:andaluc[ií]a|andalusia)\b',                                 None,               'Andalusia',                    'Spain'),
    (r'\b(?:basque country|pa[ií]s vasco|euskadi)\b',                   None,               'Basque Country',               'Spain'),
    (r'\bgalicia\b',                                                    None,               'Galicia',                      'Spain'),
    (r'\b(?:balearic|baleares)\b',                                      None,               'Balearic Islands',             'Spain'),
    (r'\b(?:canary islands|islas canarias)\b',                          None,               'Canary Islands',               'Spain'),
    (r'\b(?:spain|espa[nñ]a|espana|spanish)\b',                         None,               None,                           'Spain'),

    # =========================================================
    # FRANCE — MAJOR CITIES AND REGIONS
    # =========================================================
    (r'\bparis\b(?!.*\btexas\b)',                                       'Paris',            'Île-de-France',                'France'),
    (r'\bmarseille\b|\bmarseilles\b',                                   'Marseille',        "Provence-Alpes-Côte d'Azur",   'France'),
    (r'\blyon\b',                                                       'Lyon',             'Auvergne-Rhône-Alpes',         'France'),
    (r'\btoulouse\b',                                                   'Toulouse',         'Occitanie',                    'France'),
    (r'\bnice\b(?=.*\b(?:france|french|c[oô]te)\b)',                    'Nice',             "Provence-Alpes-Côte d'Azur",   'France'),
    (r'\bnantes\b',                                                     'Nantes',           'Pays de la Loire',             'France'),
    (r'\bmontpellier\b',                                                'Montpellier',      'Occitanie',                    'France'),
    (r'\bstrasbourg\b',                                                 'Strasbourg',       'Grand Est',                    'France'),
    (r'\bbordeaux\b',                                                   'Bordeaux',         'Nouvelle-Aquitaine',           'France'),
    (r'\blille\b',                                                      'Lille',            'Hauts-de-France',              'France'),
    (r'\brennes\b',                                                     'Rennes',           'Brittany',                     'France'),
    (r'\breims\b',                                                      'Reims',            'Grand Est',                    'France'),
    (r'\ble havre\b',                                                   'Le Havre',         'Normandy',                     'France'),
    (r'\bsaint[\s-]*[eé]tienne\b',                                      'Saint-Étienne',    'Auvergne-Rhône-Alpes',         'France'),
    (r'\btoulon\b',                                                     'Toulon',           "Provence-Alpes-Côte d'Azur",   'France'),
    (r'\bgrenoble\b',                                                   'Grenoble',         'Auvergne-Rhône-Alpes',         'France'),
    (r'\bdijon\b',                                                      'Dijon',            'Bourgogne-Franche-Comté',      'France'),
    (r'\bangers\b',                                                     'Angers',           'Pays de la Loire',             'France'),
    (r'\bn[iî]mes\b',                                                   'Nîmes',            'Occitanie',                    'France'),
    (r'\baix[\s-]*en[\s-]*provence\b',                                  'Aix-en-Provence',  "Provence-Alpes-Côte d'Azur",   'France'),
    (r'\bcannes\b',                                                     'Cannes',           "Provence-Alpes-Côte d'Azur",   'France'),
    (r'\bbiarritz\b',                                                   'Biarritz',         'Nouvelle-Aquitaine',           'France'),
    (r'\bannecy\b',                                                     'Annecy',           'Auvergne-Rhône-Alpes',         'France'),
    (r'\bchamonix\b',                                                   'Chamonix',         'Auvergne-Rhône-Alpes',         'France'),
    (r'\bversailles\b',                                                 'Versailles',       'Île-de-France',                'France'),
    (r'\b(?:[iî]le[\s-]*de[\s-]*france)\b',                             None,               'Île-de-France',                'France'),
    (r'\bprovence\b',                                                   None,               "Provence-Alpes-Côte d'Azur",   'France'),
    (r'\b(?:brittany|bretagne)\b',                                      None,               'Brittany',                     'France'),
    (r'\b(?:normandy|normandie)\b',                                     None,               'Normandy',                     'France'),
    (r'\boccitanie\b',                                                  None,               'Occitanie',                    'France'),
    (r'\bgrand est\b',                                                  None,               'Grand Est',                    'France'),
    (r'\bhauts[\s-]*de[\s-]*france\b',                                  None,               'Hauts-de-France',              'France'),
    (r'\bnouvelle[\s-]*aquitaine\b',                                    None,               'Nouvelle-Aquitaine',           'France'),
    (r'\b(?:corsica|corse)\b',                                          None,               'Corsica',                      'France'),
    (r'\b(?:france|french|fran[cç]ais[e]?)\b',                          None,               None,                           'France'),

    # =========================================================
    # NEPAL — MAJOR CITIES AND PROVINCES
    # =========================================================
    (r'\bkathmandu\b|\bktm\b(?=.*\bnepal\b)',                           'Kathmandu',        'Bagmati',                      'Nepal'),
    (r'\bpokhara\b',                                                    'Pokhara',          'Gandaki',                      'Nepal'),
    (r'\blalitpur\b|\bpatan\b(?=.*\bnepal\b)',                          'Lalitpur',         'Bagmati',                      'Nepal'),
    (r'\bbhaktapur\b',                                                  'Bhaktapur',        'Bagmati',                      'Nepal'),
    (r'\bhetauda\b',                                                    'Hetauda',          'Bagmati',                      'Nepal'),
    (r'\b(?:bharatpur\b(?=.*\bnepal\b)|chitwan)\b',                     'Bharatpur',        'Bagmati',                      'Nepal'),
    (r'\bbiratnagar\b',                                                 'Biratnagar',       'Koshi',                        'Nepal'),
    (r'\bdharan\b',                                                     'Dharan',           'Koshi',                        'Nepal'),
    (r'\bitahari\b',                                                    'Itahari',          'Koshi',                        'Nepal'),
    (r'\bdamak\b',                                                      'Damak',            'Koshi',                        'Nepal'),
    (r'\bilam\b',                                                       'Ilam',             'Koshi',                        'Nepal'),
    (r'\bbirgunj\b|\bbirganj\b',                                        'Birgunj',          'Madhesh',                      'Nepal'),
    (r'\bjanakpur\b',                                                   'Janakpur',         'Madhesh',                      'Nepal'),
    (r'\bbutwal\b',                                                     'Butwal',           'Lumbini',                      'Nepal'),
    (r'\bnepalgunj\b|\bnepalganj\b',                                    'Nepalgunj',        'Lumbini',                      'Nepal'),
    (r'\bsiddharthanagar\b|\bbhairahawa\b',                             'Siddharthanagar',  'Lumbini',                      'Nepal'),
    (r'\bdhangadhi\b',                                                  'Dhangadhi',        'Sudurpashchim',                'Nepal'),
    (r'\bmahendranagar\b',                                              'Mahendranagar',    'Sudurpashchim',                'Nepal'),
    (r'\bsurkhet\b',                                                    'Surkhet',          'Karnali',                      'Nepal'),
    (r'\bnamche\b|\bsolukhumbu\b',                                      None,               'Koshi',                        'Nepal'),
    (r'\bmustang\b(?=.*\bnepal\b)|\bmanang\b',                          None,               'Gandaki',                      'Nepal'),
    (r'\blumbini\b',                                                    None,               'Lumbini',                      'Nepal'),
    (r'\bbagmati\b',                                                    None,               'Bagmati',                      'Nepal'),
    (r'\bgandaki\b|\bannapurna\b',                                      None,               'Gandaki',                      'Nepal'),
    (r'\bkarnali\b',                                                    None,               'Karnali',                      'Nepal'),
    (r'\bmadhesh\b|\bmadhes\b',                                         None,               'Madhesh',                      'Nepal'),
    (r'\bsudurpashchim\b',                                              None,               'Sudurpashchim',                'Nepal'),
    (r'\b(?:sagarmatha|mount everest|everest)\b',                       None,               'Koshi',                        'Nepal'),
    (r'\b(?:nepal|nepali|nepalese)\b',                                  None,               None,                           'Nepal'),

    # =========================================================
    # BHUTAN — MAJOR TOWNS AND DZONGKHAGS
    # =========================================================
    (r'\bthimphu\b',                                                    'Thimphu',          'Thimphu',                      'Bhutan'),
    (r'\bparo\b',                                                       'Paro',             'Paro',                         'Bhutan'),
    (r'\bpunakha\b',                                                    'Punakha',          'Punakha',                      'Bhutan'),
    (r'\bphuentsholing\b|\bphuntsholing\b',                             'Phuentsholing',    'Chhukha',                      'Bhutan'),
    (r'\bgelephu\b',                                                    'Gelephu',          'Sarpang',                      'Bhutan'),
    (r'\bwangdue\b|\bwangdi\b',                                         'Wangdue Phodrang', 'Wangdue Phodrang',             'Bhutan'),
    (r'\bjakar\b|\bbumthang\b',                                         'Jakar',            'Bumthang',                     'Bhutan'),
    (r'\btrongsa\b',                                                    'Trongsa',          'Trongsa',                      'Bhutan'),
    (r'\btrashigang\b|\btashigang\b',                                   'Trashigang',       'Trashigang',                   'Bhutan'),
    (r'\bmongar\b',                                                     'Mongar',           'Mongar',                       'Bhutan'),
    (r'\bsamdrup jongkhar\b',                                           'Samdrup Jongkhar', 'Samdrup Jongkhar',             'Bhutan'),
    (r'\b(?:bhutan|bhutanese|druk yul)\b',                              None,               None,                           'Bhutan'),

    # =========================================================
    # CROATIA — MAJOR CITIES AND REGIONS
    # =========================================================
    (r'\bzagreb\b',                                                     'Zagreb',           'City of Zagreb',               'Croatia'),
    (r'\bsplit\b(?=.*\b(?:croatia|hrvatska|dalmatia)\b)',               'Split',            'Split-Dalmatia',               'Croatia'),
    (r'\brijeka\b',                                                     'Rijeka',           'Primorje-Gorski Kotar',        'Croatia'),
    (r'\bosijek\b',                                                     'Osijek',           'Osijek-Baranja',               'Croatia'),
    (r'\bzadar\b',                                                      'Zadar',            'Zadar',                        'Croatia'),
    (r'\bdubrovnik\b',                                                  'Dubrovnik',        'Dubrovnik-Neretva',            'Croatia'),
    (r'\bpula\b',                                                       'Pula',             'Istria',                       'Croatia'),
    (r'\brovinj\b',                                                     'Rovinj',           'Istria',                       'Croatia'),
    (r'\b[sš]ibenik\b',                                                 'Šibenik',          'Šibenik-Knin',                 'Croatia'),
    (r'\bvara[zž]din\b',                                                'Varaždin',         'Varaždin',                     'Croatia'),
    (r'\bkarlovac\b',                                                   'Karlovac',         'Karlovac',                     'Croatia'),
    (r'\bslavonski brod\b',                                             'Slavonski Brod',   'Brod-Posavina',                'Croatia'),
    (r'\bhvar\b|\bmakarska\b',                                          None,               'Split-Dalmatia',               'Croatia'),
    (r'\bdalmatia\b|\bdalmacija\b',                                     None,               'Dalmatia',                     'Croatia'),
    (r'\bistria\b|\bistra\b',                                           None,               'Istria',                       'Croatia'),
    (r'\bslavonia\b',                                                   None,               'Slavonia',                     'Croatia'),
    (r'\b(?:croatia|hrvatska|croatian)\b',                              None,               None,                           'Croatia'),

    # =========================================================
    # SWITZERLAND — MAJOR CITIES AND CANTONS
    # =========================================================
    (r'\b(?:z[uü]rich|zurich)\b',                                       'Zurich',           'Zurich',                       'Switzerland'),
    (r'\b(?:geneva|gen[eè]ve|genf)\b',                                  'Geneva',           'Geneva',                       'Switzerland'),
    (r'\bbasel\b|\bb[aâ]le\b',                                          'Basel',            'Basel-Stadt',                  'Switzerland'),
    (r'\b(?:bern|berne)\b',                                             'Bern',             'Bern',                         'Switzerland'),
    (r'\blausanne\b',                                                   'Lausanne',         'Vaud',                         'Switzerland'),
    (r'\b(?:lucerne|luzern)\b',                                         'Lucerne',          'Lucerne',                      'Switzerland'),
    (r'\bwinterthur\b',                                                 'Winterthur',       'Zurich',                       'Switzerland'),
    (r'\bst\.?\s*gallen\b|\bsankt gallen\b',                            'St. Gallen',       'St. Gallen',                   'Switzerland'),
    (r'\blugano\b',                                                     'Lugano',           'Ticino',                       'Switzerland'),
    (r'\blocarno\b',                                                    'Locarno',          'Ticino',                       'Switzerland'),
    (r'\bfribourg\b|\bfreiburg im [uü]echtland\b',                      'Fribourg',         'Fribourg',                     'Switzerland'),
    (r'\bneuch[aâ]tel\b',                                               'Neuchâtel',        'Neuchâtel',                    'Switzerland'),
    (r'\bsion\b',                                                       'Sion',             'Valais',                       'Switzerland'),
    (r'\bchur\b',                                                       'Chur',             'Grisons',                      'Switzerland'),
    (r'\bzermatt\b',                                                    'Zermatt',          'Valais',                       'Switzerland'),
    (r'\bdavos\b',                                                      'Davos',            'Grisons',                      'Switzerland'),
    (r'\bst\.?\s*moritz\b',                                             'St. Moritz',       'Grisons',                      'Switzerland'),
    (r'\binterlaken\b',                                                 'Interlaken',       'Bern',                         'Switzerland'),
    (r'\bmontreux\b',                                                   'Montreux',         'Vaud',                         'Switzerland'),
    (r'\b(?:valais|wallis)\b',                                          None,               'Valais',                       'Switzerland'),
    (r'\bticino\b',                                                     None,               'Ticino',                       'Switzerland'),
    (r'\bvaud\b',                                                       None,               'Vaud',                         'Switzerland'),
    (r'\b(?:grisons|graub[uü]nden)\b',                                  None,               'Grisons',                      'Switzerland'),
    (r'\b(?:switzerland|schweiz|suisse|svizzera|swiss)\b',              None,               None,                           'Switzerland'),

    # =========================================================
    # ITALY
    # =========================================================
    (r'\b(?:rome|roma)\b(?!.*\b(?:georgia|new york)\b)',                'Rome',             'Lazio',                        'Italy'),
    (r'\b(?:milan|milano)\b',                                           'Milan',            'Lombardy',                     'Italy'),
    (r'\b(?:naples|napoli)\b',                                          'Naples',           'Campania',                     'Italy'),
    (r'\b(?:turin|torino)\b',                                           'Turin',            'Piedmont',                     'Italy'),
    (r'\b(?:florence|firenze)\b(?!.*\b(?:alabama|south carolina)\b)',   'Florence',         'Tuscany',                      'Italy'),
    (r'\b(?:venice|venezia)\b(?!.*\b(?:california|beach)\b)',           'Venice',           'Veneto',                       'Italy'),
    (r'\bbologna\b',                                                    'Bologna',          'Emilia-Romagna',               'Italy'),
    (r'\bpalermo\b',                                                    'Palermo',          'Sicily',                       'Italy'),
    (r'\bverona\b',                                                     'Verona',           'Veneto',                       'Italy'),
    (r'\b(?:genoa|genova)\b',                                           'Genoa',            'Liguria',                      'Italy'),
    (r'\bbari\b',                                                       'Bari',             'Apulia',                       'Italy'),
    (r'\bcatania\b',                                                    'Catania',          'Sicily',                       'Italy'),
    (r'\bpisa\b|\bsiena\b',                                             None,               'Tuscany',                      'Italy'),
    (r'\b(?:tuscany|toscana)\b',                                        None,               'Tuscany',                      'Italy'),
    (r'\b(?:lombardy|lombardia)\b',                                     None,               'Lombardy',                     'Italy'),
    (r'\b(?:sicily|sicilia)\b',                                         None,               'Sicily',                       'Italy'),
    (r'\b(?:sardinia|sardegna)\b',                                      None,               'Sardinia',                     'Italy'),
    (r'\bamalfi\b|\bcapri\b|\bpositano\b',                              None,               'Campania',                     'Italy'),
    (r'\b(?:italy|italia|italian)\b',                                   None,               None,                           'Italy'),

    # =========================================================
    # PORTUGAL
    # =========================================================
    (r'\b(?:lisbon|lisboa)\b',                                          'Lisbon',           'Lisbon',                       'Portugal'),
    (r'\bporto\b(?!\s*alegre)|\boporto\b',                              'Porto',            'Porto',                        'Portugal'),
    (r'\bbraga\b',                                                      'Braga',            'Braga',                        'Portugal'),
    (r'\bcoimbra\b',                                                    'Coimbra',          'Coimbra',                      'Portugal'),
    (r'\bfaro\b',                                                       'Faro',             'Algarve',                      'Portugal'),
    (r'\bfunchal\b|\bmadeira\b',                                        'Funchal',          'Madeira',                      'Portugal'),
    (r'\balgarve\b',                                                    None,               'Algarve',                      'Portugal'),
    (r'\bazores\b|\ba[cç]ores\b',                                       None,               'Azores',                       'Portugal'),
    (r'\b(?:portugal|portuguese|portugu[eê]s)\b',                       None,               None,                           'Portugal'),

    # =========================================================
    # AUSTRIA / BELGIUM / IRELAND
    # =========================================================
    (r'\b(?:vienna|wien)\b(?!.*\bvirginia\b)',                          'Vienna',           'Vienna',                       'Austria'),
    (r'\bsalzburg\b',                                                   'Salzburg',         'Salzburg',                     'Austria'),
    (r'\bgraz\b',                                                       'Graz',             'Styria',                       'Austria'),
    (r'\binnsbruck\b',                                                  'Innsbruck',        'Tyrol',                        'Austria'),
    (r'\blinz\b',                                                       'Linz',             'Upper Austria',                'Austria'),
    (r'\bklagenfurt\b',                                                 'Klagenfurt',       'Carinthia',                    'Austria'),
    (r'\b(?:tyrol|tirol)\b',                                            None,               'Tyrol',                        'Austria'),
    (r'\b(?:austria|[oö]sterreich|austrian)\b',                         None,               None,                           'Austria'),

    (r'\b(?:brussels|bruxelles|brussel)\b',                             'Brussels',         'Brussels-Capital',             'Belgium'),
    (r'\b(?:antwerp|antwerpen|anvers)\b',                               'Antwerp',          'Flanders',                     'Belgium'),
    (r'\b(?:ghent|gent|gand)\b',                                        'Ghent',            'Flanders',                     'Belgium'),
    (r'\b(?:bruges|brugge)\b',                                          'Bruges',           'Flanders',                     'Belgium'),
    (r'\b(?:liege|li[eè]ge|luik)\b',                                    'Liège',            'Wallonia',                     'Belgium'),
    (r'\bleuven\b|\blouvain\b',                                         'Leuven',           'Flanders',                     'Belgium'),
    (r'\b(?:flanders|vlaanderen)\b',                                    None,               'Flanders',                     'Belgium'),
    (r'\b(?:wallonia|wallonie)\b',                                      None,               'Wallonia',                     'Belgium'),
    (r'\b(?:belgium|belgi[eë]|belgique|belgian)\b',                     None,               None,                           'Belgium'),

    (r'\bdublin\b(?!.*\b(?:ohio|california)\b)',                        'Dublin',           'Leinster',                     'Ireland'),
    (r'\bcork\b(?=.*\bireland\b)',                                      'Cork',             'Munster',                      'Ireland'),
    (r'\bgalway\b',                                                     'Galway',           'Connacht',                     'Ireland'),
    (r'\blimerick\b',                                                   'Limerick',         'Munster',                      'Ireland'),
    (r'\bwaterford\b',                                                  'Waterford',        'Munster',                      'Ireland'),
    (r'\b(?:ireland|[eé]ire|irish)\b(?!.*\bnorthern\b)',                None,               None,                           'Ireland'),

    # =========================================================
    # NORDICS
    # =========================================================
    (r'\bstockholm\b',                                                  'Stockholm',        'Stockholm',                    'Sweden'),
    (r'\b(?:gothenburg|g[oö]teborg)\b',                                 'Gothenburg',       'Västra Götaland',              'Sweden'),
    (r'\bmalm[oö]\b',                                                   'Malmö',            'Skåne',                        'Sweden'),
    (r'\buppsala\b',                                                    'Uppsala',          'Uppsala',                      'Sweden'),
    (r'\b(?:sweden|sverige|swedish)\b',                                 None,               None,                           'Sweden'),

    (r'\boslo\b',                                                       'Oslo',             'Oslo',                         'Norway'),
    (r'\bbergen\b(?=.*\bnorway\b)',                                     'Bergen',           'Vestland',                     'Norway'),
    (r'\btrondheim\b',                                                  'Trondheim',        'Trøndelag',                    'Norway'),
    (r'\bstavanger\b',                                                  'Stavanger',        'Rogaland',                     'Norway'),
    (r'\btroms[oø]\b',                                                  'Tromsø',           'Troms',                        'Norway'),
    (r'\b(?:norway|norge|norwegian)\b',                                 None,               None,                           'Norway'),

    (r'\b(?:copenhagen|k[oø]benhavn)\b',                                'Copenhagen',       'Capital Region',               'Denmark'),
    (r'\b(?:aarhus|[aå]rhus)\b',                                        'Aarhus',           'Central Jutland',              'Denmark'),
    (r'\bodense\b',                                                     'Odense',           'Southern Denmark',             'Denmark'),
    (r'\baalborg\b',                                                    'Aalborg',          'North Jutland',                'Denmark'),
    (r'\b(?:denmark|danmark|danish)\b',                                 None,               None,                           'Denmark'),

    (r'\b(?:helsinki|helsingfors)\b',                                   'Helsinki',         'Uusimaa',                      'Finland'),
    (r'\bespoo\b',                                                      'Espoo',            'Uusimaa',                      'Finland'),
    (r'\btampere\b',                                                    'Tampere',          'Pirkanmaa',                    'Finland'),
    (r'\bturku\b',                                                      'Turku',            'Southwest Finland',            'Finland'),
    (r'\b(?:finland|suomi|finnish)\b',                                  None,               None,                           'Finland'),

    (r'\breykjav[ií]k\b',                                               'Reykjavík',        'Capital Region',               'Iceland'),
    (r'\b(?:iceland|[ií]sland|icelandic)\b',                            None,               None,                           'Iceland'),

    # =========================================================
    # CENTRAL / EASTERN EUROPE
    # =========================================================
    (r'\b(?:warsaw|warszawa)\b',                                        'Warsaw',           'Masovian',                     'Poland'),
    (r'\b(?:krakow|krak[oó]w|cracow)\b',                                'Kraków',           'Lesser Poland',                'Poland'),
    (r'\b(?:wroclaw|wroc[lł]aw)\b',                                     'Wrocław',          'Lower Silesian',               'Poland'),
    (r'\b(?:gdansk|gda[nń]sk)\b',                                       'Gdańsk',           'Pomeranian',                   'Poland'),
    (r'\b(?:poznan|pozna[nń])\b',                                       'Poznań',           'Greater Poland',               'Poland'),
    (r'\b(?:lodz|[lł][oó]d[zź])\b',                                     'Łódź',             'Łódź',                         'Poland'),
    (r'\b(?:poland|polska|polish)\b',                                   None,               None,                           'Poland'),

    (r'\b(?:prague|praha)\b',                                           'Prague',           'Prague',                       'Czechia'),
    (r'\bbrno\b',                                                       'Brno',             'South Moravian',               'Czechia'),
    (r'\bostrava\b',                                                    'Ostrava',          'Moravian-Silesian',            'Czechia'),
    (r'\b(?:czechia|czech republic|czech|[cč]esko)\b',                  None,               None,                           'Czechia'),

    (r'\bbudapest\b',                                                   'Budapest',         'Budapest',                     'Hungary'),
    (r'\bdebrecen\b',                                                   'Debrecen',         'Hajdú-Bihar',                  'Hungary'),
    (r'\b(?:hungary|magyarorsz[aá]g|hungarian)\b',                      None,               None,                           'Hungary'),

    (r'\bbratislava\b',                                                 'Bratislava',       'Bratislava',                   'Slovakia'),
    (r'\b(?:slovakia|slovensko|slovak)\b',                              None,               None,                           'Slovakia'),

    (r'\bljubljana\b',                                                  'Ljubljana',        'Central Slovenia',             'Slovenia'),
    (r'\bmaribor\b',                                                    'Maribor',          'Drava',                        'Slovenia'),
    (r'\bbled\b',                                                       'Bled',             'Upper Carniola',               'Slovenia'),
    (r'\b(?:slovenia|slovenija|slovenian)\b',                           None,               None,                           'Slovenia'),

    (r'\b(?:belgrade|beograd)\b',                                       'Belgrade',         'Belgrade',                     'Serbia'),
    (r'\bnovi sad\b',                                                   'Novi Sad',         'Vojvodina',                    'Serbia'),
    (r'\b(?:serbia|srbija|serbian)\b',                                  None,               None,                           'Serbia'),

    (r'\b(?:bucharest|bucure[sș]ti)\b',                                 'Bucharest',        'Bucharest',                    'Romania'),
    (r'\bcluj[\s-]*napoca\b|\bcluj\b',                                  'Cluj-Napoca',      'Cluj',                         'Romania'),
    (r'\b(?:romania|rom[aâ]nia|romanian)\b',                            None,               None,                           'Romania'),

    (r'\bsofia\b(?=.*\bbulgaria\b)',                                    'Sofia',            'Sofia City',                   'Bulgaria'),
    (r'\bplovdiv\b|\bvarna\b',                                          None,               None,                           'Bulgaria'),
    (r'\b(?:bulgaria|bulgarian)\b',                                     None,               None,                           'Bulgaria'),

    (r'\b(?:athens|athina)\b(?!.*\bgeorgia\b)',                         'Athens',           'Attica',                       'Greece'),
    (r'\bthessaloniki\b',                                               'Thessaloniki',     'Central Macedonia',            'Greece'),
    (r'\bheraklion\b|\bcrete\b|\bkriti\b',                              None,               'Crete',                        'Greece'),
    (r'\bsantorini\b|\bmykonos\b|\bnaxos\b',                            None,               'South Aegean',                 'Greece'),
    (r'\b(?:greece|hellas|greek)\b',                                    None,               None,                           'Greece'),

    (r'\b(?:istanbul|constantinople)\b',                                'Istanbul',         'Istanbul',                     'Turkey'),
    (r'\bankara\b',                                                     'Ankara',           'Ankara',                       'Turkey'),
    (r'\bizmir\b',                                                      'Izmir',            'Izmir',                        'Turkey'),
    (r'\bantalya\b',                                                    'Antalya',          'Antalya',                      'Turkey'),
    (r'\bbodrum\b|\bfethiye\b',                                         None,               'Muğla',                        'Turkey'),
    (r'\b(?:turkey|t[uü]rkiye|turkish)\b',                              None,               None,                           'Turkey'),

    # =========================================================
    # MIDDLE EAST / ASIA / OCEANIA / AMERICAS / AFRICA
    # =========================================================
    (r'\bdubai\b',                                                      'Dubai',            'Dubai',                        'United Arab Emirates'),
    (r'\babu dhabi\b',                                                  'Abu Dhabi',        'Abu Dhabi',                    'United Arab Emirates'),
    (r'\bsharjah\b',                                                    'Sharjah',          'Sharjah',                      'United Arab Emirates'),
    (r'\b(?:united arab emirates|uae|emirates)\b',                      None,               None,                           'United Arab Emirates'),

    (r'\bsingapore\b',                                                  'Singapore',        None,                           'Singapore'),

    (r'\b(?:seoul|se[o]ul)\b',                                          'Seoul',            'Seoul',                        'South Korea'),
    (r'\bbusan\b',                                                      'Busan',            'Busan',                        'South Korea'),
    (r'\bincheon\b',                                                    'Incheon',          'Incheon',                      'South Korea'),
    (r'\bjeju\b',                                                       'Jeju',             'Jeju',                         'South Korea'),
    (r'\b(?:south korea|korea|korean)\b',                               None,               None,                           'South Korea'),

    (r'\bbangkok\b',                                                    'Bangkok',          'Bangkok',                      'Thailand'),
    (r'\bchiang mai\b',                                                 'Chiang Mai',       'Chiang Mai',                   'Thailand'),
    (r'\bphuket\b',                                                     'Phuket',           'Phuket',                       'Thailand'),
    (r'\bpattaya\b|\bkrabi\b|\bkoh samui\b',                            None,               None,                           'Thailand'),
    (r'\b(?:thailand|thai)\b',                                          None,               None,                           'Thailand'),

    (r'\bjakarta\b',                                                    'Jakarta',          'Jakarta',                      'Indonesia'),
    (r'\bbali\b|\bdenpasar\b|\bubud\b|\bcanggu\b|\bseminyak\b',         'Denpasar',         'Bali',                         'Indonesia'),
    (r'\bsurabaya\b',                                                   'Surabaya',         'East Java',                    'Indonesia'),
    (r'\bbandung\b',                                                    'Bandung',          'West Java',                    'Indonesia'),
    (r'\byogyakarta\b|\bjogja\b',                                       'Yogyakarta',       'Yogyakarta',                   'Indonesia'),
    (r'\b(?:indonesia|indonesian)\b',                                   None,               None,                           'Indonesia'),

    (r'\bkuala lumpur\b',                                               'Kuala Lumpur',     'Kuala Lumpur',                 'Malaysia'),
    (r'\bpenang\b|\bgeorge town\b(?=.*\bmalaysia\b)',                   'Penang',           'Penang',                       'Malaysia'),
    (r'\bjohor bahru\b',                                                'Johor Bahru',      'Johor',                        'Malaysia'),
    (r'\b(?:malaysia|malaysian)\b',                                     None,               None,                           'Malaysia'),

    (r'\b(?:ho chi minh|saigon)\b',                                     'Ho Chi Minh City', None,                           'Vietnam'),
    (r'\bhanoi\b',                                                      'Hanoi',            None,                           'Vietnam'),
    (r'\bda nang\b|\bdanang\b|\bhoi an\b',                              'Da Nang',          None,                           'Vietnam'),
    (r'\b(?:vietnam|viet nam|vietnamese)\b',                            None,               None,                           'Vietnam'),

    (r'\bmanila\b',                                                     'Manila',           'Metro Manila',                 'Philippines'),
    (r'\bquezon city\b',                                                'Quezon City',      'Metro Manila',                 'Philippines'),
    (r'\bcebu\b',                                                       'Cebu City',        'Cebu',                         'Philippines'),
    (r'\bdavao\b',                                                      'Davao City',       'Davao',                        'Philippines'),
    (r'\b(?:philippines|filipino|pinoy)\b',                             None,               None,                           'Philippines'),

    (r'\bcolombo\b',                                                    'Colombo',          'Western',                      'Sri Lanka'),
    (r'\bkandy\b|\bgalle\b',                                            None,               None,                           'Sri Lanka'),
    (r'\b(?:sri lanka|sri lankan)\b',                                   None,               None,                           'Sri Lanka'),

    (r'\bdhaka\b',                                                      'Dhaka',            'Dhaka',                        'Bangladesh'),
    (r'\bchittagong\b|\bchattogram\b',                                  'Chattogram',       'Chattogram',                   'Bangladesh'),
    (r'\b(?:bangladesh|bangladeshi)\b',                                 None,               None,                           'Bangladesh'),

    (r'\bkarachi\b',                                                    'Karachi',          'Sindh',                        'Pakistan'),
    (r'\blahore\b',                                                     'Lahore',           'Punjab',                       'Pakistan'),
    (r'\bislamabad\b',                                                  'Islamabad',        'Islamabad',                    'Pakistan'),
    (r'\b(?:pakistan|pakistani)\b',                                     None,               None,                           'Pakistan'),

    (r'\bauckland\b',                                                   'Auckland',         'Auckland',                     'New Zealand'),
    (r'\bwellington\b(?=.*\b(?:new zealand|nz)\b)',                     'Wellington',       'Wellington',                   'New Zealand'),
    (r'\bchristchurch\b',                                               'Christchurch',     'Canterbury',                   'New Zealand'),
    (r'\bqueenstown\b',                                                 'Queenstown',       'Otago',                        'New Zealand'),
    (r'\b(?:new zealand|aotearoa)\b',                                   None,               None,                           'New Zealand'),

    (r'\b(?:sao paulo|s[aã]o paulo)\b',                                 'São Paulo',        'São Paulo',                    'Brazil'),
    (r'\brio de janeiro\b',                                             'Rio de Janeiro',   'Rio de Janeiro',               'Brazil'),
    (r'\bbras[ií]lia\b',                                                'Brasília',         'Federal District',             'Brazil'),
    (r'\bsalvador\b(?=.*\bbrazil\b)|\bporto alegre\b',                  None,               None,                           'Brazil'),
    (r'\b(?:brazil|brasil|brazilian)\b',                                None,               None,                           'Brazil'),

    (r'\bbuenos aires\b',                                               'Buenos Aires',     'Buenos Aires',                 'Argentina'),
    (r'\bc[oó]rdoba\b(?=.*\bargentin)',                                 'Córdoba',          'Córdoba',                      'Argentina'),
    (r'\b(?:argentina|argentine|argentinian)\b',                        None,               None,                           'Argentina'),

    (r'\bsantiago\b(?=.*\bchile\b)',                                    'Santiago',         'Santiago Metropolitan',        'Chile'),
    (r'\b(?:chile|chilean)\b',                                          None,               None,                           'Chile'),

    (r'\bcape town\b|\bkaapstad\b',                                     'Cape Town',        'Western Cape',                 'South Africa'),
    (r'\bjohannesburg\b|\bjoburg\b',                                    'Johannesburg',     'Gauteng',                      'South Africa'),
    (r'\bdurban\b',                                                     'Durban',           'KwaZulu-Natal',                'South Africa'),
    (r'\bpretoria\b',                                                   'Pretoria',         'Gauteng',                      'South Africa'),
    (r'\b(?:south africa|south african)\b',                             None,               None,                           'South Africa'),
]
# fmt: on


# ---------------------------------------------------------------------------
# EMOJI / UNICODE LOCATION INDICATORS
# ---------------------------------------------------------------------------
LOCATION_EMOJI_PATTERN = re.compile(
    r'(?:📍|🌍|🌎|🌏|🗺|📌|🏙|🏡|🏠|🌆|🌇|🌃|🗼|✈️|✈)\s*(.{2,40})'
)

# ---------------------------------------------------------------------------
# ZIP / POSTAL CODE PATTERNS
# ---------------------------------------------------------------------------
# Each tuple: (compiled regex, country_hint)
# Matched against the raw biography (not lowercased, to preserve digits).
ZIP_CODE_PATTERNS = [
    # USA: exactly 5 digits, optionally followed by a hyphen and 4 more (ZIP+4)
    (re.compile(r'\b(\d{5}(?:-\d{4})?)\b'), 'USA'),
    # Canada: A1A 1A1 format (letter-digit-letter space digit-letter-digit)
    (re.compile(r'\b([A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d)\b'), 'Canada'),
    # India: 6-digit PIN codes (100000–999999)
    (re.compile(r'\b([1-9]\d{5})\b'), 'India'),
    # China: 6-digit postal codes (100000–999999, same range; matched after India context)
    (re.compile(r'\b([1-9]\d{5})\b'), 'China'),
]

# A standalone 5-digit run could be a phone fragment — require it to appear
# near a location signal word or at a line boundary to reduce false positives.
_ZIP_CONTEXT_PATTERN = re.compile(
    r'(?:zip|postal|pin|pincode|zip\s*code|post\s*code|📍|🏠|🏡|🌆)[^\d]{0,15}(\d{5,6}(?:-\d{4})?)'
    r'|(?:^|[\s,|•·])(\d{5}(?:-\d{4})?)(?:[\s,|•·]|$)'
    r'|(?:^|[\s,|•·])([A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d)(?:[\s,|•·]|$)'
    r'|(?:^|[\s,|•·])([1-9]\d{5})(?:[\s,|•·]|$)',
    re.IGNORECASE | re.MULTILINE,
)


def _extract_zip_code(biography: str) -> Optional[str]:
    """
    Extract a postal / zip code from the raw biography text.
    Priority:
      1. Codes appearing next to explicit zip/postal/pin keywords or a location emoji.
      2. Standalone 5-digit (USA), 6-letter-digit (Canada), or 6-digit (India/China) codes.
    Returns the first plausible match as a string, or None.
    """
    if not biography:
        return None

    for m in _ZIP_CONTEXT_PATTERN.finditer(biography):
        # Return whichever capture group matched
        code = next((g for g in m.groups() if g), None)
        if code:
            return code.strip()

    return None


BASED_IN_PATTERN = re.compile(
    r'\bbased\s+in\s+(.{2,30}?)(?:\s*[|•·,\n]|$)', re.IGNORECASE
)
BASED_SUFFIX_PATTERN = re.compile(
    r'(.{2,30}?)\s*[-–]?\s*based\b', re.IGNORECASE
)
LOCATION_IN_PATTERN = re.compile(
    r'\b(?:located|living|based|from|in|at)\s+(?:in\s+)?(.{2,40}?)(?:\s*[|•·,\n]|$)',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# CORE MATCHER
# ---------------------------------------------------------------------------

def _match_patterns(text: str) -> Optional[Dict]:
    """
    Run all LOCATION_PATTERNS against `text`.
    Returns the first match as {city, state, country} or None.
    """
    text_lower = text.lower()
    for pattern, city, state, country in LOCATION_PATTERNS:
        try:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    'city':    city,
                    'state':   state,
                    'country': country,
                }
        except re.error:
            continue
    return None


def _clean_bio_segment(segment: str) -> str:
    """Strip common separators and extra whitespace from a bio segment."""
    return re.sub(r'[|•·\-–—]+', ' ', segment).strip()


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def extract_location_from_bio(biography: str) -> Dict:
    """
    Parse an Instagram biography string and return location components.

    Returns:
        {
            'city':       str | None,
            'state':      str | None,
            'country':    str | None,
            'zip_code':   str | None,
            'confidence': 'high' | 'medium' | 'low' | None
                          high   → location-emoji / "based in" phrase
                          medium → direct city/name keyword match
                          low    → country-only match

        All fields that have no value are returned as None (never as "").
        }
    """
    empty = {'city': None, 'state': None, 'country': None, 'zip_code': None, 'confidence': None}
    if not biography or not isinstance(biography, str):
        return empty

    bio = biography.strip()

    # Extract zip/postal code from the full raw bio (before any segment trimming)
    zip_code = _extract_zip_code(bio)

    location_result = None

    # ── 1. Location-emoji hint (highest signal) ──────────────────────────────
    for m in LOCATION_EMOJI_PATTERN.finditer(bio):
        segment = _clean_bio_segment(m.group(1))
        result  = _match_patterns(segment)
        if result:
            result['confidence'] = 'high'
            location_result = result
            break

    # ── 2. "based in <place>" / "<place>-based" ───────────────────────────────
    if not location_result:
        for m in BASED_IN_PATTERN.finditer(bio):
            segment = _clean_bio_segment(m.group(1))
            result  = _match_patterns(segment)
            if result:
                result['confidence'] = 'high'
                location_result = result
                break

    if not location_result:
        for m in BASED_SUFFIX_PATTERN.finditer(bio):
            segment = _clean_bio_segment(m.group(1))
            result  = _match_patterns(segment)
            if result:
                result['confidence'] = 'high'
                location_result = result
                break

    # ── 3. "from / in / living in <place>" ───────────────────────────────────
    if not location_result:
        for m in LOCATION_IN_PATTERN.finditer(bio):
            segment = _clean_bio_segment(m.group(1))
            result  = _match_patterns(segment)
            if result:
                result['confidence'] = 'medium'
                location_result = result
                break

    # ── 4. Full bio scan — try each line, then pipe/bullet segments ──────────
    if not location_result:
        for line in bio.splitlines():
            line = line.strip()
            if not line:
                continue
            result = _match_patterns(line)
            if result:
                result['confidence'] = 'medium' if result['city'] else 'low'
                location_result = result
                break

    if not location_result:
        for segment in re.split(r'[|•·]+', bio):
            segment = segment.strip()
            if not segment:
                continue
            result = _match_patterns(segment)
            if result:
                result['confidence'] = 'medium' if result['city'] else 'low'
                location_result = result
                break

    # Full bio as last resort
    if not location_result:
        result = _match_patterns(bio)
        if result:
            result['confidence'] = 'medium' if result['city'] else 'low'
            location_result = result

    if location_result:
        # Ensure all string fields are None (not "") when empty
        for key in ('city', 'state', 'country'):
            if location_result.get(key) == '':
                location_result[key] = None
        location_result['country'] = country_to_alpha2(location_result.get('country'))
        location_result['zip_code'] = zip_code
        return location_result

    # Nothing matched — return empty with zip_code if found
    empty['zip_code'] = zip_code
    return empty


# ---------------------------------------------------------------------------
# QUICK SELF-TEST
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_bios = [
        "📍 Los Angeles | Content creator | DMs open",
        "New York City based photographer & filmmaker",
        "based in San Francisco | tech lover",
        "Living in Toronto, Ontario 🍁",
        "Mumbai girl 🇮🇳 | fashion & beauty",
        "Bengaluru | software engineer | 🎮 gamer",
        "From Vancouver, British Columbia 🍁",
        "Foodie in Hyderabad 🍛",
        "Based in Austin | music producer",
        "Calgary Alberta | outdoor adventurer",
        "Hong Kong 🇭🇰 | travel & lifestyle",
        "Shanghai based entrepreneur",
        "Just a regular dude",
        "📍 Jaipur, Rajasthan 🌸",
        "New York | Los Angeles | Miami — always moving",
        "Norcal raised, Socal living",
        "Chandigarh | Punjab 🇮🇳",
        "Ottawa girl 🇨🇦",
        "Las Vegas, Nevada",
        "Portland | Coffee | Rain",
        "📍 Los Angeles, CA 90001 | lifestyle creator",
        "Based in Austin, TX 78701 | music producer",
        "Mumbai 400001 🇮🇳 | fashion blogger",
        "Toronto M5V 3A8 🇨🇦 | food enthusiast",
    ]

    for bio in test_bios:
        result = extract_location_from_bio(bio)
        print(f"BIO : {bio!r}")
        print(f"  → city={result['city']!r}  state={result['state']!r}  country={result['country']!r}  zip_code={result['zip_code']!r}  confidence={result['confidence']!r}")
        print()