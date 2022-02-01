import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import plotly.express as px

import geopandas as gpd
import pandas as pd
import shapely.geometry
import numpy as np
import datetime

import pickle

NYC_LAT_LONG = {'lon': -74.0060, 'lat': 40.7128}

app = dash.Dash(__name__)

with open('data.p', 'rb') as f:
    df = gpd.GeoDataFrame(pickle.load(f))

df['startdate'] = pd.to_datetime(df['startdate']).dt.date
df['enddate'] = pd.to_datetime(df['enddate']).dt.date
df['enteredon'] = pd.to_datetime(df['enteredon']).dt.date

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    html.Div([
        dcc.DatePickerRange(
            id='date-picker',
            start_date=df['startdate'].min(),
            end_date=df['enddate'].max(),
            initial_visible_month=df['startdate'].min()
        )
    ]),

    dcc.Graph(
        id='film-map'
    )
])

@app.callback(
    Output('film-map', 'figure'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def fig_by_date(startdate: datetime.date, enddate: datetime.date):
    lats = []
    lons = []
    data = []

    startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()

    temp = df.loc[(df['startdate'] >= startdate) & (df['enddate'] <= enddate)].copy()
    temp['hoverdata'] = temp.apply(
        lambda x: f"ID: {x['id']}, Production Origin: {x['origin']}, Category: {x['category']}, Subcategory: {x['subcategory']}",
        axis=1
    )

    for feature, datum in zip(temp['geometry'], temp['hoverdata']):
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
            data = np.append(data, [datum]*len(y))
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            data = np.append(data, None)

    fig = px.line_mapbox(
        lat=lats,
        lon=lons,
        text=data,
        mapbox_style="carto-positron",
        center=NYC_LAT_LONG,
        height=900,
        width=1000,
        zoom=10)

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
