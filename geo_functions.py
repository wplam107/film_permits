import numpy as np
import geopandas as gpd
import shapely.ops
from shapely.geometry import GeometryCollection
from shapely.geometry import LineString
from shapely.geometry import MultiLineString
from shapely.geometry import Point
from shapely.geometry import MultiPoint

import plotly.express as px

BORO_DICT = {
    'New York': 'Manhattan',
    'Kings': 'Brooklyn',
    'Queens': 'Queens',
    'Bronx': 'Bronx',
    'Richmond': 'Staten Island'
}

def seg_in_zipcode(geo: LineString | MultiLineString, ref_df: gpd.GeoDataFrame) -> list:
    """
    Function to return list of zip codes of a street.
    """
    temp = ref_df.copy()
    temp['contains'] = temp['geometry'].map(lambda x: x.intersects(geo))
    
    return list(temp.loc[temp['contains'] == True]['zipcode'])

def match_street_geo(
    street: str,
    zipcodes: list,
    ref_df: gpd.GeoDataFrame) -> LineString | MultiLineString:
    """
    Function to match geometry to street name.
    """
    temp = ref_df.query(f'street == "{street}"')
    if len(temp) == 1:
        if isinstance(temp.iloc[0]['geometry'], LineString):
            return MultiLineString([temp.iloc[0]['geometry']]).geoms
        else:
            return temp.iloc[0]['geometry'].geoms
    elif len(temp) == 0:
        return None
    else:
        for zc in list(temp['zipcode']):
            if zc in zipcodes:
                temp = temp.query(f'zipcode == "{zc}"')
                if isinstance(temp.iloc[0]['geometry'], LineString):
                    return MultiLineString([temp.iloc[0]['geometry']]).geoms
                else:
                    return temp.iloc[0]['geometry'].geoms
        return None

def get_held_geometry(row) -> GeometryCollection:
    """
    Function to get geometry of parking held.
    """
    # Streets intersections
    ms = MultiLineString(row['ms_geom'])
    cs1 = MultiLineString(row['cs1_geom'])
    cs2 = MultiLineString(row['cs2_geom'])

    # is_int_1 = ms.intersects(cs1)
    # is_int_2 = ms.intersects(cs2)

    # Improvements need to be made
    # Add segment if streets do not intersect
    # if is_int_1 == False:
    #     nms = MultiLineString([*ms.geoms, LineString(shapely.ops.nearest_points(ms, cs1))])
    #     ncs1 = MultiLineString([*cs1.geoms, LineString(shapely.ops.nearest_points(ms, cs1))])
    #     ms = nms
    #     cs1 = ncs1
    # if is_int_2 == False:
    #     nms = MultiLineString([*ms.geoms, LineString(shapely.ops.nearest_points(ms, cs2))])
    #     ncs2 = MultiLineString([*cs2.geoms, LineString(shapely.ops.nearest_points(ms, cs2))])
    #     ms = nms
    #     cs2 = ncs2

    # Get intersection points
    intersect_1 = ms.intersection(cs1)
    intersect_2 = ms.intersection(cs2)
    if isinstance(intersect_1, MultiPoint):
        intersect_1 = intersect_1.geoms[0]
    if isinstance(intersect_2, MultiPoint):
        intersect_2 = intersect_2.geoms[0]
    if isinstance(intersect_1, LineString | MultiLineString | GeometryCollection):
        intersect_1 = intersect_1.representative_point()
    if isinstance(intersect_2, LineString | MultiLineString | GeometryCollection):
        intersect_2 = intersect_2.representative_point()


    # Find center point between intersections and draw center circle
    try:
        x1 = intersect_1.x
        x2 = intersect_2.x
        y1 = intersect_1.y
        y2 = intersect_2.y
        x = (x1 + x2) / 2
        y = (y1 + y2) / 2
        center = Point(x, y)
        buffer = center.distance(intersect_1)
        circle = center.buffer(buffer)
    except:
        return None

    result = circle.intersection(ms)

    return result

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