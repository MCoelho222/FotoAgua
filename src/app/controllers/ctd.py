import os
from os.path import dirname, abspath, join
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
# from ua_parser import user_agent_parser
from flask import Blueprint
from datetime import datetime
# from flask.wrappers import Response
from src.app import mongo_client
# from bson import json_util
from flask import request, jsonify
from src.app.services.geo_services import pointNamer
from src.app.services.plot_services import nrows_ncols_for_subplots

ctd = Blueprint("ctd", __name__, url_prefix="/ctd")

ROOTPATH = dirname(dirname(dirname(dirname(abspath(__file__)))))
DATAPATH = join(ROOTPATH, 'data_ctd')
PROCESSED_XLSX_DATAPATH = join(ROOTPATH, 'ctd_processed_xlsx')
PROCESSED_CSV_DATAPATH = join(ROOTPATH, 'ctd_processed_csv')
GRAPH_PATH = join(ROOTPATH, 'ctd_graphs')

target_cols = ['Temperature (Celsius)', 'Pressure (Decibar)',
               'Conductivity (MicroSiemens per Centimeter)',
               'Specific conductance (MicroSiemens per Centimeter)',
               'Salinity (Practical Salinity Scale)',
               'Sound velocity (Meters per Second)',
               'Density (Kilograms per Cubic Meter)']

# sites = ['L1', 'L2', 'L3', 'LR', 'PV1', 'PV6', 'PV7', 'NEAR_UP', 'NEAR_DOWN', 'FAR_UP', 'VERY_FAR_UP', 'VERY_FAR_DOWN']
sites = ['LR', 'PV1',]

month_names = {
    "01": "jan",
    "02": "fev",
    "03": "mar",
    "04": "apr",
    "05": "may",
    "06": "jun",
    "07": "jul",
    "08": "aug",
    "09": "sep",
    "10": "oct",
    "11": "nov",
    "12": "dec",
}


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
    ------------------------------------------------------------"""
    try:
        for col in target_cols:
            fdates = set([])
            dfs_dict = {}
            coord_dfs = {}
            for f in os.listdir(DATAPATH):
                if f.endswith('.csv'):
                    fdate = f.split('_')[1]
                    fdates.add(fdate)
            for date in fdates:
                temp_profiles_df = pd.DataFrame(columns=['Depth (Meter)'])
                point_names = []
                lat_info = []
                lon_info = []
                for ff in os.listdir(DATAPATH):
                    if ff.endswith('.csv'):
                        fdate = ff.split('_')[1]
                        if date == fdate:
                            lat = None
                            lon = None
                            cast_time = None
                            for line in open(f'{DATAPATH}/{ff}', 'r'):
                                split_comma = line.split(',')
                                split_space = line.split(' ')
                                if split_comma[0] == '% Start latitude':
                                    lat = float(split_comma[1][:-2])
                                if split_comma[0] == '% Start longitude':
                                    lon = float(split_comma[1][:-2])
                                if split_comma[0] == '% Cast time (local)':
                                    cast_time = split_space[-1][:-1]
                            lat_info.append(lat)
                            lon_info.append(lon)
                            point_name = pointNamer(lat, lon, cast_time)
                            point_names.append(point_name)
                
                counter2 = 0
                for ff in os.listdir(DATAPATH):
                    if ff.endswith('.csv'):
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
            if f.endswith('.csv'):
                fdate = f.split('_')[1]
                fdates.add(fdate)

        per_date_df = {}
        for fdate_ in fdates:
            date_fmt_ = f'{fdate_[:4]}-{fdate_[4:6]}-{fdate_[6:8]}'
            per_date_df[date_fmt_] = {}

        coord_dfs = {}
        for col in target_cols:
            for date in fdates:
                date_fmt = f'{date[:4]}-{date[4:6]}-{date[6:8]}'
                temp_profiles_df = pd.DataFrame(columns=['Depth (Meter)'])
                point_names = []
                lat_info = []
                lon_info = []
                for f in os.listdir(DATAPATH):
                    if f.endswith('.csv'):
                        checkpath = DATAPATH + '/' + f
                        check_df = pd.read_csv(checkpath, skiprows=28, index_col=False)
                        if len(check_df) < 5:
                            continue
                        fdate = f.split('_')[1]
                        if date == fdate:
                            lat = None
                            lon = None
                            cast_time = None
                            for line in open(f'{DATAPATH}/{f}', 'r'):
                                split_comma = line.split(',')
                                split_space = line.split(' ')
                                if split_comma[0] == '% Start latitude':
                                    lat = float(split_comma[1][:-2])
                                if split_comma[0] == '% Start longitude':
                                    lon = float(split_comma[1][:-2])
                                if split_comma[0] == '% Cast time (local)':
                                    cast_time = split_space[-1][:-1]
                            lat_info.append(lat)
                            lon_info.append(lon)
                            point_name = pointNamer(lat, lon, cast_time)
                            point_names.append(point_name)

                counter2 = 0
                for f in os.listdir(DATAPATH):
                    if f.endswith('.csv'):
                        checkpath = DATAPATH + '/' + f
                        check_df = pd.read_csv(checkpath, skiprows=28, index_col=False)
                        if len(check_df) < 5:
                            continue
                        fdate = f.split('_')[1]
                        if date == fdate:
                        
                            fpath = DATAPATH + '/' + f
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
                    per_date_df[date_fmt][col] = temp_profiles_df.to_json()
                    coord_dfs[date_fmt] = {'site': point_names, 'lat': lat_info, 'lon': lon_info}

            
        for key, value in per_date_df.items():
            mongo_client.ctd_data.insert_one({'date': key,'data': value})

        return jsonify({'msg': 'success'}), 200
    
    except Exception as e:
        print(e)
        return jsonify({'error': e}), 500

@ctd.route("/plots/", methods=['GET'])
def plot_ctd_data():
    params_dict = {
        'temperature': 'Temperature (Celsius)',
    }
    # params_dict = {
    #     'temperature': 'Temperature (Celsius)',
    #     'conductivity': 'Conductivity (MicroSiemens per Centimeter)',
    #     'density': 'Density (Kilograms per Cubic Meter)',
    #     'pressure': 'Pressure (Decibar)'
    # }
    xlabels_dict = {
        'temperature': 'Temperature (°C)',
        'conductivity': 'Conductivity (u"\u03bcS/cm")',
        'density': 'Density (kg/m³)',
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
            if date.split('-')[0] == '2022':
                dates.append(datetime.strptime(date, '%Y-%m-%d').date())
                df = json.loads(data['data'][param])
                data_dict[date] = df
        dates.sort()

        fmt_dates = []
        for date in dates:
            fmt_dates.append(date.strftime('%Y-%m-%d'))
        
        if qmode == 'spatial':
            if len(data_dict) == 3:
                nrows = 3
                ncols = 1
            else:
                nrows = nrows_ncols_for_subplots(data_dict)[0]
                ncols = nrows_ncols_for_subplots(data_dict)[1]
            spatialcolors = {
                        'L1': 'm','L2': 'darkviolet', 'L3': 'deeppink',
                        'LR': 'red', 'PV1': 'lime', 'PV6': 'deepskyblue',
                        'PV7': 'b', 'FPV': 'g', 'NEAR_UP': 'k', 'NEAR_DOWN': 'dimgray',
                        'FAR_UP': 'grey', 'FAR_DOWN': 'darkgrey',
                        'VERY_FAR_UP': 'lightgrey', 'VERY_FAR_DOWN': 'gainsboro'
                    }
            fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(6, 8), sharex=True, sharey=True)
            
            idx = []
            for i in range(nrows):
                for j in range(ncols):
                    if ncols == 1:
                        k = i
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
                        plot_df = pd.DataFrame(data_dict[fmt_dates[k]])
                        plot_df.dropna(how='all', axis=1, inplace=True)
                        plot_cols = plot_df.columns.values.tolist()
                        y = plot_df['Depth (Meter)']
                        for plot_col in plot_cols[1:]:
                            point_name = plot_col.split(' ')[0]
                            if point_name == 'LR' or point_name == 'PV1':
                                x = plot_df[plot_col]
                                colorkey = plot_col.split(' ')[0]
                                if ncols == 1:
                                    axes[i].scatter(x, y, label=plot_col[:-3], s=6, color=spatialcolors[colorkey])
                                else:
                                    axes[i, j].scatter(x, y, label=plot_col[:-3], s=6, color=spatialcolors[colorkey])
                        leg_cols = 1
                        if len(plot_cols) > 14:
                            leg_cols = 2
                        if len(plot_cols) > 28:
                            leg_cols = 3
                        if len(plot_cols) > 42:
                            leg_cols = 4
                        if ncols == 1:
                            axes[i].legend(fontsize=8, framealpha=0.25, loc='upper left', ncols=leg_cols, columnspacing=0.2, labelspacing=0.2, handletextpad=0.1)
                            axtitle = f'{month_names[fmt_dates[k][5:7]]}-{fmt_dates[k][:4]}'
                            axes[i].set_title(axtitle, fontsize=10)
                            if k == 0:
                                axes[i].invert_yaxis()
                            if i == nrows - 1:
                                axes[i].set_xlabel(xlabels_dict[qparam])
                        else:
                            axes[i, j].legend(fontsize=8, framealpha=0.25, loc='upper left', ncols=leg_cols, columnspacing=0.2, labelspacing=0.2, handletextpad=0.1)
                            axtitle = f'{month_names[fmt_dates[k][5:7]]}-{fmt_dates[k][:4]}'
                            axes[i, j].set_title(axtitle, fontsize=10)
                            if k == 0:
                                axes[i, j].invert_yaxis()
                            if i == nrows - 1:
                                axes[i, j].set_xlabel(xlabels_dict[qparam])
                    except IndexError:
                        pass
                if ncols == 1:
                    axes[i].set_ylabel('Depth (m)')
                else:
                    axes[i, 0].set_ylabel('Depth (m)')
            plt.tight_layout()
            figname = f'{GRAPH_PATH}/fotoagua_{qparam}_{qmode}.jpeg'
            plt.savefig(figname, dpi=300)
            plt.show()

        if qmode == 'temporal':

            temporalcolors = {
                        '01': 'red','02': 'm', '03': 'pink',
                        '04': 'b', '05': '#B729FF', '06': '#6229FF',
                        '07': '#2983FF', '08': '#29D8FF', '09': '#29FF83',
                        '10': 'lime', '11': 'y', '12': 'orange'
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
                if len(all_dates_df) > 0:
                    all_sites_dict[site] = all_dates_df
            xmins = []
            xmaxs = []
            ymins = []
            ymaxs = []
            for site, df in all_sites_dict.items():
                xmins.append(np.floor(df.min().min()))
                ymins.append(np.floor(df.index.min()))
                xmaxs.append(np.ceil(df.max().max()))
                ymaxs.append(np.ceil(df.index.max()))
            plot_xmin = np.min(np.array(xmins))
            plot_ymin = np.min(np.array(ymins))
            plot_xmax = np.max(np.array(xmaxs))
            plot_ymax = np.max(np.array(ymaxs))
            if len(all_sites_dict) > 0:
                plot_sites = list(all_sites_dict.keys())
                print(len(plot_sites))
                if len(plot_sites) == 2:
                    nrows = 2
                    ncols = 1
                else:
                    nrows = nrows_ncols_for_subplots(all_sites_dict)[0]
                    ncols = nrows_ncols_for_subplots(all_sites_dict)[1]

                fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(6, 8), sharex=True, sharey=True)
                idx = []
                for i in range(nrows):
                    for j in range(ncols):
                        if ncols == 1:
                            k = i
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
                            plot_df = all_sites_dict[plot_sites[k]]
                            plot_df.dropna(how='all', axis=1, inplace=True)
                            plot_cols = plot_df.columns.values.tolist()
                            if ncols == 1:
                                plot_df = plot_df.rename_axis('Depth (Meter)').reset_index()
                                y = plot_df['Depth (Meter)']
                                for plot_col in plot_cols:
                                    plot_date = plot_col.split(' ')[0]
                                    plot_date = plot_date.replace('20', '')
                                    cast_time = plot_col.split(' ')[-1]
                                    plot_date_items = plot_date.split('-')
                                    year = plot_date_items[0]
                                    month = plot_date_items[1]
                                    label = f'{month_names[month]}-{year} {cast_time[:-3]}'
                                    x = plot_df[plot_col]
                                    xticks = np.arange(int(plot_xmin), int(plot_xmax), 1)
                                    yticks = np.arange(int(plot_ymin), int(plot_ymax), 2)
                                    axes[i].scatter(x, y, label=label, color=temporalcolors[month], s=6)
                                    axes[i].set_xticks(xticks, labels=xticks, fontsize=9)
                                    axes[i].set_yticks(yticks, labels=yticks, fontsize=9)
                                leg_cols = 1
                                if len(plot_cols) > 13:
                                    leg_cols = 2
                                if len(plot_cols) > 26:
                                    leg_cols = 3
                                if len(plot_cols) > 39:
                                    leg_cols = 4
                                axes[i].legend(fontsize=8, framealpha=0.25, loc='upper left', ncols=leg_cols, columnspacing=0.2, labelspacing=0.2, handletextpad=0.1)
                                axes[i].set_title(plot_sites[k], fontsize=9)
                                if i == nrows - 1:
                                    axes[i].set_xlabel(xlabels_dict[qparam], fontsize=9)
                                if j == 0:
                                    axes[i].set_ylabel('Depth (m)', fontsize=9)
                                if k == 0:
                                    axes[i].invert_yaxis()
                            else:
                                plot_df = plot_df.rename_axis('Depth (Meter)').reset_index()
                                y = plot_df['Depth (Meter)']
                                for plot_col in plot_cols:
                                    plot_date = plot_col.split(' ')[0]
                                    plot_date = plot_date.replace('20', '')
                                    cast_time = plot_col.split(' ')[-1]
                                    plot_date_items = plot_date.split('-')
                                    year = plot_date_items[0]
                                    month = plot_date_items[1]
                                    label = f'{month_names[month]}-{year} {cast_time[:-3]}'
                                    x = plot_df[plot_col]
                                    xticks = np.arange(int(plot_xmin), int(plot_xmax), 1)
                                    yticks = np.arange(int(plot_ymin), int(plot_ymax), 2)
                                    axes[i, j].scatter(x, y, label=label, color=temporalcolors[month], s=6)
                                    axes[i, j].set_xticks(xticks, labels=xticks, fontsize=9)
                                    axes[i, j].set_yticks(yticks, labels=yticks, fontsize=9)
                                leg_cols = 1
                                if len(plot_cols) > 13:
                                    leg_cols = 2
                                if len(plot_cols) > 26:
                                    leg_cols = 3
                                if len(plot_cols) > 39:
                                    leg_cols = 4
                                axes[i, j].legend(fontsize=8, framealpha=0.25, loc='upper left', ncols=leg_cols, columnspacing=0.2, labelspacing=0.2, handletextpad=0.1)
                                axes[i, j].set_title(plot_sites[k], fontsize=9)
                                if i == nrows - 1:
                                    axes[i, j].set_xlabel(xlabels_dict[qparam], fontsize=9)
                                if j == 0:
                                    axes[i, j].set_ylabel('Depth (m)', fontsize=9)
                                if k == 0:
                                    axes[i, j].invert_yaxis()
                        except IndexError as e:
                            print('INDEXERROR', e)
                            pass
                plt.tight_layout()
                # figname1 = f'{GRAPH_PATH}/fotoagua_{qparam}_{qmode}.png'
                figname2 = f'{GRAPH_PATH}/fotoagua_{qparam}_{qmode}.jpeg'
                # plt.savefig(figname1, dpi=300)
                plt.savefig(figname2, dpi=300)
                plt.show()

        return (jsonify({"msg": "success"}), 200)
    
    except Exception as e:
        print(e)
        return jsonify({'error': e}), 500