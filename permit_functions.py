import re
import pandas as pd
from datetime import datetime

import configparser
from sodapy import Socrata

DATASET = 'tg4x-b46p'
CONFIG_FILE = 'configs.ini'
PERMIT_TYPE = 'Shooting Permit'

SPECIAL_CASES = {
    'brooklyn bridge boulevard': 'adams street - brooklyn bridge boulevard',
    'laguardia place': 'la guardia place',
    'north powell jr boulevard': 'adam clayton powell jr. boulevard',
    'adam clayton powell jr boulevard': 'adam clayton powell jr. boulevard',
    'avenue of the americas': '6th avenue',
    'fort green place': 'fort greene place',
    'west 106th street': 'west 106th street / duke ellington',
    'adam clayton powell boulevard': 'adam clayton powell jr. boulevard',

}

ABB_DICT = {
    'st': 'street',
    'ave': 'avenue',
    'ct': 'court',
    'blvd': 'boulevard',
    'sq': 'square',
    'rd': 'road',
    'ln': 'lane',
    'expy': 'expressway',
    'pkwy': 'parkway',
    'pl': 'place',
    'dr': 'drive'
}

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
        ' '.join([ word.lower() for word in s.split() ])
        for s in addresses
    ]

    return addresses

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

def _abb_replace(street: str) -> str:
    """
    Helper function to convert cardinal abbreviations.
    """
    street = re.sub(r'^e |^e. |e(?=[0-9])|e.(?=[0-9])', 'east ', street)
    street = re.sub(r'^w |^w. |w(?=[0-9])|w.(?=[0-9])', 'west ', street)
    street = re.sub(r'^n |^n. |n(?=[0-9])|n.(?=[0-9])', 'north ', street)
    street = re.sub(r'^s |^s. |s(?=[0-9])|s.(?=[0-9])', 'south ', street)

    return street

def _standardize_street(street: str) -> str:
    """
    Helper function to standardize street names.
    """
    for abb in list(ABB_DICT.keys()):
        full = ABB_DICT[abb]
        street = re.sub(f' {abb}$', f' {full}', street)
        street = re.sub(f' {abb}\.$', f' {full}', street)
        street = re.sub(f' {abb} ', f' {full} ', street)
        street = re.sub(f' {abb}\. ', f' {full} ', street)
    street = re.sub(r"'", '', street)
    street = re.sub(r'^b ', 'beach ', street)
    street = re.sub(r'^st ', 'saint ', street)
    street = re.sub(r'^st.', 'saint', street)
    street = re.sub(r'^mt|^mt.', 'mount', street)
    street = re.sub(r'^ft|^ft.', 'fort', street)
    street = re.sub(r'first', '1st', street)
    street = re.sub(r'second', '2nd', street)
    street = re.sub(r'third', '3rd', street)
    street = re.sub(r'fourth', '4th', street)
    street = re.sub(r'fifth', '5th', street)
    street = re.sub(r'sixth', '6th', street)
    street = re.sub(r'seventh', '7th', street)
    street = re.sub(r'eighth', '8th', street)
    street = re.sub(r'ninth', '9th', street)
    street = re.sub(r'tenth', '10th', street)
    street = re.sub(r'eleventh', '11th', street)
    street = re.sub(r'twelfth', '12th', street)

    return street

def clean_street(address: str) -> str:
    """
    Function to clean street strings.
    """
    address = address.lower()
    address = _standardize_street(address)
    address = _abb_replace(address)
    address = _ordinal_rep(address)
    if address in SPECIAL_CASES.keys(): # Special cases
        address = SPECIAL_CASES[address]

    return address

def _get_intersections(address: str) -> tuple | None:
    """
    Helper function to extract intersections from address.
    """
    null_streets = ['dead road', 'dead end']
    for s in null_streets:
        if s in address:
            return None
    
    intersections = address.split(' between ')
    if len(intersections) != 2:
        return None
    
    main_st = intersections[0]
    cross_sts = intersections[1].split(' and ')
    total_names = [main_st] + cross_sts
    if len(total_names) != 3:
        return None

    block_dict = {
        'main': clean_street(main_st),
        'cross_1': clean_street(cross_sts[0]),
        'cross_2': clean_street(cross_sts[1])
    }

    return block_dict

def _clean_datetime(date: str) -> datetime:
    """
    Helper function to covert datetime string to datetime object.
    """
    date = ' '.join(date.split('T'))
    date = date.split('.')[0]
    date_format = '%Y-%m-%d %H:%M:%S'
    date = datetime.strptime(date, date_format)
    
    return date


### Main Data Cleaning/DataFrame Creation Functions ###
def clean_data(row: dict) -> dict:
    """
    Function to clean film permit row.
    """
    eventid = row['eventid']
    addresses = _split_addresses(row['parkingheld'])
    addresses = [
        _get_intersections(address) for address in addresses
    ]

    startdate = _clean_datetime(row['startdatetime'])
    enddate = _clean_datetime(row['enddatetime'])
    enteredon = _clean_datetime(row['enteredon'])

    category = row['category']
    subcategory = row['subcategoryname']
    country = row['country']
    boro = row['borough']
    zipcode = row['zipcode_s']

    data_dict = {
        'id': eventid,
        'streets': addresses,
        'borough': boro,
        'zipcode': zipcode,
        'startdate': startdate,
        'enddate': enddate,
        'enteredon': enteredon,
        'category': category,
        'subcategory': subcategory,
        'origin': country
    }

    return data_dict

def create_film_df(film_permits: list) -> pd.DataFrame:
    """
    Function to convert list of film permits to DataFrame from wide-to-long film locations.
    """
    shoots = pd.DataFrame(film_permits)
    locs = pd.DataFrame(shoots['streets'].to_list(), index=shoots['id']).stack()
    locs = locs.reset_index().drop(columns='level_1')
    locs.columns = ['id', 'street_dict']
    df = locs.merge(shoots, how='left', on='id').drop(columns='streets')
    df['main_st'] = df['street_dict'].map(lambda x: x['main'])
    df['cross_st_1'] = df['street_dict'].map(lambda x: x['cross_1'])
    df['cross_st_2'] = df['street_dict'].map(lambda x: x['cross_2'])
    df.drop(columns='street_dict', inplace=True)
    df['zipcode'] = df['zipcode'].map(lambda x: x.split(', '))

    return df