from unicodedata import name
from click import style
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import plotly.express as px
import plotly.graph_objects as go

import geopandas as gpd
import pandas as pd
import shapely.geometry
import numpy as np
import datetime

import pickle

NYC_LAT_LONG = {'lon': -74.0060, 'lat': 40.7128}
FILM_PERMITS = 'film_df.p'
ZIP_CODES = 'zip_codes.p'
BORO_DICT = {
    'New York': 'Manhattan',
    'Kings': 'Brooklyn',
    'Queens': 'Queens',
    'Bronx': 'Bronx',
    'Richmond': 'Staten Island'
}

external_stylesheets = ['https://taniarascia.github.io/primitive/css/main.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

with open(FILM_PERMITS, 'rb') as f:
    df = gpd.GeoDataFrame(pickle.load(f))

with open(ZIP_CODES, 'rb') as f:
    zip_codes = gpd.GeoDataFrame(pickle.load(f))

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
        id='container-figures',
        type='default',
        children=[
            dcc.Graph(id='film-map')
        ]
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
    if startdate > enddate:
        return default_map_fig

    startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()

    filtered_df = df.loc[(df['startdate'] >= startdate) & (df['enddate'] <= enddate)].copy()
    filtered_df['parking_held'] = filtered_df.apply(
        lambda x: x['main_st'].upper() + ' between ' + x['cross_st_1'].upper() + ' and ' + x['cross_st_2'].upper(), axis=1
    )

    temp = pd.DataFrame(filtered_df['zipcode'].to_list(), index=filtered_df['id']).stack().reset_index()
    temp.drop(columns='level_1', inplace=True)
    temp.columns = ['permit_id', 'zip_code']
    temp = temp.groupby('zip_code')['permit_id'].unique().reset_index()
    temp['permit_count'] = temp['permit_id'].map(lambda x: len(x))
    temp = temp[['zip_code', 'permit_count']]

    counts = zip_codes.merge(temp, left_on='zipcode', right_on='zip_code', how='left')
    counts = counts[['zipcode', 'permit_count', 'geometry']]
    counts['permit_count'] = counts['permit_count'].fillna(0)
    counts['permit_count'] = counts['permit_count'].astype('int')
    counts.set_index('zipcode', inplace=True)

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

    fig = px.choropleth_mapbox(
        counts,
        geojson=counts['geometry'],
        locations=counts.index,
        color='permit_count',
        custom_data=['permit_count'],
        title=f'Data Range: {startdate} - {enddate}',
        opacity=0.1,
        mapbox_style='carto-positron',
        center=NYC_LAT_LONG,
        zoom=10,
        height=800,
        width=800
    )
    fig.update_traces(
        hovertemplate='<b>Zip Code:</b> %{location}<br><b>Permit Count:</b> %{customdata[0]}'
    )
    
    fig.add_trace(scatter)

    # fig.update_layout(
    #     title=f'Data Range: {startdate} - {enddate}',
    #     mapbox={
    #         'style': 'carto-positron',
    #         'center': NYC_LAT_LONG,
    #         'zoom': 10
    #     },
    #     height=900,
    #     width=1000
    # )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
