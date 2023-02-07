import os
from os.path import dirname, abspath, join
import pandas as pd
import numpy as np
from flask import Blueprint
from flask.wrappers import Response
from src.app import mongo_client
from bson import json_util
from flask import request, jsonify
from src.app.services.geo_services import pointNamer

ctd = Blueprint("ctd", __name__, url_prefix="/ctd")

ROOTPATH = dirname(dirname(dirname(dirname(abspath(__file__)))))
DATAPATH = join(ROOTPATH, 'data_ctd')
PROCESSED_XLSX_DATAPATH = join(ROOTPATH, 'ctd_processed_xlsx')
PROCESSED_CSV_DATAPATH = join(ROOTPATH, 'ctd_processed_csv')

@ctd.route("/process", methods=['GET'])
def process_ctd_data():
    """------------------------------------------------------------
    FUNCTION 
    ---------------------------------------------------------------
    1. Create and save .xlsx and .csv dataframes from CTD sensor 
       measurements;
    2. Convert the coordinates from each measurement to names given 
       in the fotoagua project;
    3. Create one dataframe per parameter.
    ---------------------------------------------------------------
    RETURN
    ---------------------------------------------------------------
    JSON, status; {'msg': str}, int
            
    """
    target_cols = ['Temperature (Celsius)', 'Pressure (Decibar)', 
                   'Conductivity (MicroSiemens per Centimeter)', 
                   'Specific conductance (MicroSiemens per Centimeter)', 
                   'Salinity (Practical Salinity Scale)', 
                   'Sound velocity (Meters per Second)', 
                   'Density (Kilograms per Cubic Meter)']
    try:
        for col in target_cols:
            fdates = set([])
            dfs_dict = {}
            coord_dfs = {}
            for f in os.listdir(DATAPATH):
                fdate = f.split('_')[1]
                fdates.add(fdate)
            for date in fdates:
                temp_profiles_df = pd.DataFrame(columns=['Depth (Meter)'])
                point_names = []
                lat_info = []
                lon_info = []
                for ff in os.listdir(DATAPATH):
                    fdate = ff.split('_')[1]
                    if date == fdate:
                        lat = None
                        lon = None
                        for line in open(f'{DATAPATH}/{ff}', 'r'):
                            split_comma = line.split(',')
                            if split_comma[0] == '% Start latitude':
                                lat = float(split_comma[1][:-2])
                            if split_comma[0] == '% Start longitude':
                                lon = float(split_comma[1][:-2])
                            
                        lat_info.append(lat)
                        lon_info.append(lon)
                        point_name = pointNamer(lat, lon)
                        point_names.append(point_name)

                point_names_np = np.array(point_names)
                for pt in point_names:

                    times_repeat = len(point_names_np[point_names_np == pt])
                    if times_repeat >= 2:

                        pt_indexes = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j')
                        counter = 0
                        for i in range(len(point_names)):
                            if pt == point_names[i]:
                                point_names[i] = f'{pt}_{pt_indexes[counter]}'
                                counter+=1
                                
                counter2 = 0
                for ff in os.listdir(DATAPATH):
                    fdate = ff.split('_')[1]
                    if date == fdate:
                    
                        fpath = DATAPATH + '/' + ff
                        if os.path.isfile(fpath):
                            df = pd.read_csv(fpath, skiprows=28, index_col=False)
                            target_df = df[['Depth (Meter)', col]]
                            target_df.columns = ['Depth (Meter)', f'{point_names[counter2]}']
                            target_df['Depth (Meter)'] = np.round(target_df['Depth (Meter)'], 1)
                            temp_profiles_df =  temp_profiles_df.merge(target_df, how='outer', on='Depth (Meter)', sort=True)
                            temp_profiles_df.set_index('Depth (Meter)',drop=True, inplace=True, verify_integrity=True)
                            counter2 += 1
                    
                if len(point_names) > 0:
                    cols_sorted = sorted(point_names)
                    temp_profiles_df = temp_profiles_df[cols_sorted]
                    dfs_dict[date] = temp_profiles_df
                    coord_dfs[date] = {'site': point_names, 'lat': lat_info, 'lon': lon_info}

            for key, value in dfs_dict.items():

                file_first_name = col.split(' (')[0]
                xlsx_fname = f'{file_first_name}_{key}.xlsx'
                coords_xls_fname = f'coords_info_{key}.xlsx'
                csv_fname = f'{file_first_name}_{key}.csv'
                coords_csv_fname = f'coords_info_{key}.csv'

                final_df_xlsx_path = join(PROCESSED_XLSX_DATAPATH, xlsx_fname)
                coords_xlsx_df_path = join(PROCESSED_XLSX_DATAPATH, coords_xls_fname)
                final_df_csv_path = join(PROCESSED_CSV_DATAPATH, csv_fname)
                coords_df_csv_path = join(PROCESSED_CSV_DATAPATH, coords_csv_fname)
                
                with pd.ExcelWriter(final_df_xlsx_path) as writer:
                    value.to_excel(writer, sheet_name='Data')
                    coords_df = pd.DataFrame(coord_dfs[key])
                    coords_df.to_excel(writer, sheet_name='coords_info')
                
                value.to_csv(final_df_csv_path)

                if col == 'Temperature (Celsius)':
                    coords_df = pd.DataFrame(coord_dfs[key])
                    with pd.ExcelWriter(coords_xlsx_df_path) as writer2:
                        coords_df.to_excel(writer2, sheet_name='coords_info')

                    coords_df.to_csv(coords_df_csv_path)

        return jsonify({'msg': 'success'}), 200
    
    except Exception as e:
        print(e)
        return jsonify({'error': e}), 500

@ctd.route("/temperature", methods=['GET'])
def temperature_ctd_data():
    try:
        for f in os.listdir(PROCESSED_CSV_DATAPATH):
            if f.split('_')[0] == 'Temperature':
                maindf = pd.read_csv(f'{PROCESSED_CSV_DATAPATH}/{f}')
                maindf_cols = maindf.columns.values.tolist()
                


        return jsonify({'msg': 'temp success'}), 200
    
    except Exception as e:
        print(e)
        return jsonify({'error': e}), 500