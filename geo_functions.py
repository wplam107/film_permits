import numpy as np
import geopandas as gpd
from shapely.geometry.linestring import LineString
from shapely.geometry.multilinestring import MultiLineString
from shapely.geometry.point import Point

import plotly.express as px

def clean_county_str(county_str: str) -> list[str]:
    """
    Function to clean a string of counties to a list of counties.
    """
    county_str_list = county_str.split(';')
    counties = [ s.split(',')[0] for s in county_str_list ]

    return counties

def get_street_linestrings(
    df: gpd.GeoDataFrame,
    street: str,
    boro: str,
    boro_df: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """
    Function to get GeoSeries geometry of street.
    """
    df = df.loc[df['name'] == street]
    temp = df.loc[df['boros'].map(lambda x: boro in x)]
    if len(temp) < 1:
        temp = df.loc[df['boros'].map(lambda x: 'Missing' in x)].reset_index()
        if len(temp) > 0:
            geo = boro_df.loc[boro_df['BoroName'] == boro][0]
            return geo
        else:
            return gpd.GeoSeries([])
    else:
        geo = temp['geometry']
        return geo

def get_intersec_coords(
    street_1: LineString | MultiLineString,
    street_2: LineString | MultiLineString) -> Point:
    pass

def plot_street(df: gpd.GeoDataFrame, street: str, boro: str, boro_df: gpd.GeoDataFrame):
    """
    Function to plot a singular street.
    """
    df = df.loc[df['name'] == street]
    temp = df.loc[df['boros'].map(lambda x: boro in x)]
    if len(temp) < 1:
        temp = df.loc[df['boros'].map(lambda x: 'Missing' in x)].reset_index()
        if len(temp) > 0:
            boro_df = boro_df.loc[boro_df['BoroName'] == boro].reset_index()
            temp = boro_df['geometry'].intersection(temp['geometry']).reset_index().drop(columns='index')
            temp.columns = ['geometry']
            temp['name'] = street
            
    lats = []
    lons = []
    names = []

    for feature, name in zip(temp['geometry'], temp['name']):
        if isinstance(feature, LineString):
            linestrings = [feature]
        elif isinstance(feature, MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            names = np.append(names, [name]*len(y))
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            names = np.append(names, None)

    fig = px.line_mapbox(
        lat=lats,
        lon=lons,
        hover_name=names,
        mapbox_style='carto-positron', 
        center={'lat':40.7128, 'lon':-74.006},
        zoom=9,
        height=750,
        width=750
    )

    fig.show()