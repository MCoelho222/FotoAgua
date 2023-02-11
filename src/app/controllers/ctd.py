import os
from os.path import dirname, abspath, join
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from flask import Blueprint
from flask.wrappers import Response
from src.app import mongo_client
from bson import json_util
from flask import request, jsonify
from src.app.services.geo_services import pointNamer
from src.app.services.plot_services import nrows_ncols_for_subplots

ctd = Blueprint("ctd", __name__, url_prefix="/ctd")

ROOTPATH = dirname(dirname(dirname(dirname(abspath(__file__)))))
DATAPATH = join(ROOTPATH, 'data_ctd')
PROCESSED_XLSX_DATAPATH = join(ROOTPATH, 'ctd_processed_xlsx')
PROCESSED_CSV_DATAPATH = join(ROOTPATH, 'ctd_processed_csv')

target_cols = ['Temperature (Celsius)', 'Pressure (Decibar)', 
               'Conductivity (MicroSiemens per Centimeter)', 
               'Specific conductance (MicroSiemens per Centimeter)', 
               'Salinity (Practical Salinity Scale)', 
               'Sound velocity (Meters per Second)', 
               'Density (Kilograms per Cubic Meter)']

sites = ['L1', 'L2', 'L3', 'LR', 'PV1', 'PV6', 'PV7', 'NEAR_UP']

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
    

@ctd.route("/populatedb", methods=['GET'])
def populate_db():
    """------------------------------------------------------------
    FUNCTION 
    ---------------------------------------------------------------
    1. Save ctd data into mongoAtlasDB;
    2. Convert the coordinates from each measurement to names given 
       in the fotoagua project;
    3. Create one dataframe per parameter.
    ---------------------------------------------------------------
    RETURN
    ---------------------------------------------------------------
    JSON, status; {'msg': str}, int
            
    """
    fdates = set([])
    try:

        for f in os.listdir(DATAPATH):
            fdate = f.split('_')[1]
            fdates.add(fdate)

        per_date_df = {}
        for fdate_ in fdates:
            per_date_df[fdate_] = {}

        coord_dfs = {}
        for col in target_cols:
            for date in fdates:
                temp_profiles_df = pd.DataFrame(columns=['Depth (Meter)'])
                point_names = []
                lat_info = []
                lon_info = []
                for ff in os.listdir(DATAPATH):
                    checkpath = DATAPATH + '/' + ff
                    check_df = pd.read_csv(checkpath, skiprows=28, index_col=False)
                    if len(check_df) < 5:
                        continue
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
                    checkpath = DATAPATH + '/' + ff
                    check_df = pd.read_csv(checkpath, skiprows=28, index_col=False)
                    if len(check_df) < 5:
                        continue
                    fdate = ff.split('_')[1]
                    if date == fdate:
                    
                        fpath = DATAPATH + '/' + ff
                        if os.path.isfile(fpath):
                            df = pd.read_csv(fpath, skiprows=28, index_col=False)
                            target_df = df[['Depth (Meter)', col]]
                            target_df.columns = ['Depth (Meter)', f'{point_names[counter2]}']
                            target_df['Depth (Meter)'] = np.round(target_df['Depth (Meter)'], 1)
                            temp_profiles_df =  temp_profiles_df.merge(target_df, how='outer', on='Depth (Meter)', sort=True)
                            counter2 += 1
                    
                if len(point_names) > 0:
                    cols_sorted = sorted(point_names)
                    ordered_cols = ['Depth (Meter)'] + cols_sorted
                    temp_profiles_df = temp_profiles_df[ordered_cols]
                    per_date_df[date][col] = temp_profiles_df.to_json()
                    coord_dfs[date] = {'site': point_names, 'lat': lat_info, 'lon': lon_info}

            
        for key, value in per_date_df.items():
            mongo_client.ctd_data.insert_one({'date': key,'data': value})

        return jsonify({'msg': 'success'}), 200
    
    except Exception as e:
        print(e)
        return jsonify({'error': e}), 500

@ctd.route("/plots/", methods=['GET'])
def temperature_ctd_data():
    params_dict = {
        'temperature': 'Temperature (Celsius)',
        'conductivity': 'Conductivity (MicroSiemens per Centimeter)',
        'density': 'Density (Kilograms per Cubic Meter)',
        'pressure': 'Pressure (Decibar)'
    }
    qmode = request.args.get('mode')
    qparam = request.args.get('param')
   
    param = params_dict[qparam]

    try:
        dates = []
        ctd_data = mongo_client.ctd_data.find()
        data_dict = {}
        for data in ctd_data:
            date = data['date']
            dates.append(date)
            temp_df = json.loads(data['data'][param])
            data_dict[date] = temp_df
        
        
        if qmode == 'temporal':

            nrows = nrows_ncols_for_subplots(data_dict)[0]
            ncols = nrows_ncols_for_subplots(data_dict)[1]
            fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(8, 16), sharex=True, sharey=True)
            idx = []
            for i in range(nrows):
                for j in range(ncols):
                    if ncols == 2:
                        idx.append(i + j)
                        idx_np = np.array(idx)
                        k = np.sum(idx_np[-2:])
                    if ncols == 3:
                        idx.append(i + j)
                        idx_np = np.array(idx)
                        if len(idx_np) > 2:
                            k = np.sum(idx_np[-3:]) - 1
                        else:
                            k = idx[-1]
                    if ncols == 4:
                        idx.append(i + j)
                        idx_np = np.array(idx)
                        if len(idx_np) > 4:
                            k = np.sum(idx_np[-4:]) - 3
                        else:
                            k = idx[-1]
                    try:
                        plot_df = pd.DataFrame(data_dict[dates[k]])
                        plot_df.dropna(how='all', axis=1, inplace=True)
                        plot_cols = plot_df.columns.values.tolist()
                        # no_idx_cols = set([])
                        # for plot_col in plot_cols[1:]:
                        #     no_idx_cols.add(plot_col[:-2])
                        y = plot_df['Depth (Meter)']
                        for plot_col in plot_cols[1:]:
                            x = plot_df[plot_col]
                            axes[i, j].scatter(x, y, label=plot_col, s=6)
                        axes[i, j].legend(fontsize=5)
                        axes[i, j].set_title(dates[k], fontsize=8)
                        if k == 0:
                            axes[i, j].invert_yaxis()
                    except IndexError:
                        pass
            # plt.tight_layout()
            plt.show()

        if qmode == 'spatial':

            colors = {
                        '01': 'red','02': 'm', '03': '#FE0000',
                        '04': '#FF2984', '05': '#B729FF', '06': '#6229FF',
                        '07': '#2983FF', '08': '#29D8FF', '09': '#29FF83',
                        '10': 'c', '11': 'y', '12': 'orange'
                    }
            all_sites_dict = {}
            for site in sites:
                all_dates_df = pd.DataFrame(columns=['Depth (Meter)'])
                for date, data in data_dict.items():
                    data_df = pd.DataFrame(data)
                    data_cols = np.array(data_df.columns.values.tolist())
                    site_filter = data_cols[np.char.startswith(data_cols, site)]
                    if len(site_filter) == 0:
                        continue
                    start_col = np.array([data_cols[0]])
                    wanted_cols = np.concatenate((start_col, site_filter))
                    site_df = data_df[wanted_cols]
                    site_df.columns = site_df.columns.str.replace(site, date)
                    all_dates_df = all_dates_df.merge(site_df, how='outer', on='Depth (Meter)', sort=True)

                all_dates_df = all_dates_df.set_index('Depth (Meter)')
                all_sites_dict[site] = all_dates_df
            
            nrows = nrows_ncols_for_subplots(all_sites_dict)[0]
            ncols = nrows_ncols_for_subplots(all_sites_dict)[1]
            fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(8, 16), sharex=True, sharey=True)
            idx = []
            for i in range(nrows):
                for j in range(ncols):
                    if ncols == 2:
                        idx.append(i + j)
                        idx_np = np.array(idx)
                        k = np.sum(idx_np[-2:])
                    if ncols == 3:
                        idx.append(i + j)
                        idx_np = np.array(idx)
                        if len(idx_np) > 2:
                            k = np.sum(idx_np[-3:]) - 1
                        else:
                            k = idx[-1]
                    if ncols == 4:
                        idx.append(i + j)
                        idx_np = np.array(idx)
                        if len(idx_np) > 4:
                            k = np.sum(idx_np[-4:]) - 3
                        else:
                            k = idx[-1]
                    
                    try:
                        plot_df = all_sites_dict[sites[k]]
                        plot_df.dropna(how='all', axis=1, inplace=True)
                        plot_cols = plot_df.columns.values.tolist()
                        plot_df = plot_df.rename_axis('Depth (Meter)').reset_index()
                        y = plot_df['Depth (Meter)']
                        for plot_col in plot_cols:
                            year = plot_col[:4]
                            month = plot_col[4:6]
                            day = plot_col[6:8]
                            letter = plot_col[-1]
                            label = f'{day}-{month}-{year}'
                            if len(plot_col) > 8:
                                label = f'{day}-{month}-{year}_{letter}'

                            x = plot_df[plot_col]
                            axes[i, j].scatter(x, y, label=label, color=colors[month], s=6)
                        axes[i, j].legend(fontsize=5)
                        axes[i, j].set_title(sites[k], fontsize=8)
                        if k == 0:
                            axes[i, j].invert_yaxis()
                    except IndexError:
                        pass
            # plt.tight_layout()
            plt.show()

        return (jsonify({"msg": "success"}), 200)
    
    except Exception as e:
        print(e)
        return jsonify({'error': e}), 500