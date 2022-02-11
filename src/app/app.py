from dash import Dash, dcc, html, Input, Output

import geopandas as gpd
import pandas as pd
import datetime
import json
import pickle

import graphing_callbacks

FILM_PERMITS = './data/film_df.p'
ZIP_CODES = './data/zip_codes.p'
BORO_DICT = {
    'New York': 'Manhattan',
    'Kings': 'Brooklyn',
    'Queens': 'Queens',
    'Bronx': 'Bronx',
    'Richmond': 'Staten Island'
}

external_stylesheets = ['https://taniarascia.github.io/primitive/css/main.css']
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
server = app.server

with open(FILM_PERMITS, 'rb') as f:
    df = gpd.GeoDataFrame(pickle.load(f))

with open(ZIP_CODES, 'rb') as f:
    zip_codes = gpd.GeoDataFrame(pickle.load(f))

df['startdate'] = pd.to_datetime(df['startdate']).dt.date
df['enddate'] = pd.to_datetime(df['enddate']).dt.date
df['enteredon'] = pd.to_datetime(df['enteredon']).dt.date
df.rename(columns={'id': 'id_'}, inplace=True)
df = gpd.GeoDataFrame(df[[
    'id_', 'zipcode', 'startdate', 'enddate', 'category', 'subcategory', 'origin', 'main_st', 'cross_st_1', 'cross_st_2', 'geometry'
]])

app.layout = html.Div(children=[
    html.H1(children='NYC Film Shoots', style={'textAlign': 'center'}),

    dcc.Store(id='filtered-shoots'),
    dcc.Store(id='zipcode-shoots'),

    html.Div(
        children=[
            'Select Date',
            html.Br(),
            dcc.DatePickerRange(
                id='date-picker',
                min_date_allowed=df['startdate'].min(),
                max_date_allowed=df['enddate'].max(),
                initial_visible_month=df['startdate'].min()
            )
        ],
        style={'textAlign': 'center'}
    ),

    dcc.Loading(
        type='default',
        children=html.Div(
            id='container-figures',
            className='row',
            children=html.Div(
                children=[
                    html.Div(
                        id='container-map',
                        children=html.Div(dcc.Graph(
                            id='film-map',
                            style={'height': '80vh', 'width': '80vh'},
                            config={'displayModeBar': False}
                        )),
                        className='six columns',
                        style={'display': 'inline-block'}
                    ),
                    html.Div(
                        id='container-bar',
                        children=html.Div(dcc.Graph(
                            id='zipcode-bar',
                            style={'height': '80vh', 'width': '80vh'},
                            config={'displayModeBar': False}
                        )),
                        className='six columns',
                        style={'display': 'inline-block'}
                    )
                ]
            ),
            style={'justify-content': 'center', 'align-items': 'center', 'display': 'flex'}
        )
    )
])

@app.callback(
    [Output('filtered-shoots', 'data'), Output('zipcode-shoots', 'data')],
    [Input('date-picker', 'start_date'), Input('date-picker', 'end_date')]
)
def pick_dates(startdate: datetime.date, enddate: datetime.date):
    if (startdate == None) or (enddate == None):
        return (None, None)
    if startdate > enddate:
        return (None, None)

    startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()

    filtered_df = df.loc[(df['startdate'] >= startdate) & (df['enddate'] <= enddate)].copy()
    filtered_df['parking_held'] = filtered_df.apply(
        lambda x: x['main_st'].upper() + ' between ' + x['cross_st_1'].upper() + ' and ' + x['cross_st_2'].upper(), axis=1
    )

    temp = pd.DataFrame(filtered_df['zipcode'].to_list(), index=filtered_df['id_']).stack().reset_index()
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
    counts['zipcode'] = counts.index

    filtered_df['startdate'] = pd.to_datetime(filtered_df['startdate']).dt.strftime('%Y-%m-%d')
    filtered_df['enddate'] = pd.to_datetime(filtered_df['enddate']).dt.strftime('%Y-%m-%d')

    # __geo_interface__ is GeoJSON as str
    return json.dumps(filtered_df.__geo_interface__), json.dumps(counts.__geo_interface__)

if __name__ == '__main__':
    app.run_server(debug=True)
