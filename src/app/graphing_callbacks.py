from dash import Input, Output
from dash import callback

import plotly.express as px
import plotly.graph_objects as go

import geopandas as gpd
import pandas as pd
import shapely.geometry
import numpy as np
import json


NYC_LAT_LONG = {'lon': -74.0060, 'lat': 40.7128}

default_map_fig = go.Figure(go.Scattermapbox(
    lat=[None],
    lon=[None]
))
default_map_fig.update_layout(
    mapbox={
        'style': 'carto-positron',
        'center': NYC_LAT_LONG,
        'zoom': 10
    },
    title={
        'text': 'Map of Blocks with Film Shoots',
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'
    }
)

default_bar_fig = go.Figure(px.bar())
default_bar_fig.update_layout(
    title={
        'text': 'Top Zip Codes',
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'
    },
    margin={
        't': 100
    },
    yaxis_title='Permit Counts',
    xaxis_title='Zip Code'
)
default_bar_fig.update_yaxes(showticklabels=False)
default_bar_fig.update_xaxes(showticklabels=False)

@callback(
    Output('film-map', 'figure'),
    Input('filtered-shoots', 'data'),
    Input('zipcode-shoots', 'data')
)
def fig_by_date(filtered_json, zipcode_json):
    if filtered_json == None:
        return default_map_fig

    j = json.loads(filtered_json)
    filtered_df = gpd.GeoDataFrame.from_features(j)
    filtered_df['startdate'] = pd.to_datetime(filtered_df['startdate']).dt.date
    filtered_df['enddate'] = pd.to_datetime(filtered_df['enddate']).dt.date

    c = json.loads(zipcode_json)
    counts = gpd.GeoDataFrame.from_features(c)

    lats = []
    lons = []
    ids = []
    cats = []
    subcats = []
    countries = []
    sdates = []
    edates = []
    phs = []

    data = zip(
        filtered_df['geometry'],
        filtered_df['id_'],
        filtered_df['category'],
        filtered_df['subcategory'],
        filtered_df['origin'],
        filtered_df['startdate'],
        filtered_df['enddate'],
        filtered_df['parking_held']
    )

    for feature, id_, cat, subcat, country, sdate, edate, ph in data:
        if isinstance(feature, shapely.geometry.linestring.LineString):
            linestrings = [feature]
        elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            ids = np.append(ids, [id_]*len(y))
            cats = np.append(cats, [cat]*len(y))
            subcats = np.append(subcats, [subcat]*len(y))
            countries = np.append(countries, [country]*len(y))
            sdates = np.append(sdates, [sdate]*len(y))
            edates = np.append(edates, [edate]*len(y))
            phs = np.append(phs, [ph]*len(y))
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            ids = np.append(ids, None)
            cats = np.append(cats, None)
            subcats = np.append(subcats, None)
            countries = np.append(countries, None)
            sdates = np.append(sdates, None)
            edates = np.append(edates, None)
            phs = np.append(phs, None)

    scatter = go.Scattermapbox(
        mode='lines',
        lat=lats,
        lon=lons,
        customdata=np.stack((ids, cats, subcats, countries, sdates, edates, phs), axis=-1),
        hovertemplate='<br>'.join([
            '<b>Permit ID:</b> %{customdata[0]}',
            '<b>Category:</b> %{customdata[1]}',
            '<b>Subcategory:</b> %{customdata[2]}',
            '<b>Country:</b> %{customdata[3]}',
            '<b>Start Date:</b> %{customdata[4]}',
            '<b>End Date:</b> %{customdata[5]}',
            '<b>Parking Held:</b> %{customdata[6]}'
        ]),
        name=''
    )

    fig = go.Figure(px.choropleth_mapbox(
        counts,
        geojson=counts['geometry'],
        locations=counts.index,
        color='permit_count',
        custom_data=['zipcode', 'permit_count'],
        title='Map of Blocks with Film Shoots',
        opacity=0.1,
        mapbox_style='carto-positron',
        center=NYC_LAT_LONG,
        zoom=10
    ))
    fig.update_traces(
        hovertemplate='<b>Zip Code:</b> %{customdata[0]}<br><b>Permit Count:</b> %{customdata[1]}'
    )
    fig.add_trace(scatter)
    fig.update_layout(
        coloraxis_showscale=False,
        title={
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )

    return fig

@callback(
    Output('zipcode-bar', 'figure'),
    Input('zipcode-shoots', 'data')
)
def top_ten_zc(zipcode_json):
    if zipcode_json == None:
        return default_bar_fig

    c = json.loads(zipcode_json)
    counts = gpd.GeoDataFrame.from_features(c)
    counts.sort_values('permit_count', ascending=False, inplace=True)
    counts = counts.iloc[:10]

    fig = go.Figure(px.bar(data_frame=counts, x='zipcode', y='permit_count', labels={'permit_count': 'Permit Count', 'zipcode': 'Zip Code'}))
    fig.update_layout(
        title={
            'text': 'Top Zip Codes',
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        margin={
            't': 100
        },
        yaxis_title='Permit Counts',
        xaxis_title='Zip Code'
    )
    fig.update_traces(
        hovertemplate='<b>Zip Code:</b> %{x}<br><b>Permit Count:</b> %{y}'
    )

    return fig