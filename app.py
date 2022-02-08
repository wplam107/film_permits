from unicodedata import name
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

# import plotly.express as px
import plotly.graph_objects as go

import geopandas as gpd
import pandas as pd
import shapely.geometry
import numpy as np
import datetime

import pickle

NYC_LAT_LONG = {'lon': -74.0060, 'lat': 40.7128}

app = dash.Dash(__name__)

with open('film_df.p', 'rb') as f:
    df = gpd.GeoDataFrame(pickle.load(f))

df['startdate'] = pd.to_datetime(df['startdate']).dt.date
df['enddate'] = pd.to_datetime(df['enddate']).dt.date
df['enteredon'] = pd.to_datetime(df['enteredon']).dt.date

default_map_fig = go.Figure(go.Scattermapbox(
    lat=[None],
    lon=[None],
    name='Enter date range',
))

default_map_fig.update_layout(
    mapbox={
        'style': 'carto-positron',
        'center': NYC_LAT_LONG,
        'zoom': 10
    },
    height=900,
    width=1000
)

app.layout = html.Div(children=[
    html.H1(children='NYC Film Shoots'),

    html.Div(children='''
        Map of blocks shutdown for NYC film shoots
    '''),

    html.Div([
        dcc.DatePickerRange(
            id='date-picker',
            min_date_allowed=df['startdate'].min(),
            max_date_allowed=df['enddate'].max(),
            initial_visible_month=df['startdate'].min()
        )
    ]),

    dcc.Loading(
        id='container-map',
        type='default',
        children=dcc.Graph(
            id='film-map'
        )
    )
])

@app.callback(
    Output('film-map', 'figure'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def fig_by_date(startdate: datetime.date, enddate: datetime.date):

    if (startdate == None) or (enddate == None):
        return default_map_fig

    startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()

    filtered_df = df.loc[(df['startdate'] >= startdate) & (df['enddate'] <= enddate)].copy()
    filtered_df['parking_held'] = filtered_df.apply(
        lambda x: x['main_st'].upper() + ' between ' + x['cross_st_1'].upper() + ' and ' + x['cross_st_2'].upper(), axis=1
    )

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
        filtered_df['id'],
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

    fig = go.Figure(go.Scattermapbox(
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
    ))

    fig.update_layout(
        title=f'Data Range: {startdate} - {enddate}',
        mapbox={
            'style': 'carto-positron',
            'center': NYC_LAT_LONG,
            'zoom': 10
        },
        height=900,
        width=1000
    )

    # fig.update_traces(hover_template='Permit ID: %{}')

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
