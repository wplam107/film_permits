import re
from datetime import datetime

import configparser
from sodapy import Socrata

DATASET = 'tg4x-b46p'
CONFIG_FILE = 'configs.ini'
PERMIT_TYPE = 'Shooting Permit'

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

### Data Retrieval Function ###
def get_permits(date: str) -> list:
    """
    Function to retrieve permits where shooting
    includes a specified date (YYYY-MM-DD).
    """
    socrata_token = config['socrata']['APP_TOKEN']
    client = Socrata("data.cityofnewyork.us", app_token=socrata_token)
    results = client.get(
        DATASET,
        where=(
            """
            eventtype = '{}'
            and startdatetime <= '{}'
            and enddatetime >='{}'
            """
        ).format(PERMIT_TYPE, date, date),
        order="startdatetime DESC"
    )

    return results


### Helper Functions for Data Cleaning ###
def _split_addresses(address_str: str) -> list:
    """
    Helper function to convert address string to list of intersections.
    """
    addresses = address_str.split(', ')
    addresses = [
        ' '.join([ word.capitalize() for word in s.split() ])
        for s in addresses
    ]

    return addresses

def _clean_boro(boro: str) -> str:
    """
    Helper function to standardize borough names.
    """
    boro = boro.capitalize()

    return boro

def _ordinal_rep(s: str) -> str:
    """
    Helper function to convert numerical cardinality to ordinality.
    """
    num = re.search(r'[0-9]+\s', s)
    if num == None:
        return s
    else:
        num = re.search(r'[0-9]+', s)[0]
        if len(num) > 1:
            if (num[-1] == '1') and (num[-2] != '1'):
                ord = num + 'st'
            elif num[-1] == '2' and (num[-2] != '1'):
                ord = num + 'nd'
            elif num[-1] == '3' and (num[-2] != '1'):
                ord = num + 'rd'
            else:
                ord = num + 'th'
        else:
            if (num[-1] == '1'):
                ord = num + 'st'
            elif num[-1] == '2':
                ord = num + 'nd'
            elif num[-1] == '3':
                ord = num + 'rd'
            else:
                ord = num + 'th'

        return s.replace(num, ord)

def _abb_to_full(street: str) -> str:
    """
    Helper function to convert cardinality abbreviation to full.
    """
    if 'W ' in street:
        street = 'West ' + street.split('W ')[1]
    if 'E ' in street:
        street = 'East ' + street.split('E ')[1]
    if 'N ' in street:
        street = 'North ' + street.split('N ')[1]
    if 'S ' in street:
        street = 'South ' + street.split('S ')[1]

    return street

def _standardize_street(street: str) -> str:
    """
    Helper function to standardize street names.
    """
    if ' St' in street:
        street = street.split(' St')[0] + ' Street'
    if ' Ave' in street:
        street = street.split(' Ave')[0] + ' Avenue'
    if ' Rd' in street:
        street = street.split(' Rd')[0] + ' Road'
    if ' Pkwy' in street:
        street = street.split(' Pkwy')[0] + ' Parkway'
    if ' Blvd' in street:
        street = street.split(' Blvd')[0] + ' Boulevard'

    return street

def _clean_street(address: str) -> str:
    """
    Helper function to clean street strings.
    """
    address = _ordinal_rep(address)
    address = _standardize_street(address)
    address = _abb_to_full(address)

    return address

def _get_intersections(address: str, boro: str) -> tuple | None:
    """
    Helper function to extract intersections from address.
    """
    null_streets = ['Dead Road', 'Dead End', 'Dead Rd']
    for s in null_streets:
        if s in address:
            return None
    
    intersections = address.split(' Between ')
    if len(intersections) != 2:
        return None
    
    main_st = intersections[0]
    cross_sts = intersections[1].split(' And ')
    total_names = [main_st] + cross_sts
    if len(total_names) != 3:
        return None

    p1 = [_clean_street(main_st), _clean_street(cross_sts[0])] + [boro]
    p2 = [_clean_street(main_st), _clean_street(cross_sts[1])] + [boro]

    return (p1, p2)

def _clean_datetime(date: str) -> datetime:
    """
    Helper function to covert datetime string to datetime object.
    """
    date = ' '.join(date.split('T'))
    date = date.split('.')[0]
    date_format = '%Y-%m-%d %H:%M:%S'
    date = datetime.strptime(date, date_format)
    
    return date


### Main Data Cleaning Functions ###
def clean_data(row: dict) -> dict:
    """
    Function to clean film permit row.
    """
    eventid = row['eventid']
    boro = _clean_boro(row['borough'])
    addresses = _split_addresses(row['parkingheld'])
    addresses = [
        _get_intersections(address, boro) for address in addresses
    ]

    startdate = _clean_datetime(row['startdatetime'])
    enddate = _clean_datetime(row['enddatetime'])
    enteredon = _clean_datetime(row['enteredon'])

    category = row['category']
    subcategory = row['subcategoryname']
    country = row['country']

    data_dict = {
        'id': eventid,
        'streets': addresses,
        'startdate': startdate,
        'enddate': enddate,
        'enteredon': enteredon,
        'category': category,
        'subcategory': subcategory,
        'origin': country
    }

    return data_dict