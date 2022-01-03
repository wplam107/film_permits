import numpy as np
import pandas as pd
import geopandas as gpd

def events_to_zipcode(data_frame: pd.DataFrame) -> pd.DataFrame:
    """
    Function to clean Socrata results and convert list of zipcodes by permit to separate rows
    """

    data_frame['zipcode'] = data_frame['zipcode_s'].map(lambda x: x.split(', '))
    data_frame.drop(columns='zipcode_s', inplace=True)

    temp = data_frame[['eventid', 'zipcode']]
    temp = pd.DataFrame(temp['zipcode'].to_list(), index=temp['eventid']).stack()
    temp = temp.reset_index()
    temp.drop(columns='level_1', inplace=True)
    temp.rename(columns={0: 'zipcode'}, inplace=True)

    data_frame = temp.merge(data_frame, on='eventid')

    columns_to_drop = ['zipcode_y', 'eventagency', 'eventtype', 'communityboard_s', 'policeprecinct_s', 'borough']
    data_frame.drop(columns=columns_to_drop, inplace=True)
    data_frame.rename(columns={'zipcode_x': 'zipcode'}, inplace=True)

    data_frame['zipcode'] = np.where(data_frame['zipcode'] == '0', np.nan, data_frame['zipcode'])
    data_frame['zipcode'] = np.where(data_frame['zipcode'] == 'N/A', np.nan, data_frame['zipcode'])
    data_frame.dropna(axis=0, inplace=True)

    return data_frame

