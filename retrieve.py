import pandas as pd
import geopandas as gpd

import configparser
from sodapy import Socrata

GEOJSON = './temp/zipcodes.json'
DATASET = 'tg4x-b46p'
CONFIG_FILE = 'configs.ini'

def get_geojson() -> gpd.GeoDataFrame:
    '''
    Helper function to retrieve GeoJSON file
    '''
    zipcodes = gpd.read_file(GEOJSON)
    return zipcodes

def get_permit_data(limit: int) -> list:
    '''
    Function to retrieve film permit data from Socrata, retrieves by most recent first
    '''
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    app_token = config['socrata']['APP_TOKEN']
    client = Socrata("data.cityofnewyork.us", app_token=app_token)
    results = client.get(DATASET, where="eventtype = 'Shooting Permit'", order="startdatetime DESC", limit=limit)
    return results