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
df['main_st'] = df['main_st'].map(lambda x: x.upper())
df['cross_st_1'] = df['cross_st_1'].map(lambda x: x.upper())
df['cross_st_2'] = df['cross_st_2'].map(lambda x: x.upper())
df.rename(columns={'id': 'id_'}, inplace=True)
df = gpd.GeoDataFrame(df[[
    'id_', 'zipcode', 'startdate', 'enddate', 'category', 'subcategory', 'origin', 'main_st', 'cross_st_1', 'cross_st_2', 'geometry'
]])

origin_options = ['ALL', *df['origin'].unique()]
category_options = ['ALL', *df['category'].unique()]
calender_options = [ i for i in range(df['startdate'].min().year, df['enddate'].max().year + 1) ]

app.layout = html.Div(children=[
    html.H1(children='NYC Film Shoots', style={'textAlign': 'center'}),

    dcc.Store(id='filtered-shoots-store'),
    dcc.Store(id='zipcode-shoots-store'),
    dcc.Store(id='filter-args-store'),

    html.Div(
        children=[
            html.Div(
                children=[
                    'Select Date: (large ranges = long load times)',
                    html.Br(),
                    dcc.DatePickerRange(
                        id='date-picker',
                        min_date_allowed=df['startdate'].min(),
                        max_date_allowed=df['enddate'].max(),
                        initial_visible_month=df['enddate'].max(),
                        number_of_months_shown=3,
                        updatemode='bothdates'
                    )
                ],
                style={'textAlign': 'center'}
            ),
            html.Div(
                children=[
                    html.Div('Select Filters', style={'textAlign': 'center'}),
                    dcc.Dropdown(
                        id='origin-picker',
                        options=origin_options,
                        placeholder='Select Country of Origin',
                        style={'width': '50%', 'margin': 'auto'},
                    ),
                    dcc.Dropdown(
                        id='category-picker',
                        options=category_options,
                        placeholder='Select Category',
                        style={'width': '50%', 'margin': 'auto'},
                    ),
                    dcc.Dropdown(
                        id='subcategory-picker',
                        placeholder='Select Subcategory',
                        style={'width': '50%', 'margin': 'auto'},
                    )
                ]
            )
        ]
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
    Output('filtered-shoots-store', 'data'),
    Output('zipcode-shoots-store', 'data'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
    Input('origin-picker', 'value'),
    Input('category-picker', 'value'),
    Input('subcategory-picker', 'value')
)
def pick_dates(startdate: str, enddate: str, origin: str, category: str, subcat: str):
    if (startdate == None) or (enddate == None):
        return (None, None)

    startdate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    enddate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()

    filtered_df = df.loc[(df['startdate'] <= enddate) & (df['enddate'] >= startdate)].copy()
    if (origin != None) and (origin != 'ALL'):
        filtered_df = filtered_df.loc[filtered_df['origin'] == origin]
    if (category != None) and (category != 'ALL'):
        filtered_df = filtered_df.loc[filtered_df['category'] == category]
    if (subcat != None) and (subcat != 'ALL'):
        filtered_df = filtered_df.loc[filtered_df['subcategory'] == subcat]

    if len(filtered_df) == 0:
        return (None, None)

    temp = pd.DataFrame(filtered_df['zipcode'].to_list(), index=filtered_df['id_']).stack().reset_index()
    temp.drop(columns='level_1', inplace=True)
    temp.columns = ['permit_id', 'zip_code']
    temp['zip_code'] = temp['zip_code'].map(lambda x: str(x))
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

@app.callback(
    Output('subcategory-picker', 'options'),
    Input('category-picker', 'value')
)
def update_subcategories(category: str):
    options = df.loc[df['category'] == category]['subcategory'].unique()

    return ['ALL', *options]

if __name__ == '__main__':
    # Prod
    app.run_server()

    # Dev
    # app.run_server(debug=True)
