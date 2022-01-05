from typing import Iterable
import pandas as pd
import geopandas as gpd
import time
import pickle

import configparser
from sodapy import Socrata
from geopy.geocoders import MapBox

DATASET = 'tg4x-b46p'
CONFIG_FILE = 'configs.ini'
PERMIT_TYPE = 'Shooting Permit'
FIRST_DAY = '2018-01-01'

def get_geo_df(file_path: str) -> gpd.GeoDataFrame:
    """
    Function to retrieve GeoJSON file
    """
    zipcodes = gpd.read_file(file_path)
    return zipcodes

def get_permit_data(limit: int = 100000) -> list:
    """
    Function to retrieve film permit data from Socrata, retrieves by most recent first
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    app_token = config['socrata']['APP_TOKEN']
    client = Socrata("data.cityofnewyork.us", app_token=app_token)
    results = client.get(
        DATASET,
        where=f"eventtype = '{PERMIT_TYPE}' and startdatetime >= '{FIRST_DAY}'",
        order="startdatetime DESC",
        limit=limit
    )
    return results


def get_batch_geocoding(intersections: list[str]) -> dict:
    """
    Function to retrieve batch [longitude, latitude] coordinates.
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    api_key = config['mapbox']['API_KEY']
    length = len(intersections)
    locations = {}
    if length > 600: # MapBox API limit 600 requests / min
        i = 0
        for loc in intersections:
            time.sleep(0.2)
            i += 1
            try:
                intersection = f'{loc[0]} and {loc[1]}, {loc[2]}, New York'
                encoder = MapBox(api_key)
                location = encoder.geocode(intersection, country='us')
                longitude = location.longitude
                latitude = location.latitude
                outofbounds = (longitude > -72) or (longitude < -76) or (latitude > 42) or (latitude < 39)
                if outofbounds:
                    time.sleep(0.3)
                    intersection = f'{loc[1]} and {loc[0]}, {loc[2]}, New York'
                    location = encoder.geocode(intersection, country='us')
                    longitude = location.longitude
                    latitude = location.latitude
                    outofbounds = (longitude > -72) or (longitude < -76) or (latitude > 42) or (latitude < 39)
                    if outofbounds:
                        locations[loc] = None
                    else:
                        locations[loc] = [longitude, latitude]
                else:
                    locations[loc] = [longitude, latitude]
            except Exception as e:
                locations[loc] = e

            if i % 600 == 0:
                with open('temp.p', 'wb') as f:
                    pickle.dump(locations, f)
    
    return locations
