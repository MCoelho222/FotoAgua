import os
from os.path import dirname, abspath, join
import pandas as pd
import numpy as np
# import json
import matplotlib.pyplot as plt
from flask import Blueprint
# from datetime import datetime
# from flask.wrappers import Response
# from src.app import mongo_client
# from bson import json_util
from flask import request, jsonify
from src.app.services.minidot_services import concat_minidot
from src.app.services.stats import mwhitney_test
# from src.app.services.geo_services import pointNamer
# from src.app.services.plot_services import nrows_ncols_for_subplots

minidot = Blueprint("minidot", __name__, url_prefix="/minidot")

ROOTPATH = dirname(dirname(dirname(dirname(abspath(__file__)))))
DATAPATH = join(ROOTPATH, 'data_minidot')
STATSPATH = join(ROOTPATH, 'minidot_stats')
CONCAT_DATAPATH = join(ROOTPATH, 'minidot_concat')
GRAPH_PATH = join(ROOTPATH, 'minidot_graphs')

@minidot.route("/process", methods=['GET'])
def minidot_process():

    minidot_concat = concat_minidot()
    minidot_concat

    return jsonify({'msg': 'success'}), 200


@minidot.route("/plot", methods=['GET'])
def minidot_plot():
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(16, 8))
    ax_index = {'fundo': 0, 'sup': 1}
    ax_title = {'fundo': 'bottom', 'sup': 'surface'}
    colors = {'pv1': 'r', 'lr': 'b'}

    minidot_dict = concat_minidot()

    for folder in os.listdir(DATAPATH):
        folder_split = folder.split('_')
        site = folder_split[0]
        depth = folder_split[1]
        ax_col = ax_index[depth]
        title = f'LR x PV1 ({ax_title[depth]})'
        do_col = f'DO (mg/l) {site.upper()}'
        t_col = f'T (°C) {site.upper()}'
        do_y_ticks = np.arange(0, 16, 2)
        t_y_ticks = np.arange(15, 35, 2)
        rename_dict = {
            '  DO (mg/l)': do_col,
            '  T (deg C)': t_col
            }
        df = minidot_dict[folder].rename(columns = rename_dict)
        # if ax_col == 0:
        # if ax_col == 0 and site == 'lr':
        #     df[do_col].plot(ax=axes[0, ax_col], sharex=True, legend=True, title=title, ylabel='mg/l', fontsize=10, color=colors[site], linewidth=1.0, yticks=do_y_ticks)
        # else:
        df[do_col].plot(ax=axes[0, ax_col], legend=True, title=title, ylabel='mg/l', fontsize=11, color=colors[site], linewidth=1.0, yticks=do_y_ticks)
        df[t_col].plot(ax=axes[1, ax_col], legend=True, ylabel='°C', fontsize=11, xlabel='Date', color=colors[site], linewidth=1.0, yticks=t_y_ticks)
        # if ax_col == 1:
        #     subplot = plt.gca()
        axes[0, 1].yaxis.set_ticklabels([])
        axes[1, 1].yaxis.set_ticklabels([])
        axes[0, 1].xaxis.set_ticklabels([])
        axes[0, 0].xaxis.set_ticklabels([])
        axes[0, 0].xaxis.label.set_visible(False)
        axes[0, 1].xaxis.label.set_visible(False)
        axes[0, 1].yaxis.label.set_visible(False)
        axes[1, 1].yaxis.label.set_visible(False)
        

        # if ax_col == 1:
        #     df[do_col].plot(ax=axes[0, ax_col], legend=True, title=title, ylabel='mg/l', fontsize=10, color=colors[site], linewidth=1.0, yticks=do_y_ticks)
        #     df[t_col].plot(ax=axes[1, ax_col], legend=True, ylabel='°C', fontsize=10, xlabel='Date', color=colors[site], linewidth=1.0, yticks=t_y_ticks)

    plt.tight_layout()
    figname1 = f'{GRAPH_PATH}/minidot_oct-22_fev-23.svg'
    figname2 = f'{GRAPH_PATH}/minidot_oct-22_fev-23.png'
    figname3 = f'{GRAPH_PATH}/minidot_oct-22_fev-23.jpg'
    plt.savefig(figname1)
    plt.savefig(figname2, dpi=600)
    plt.savefig(figname3, dpi=600)
    plt.show()
 
    return jsonify({'msg': 'success'}), 200

@minidot.route("/mwhitney", methods=['GET'])
def minidot_mwhitney():
    minidot_dict = concat_minidot()
    do_lr_bottom = minidot_dict['lr_fundo']['  DO (mg/l)'].values.tolist()
    t_lr_bottom = minidot_dict['lr_fundo']['  T (deg C)'].values.tolist()
    do_pv1_bottom = minidot_dict['pv1_fundo']['  DO (mg/l)'].values.tolist()
    t_pv1_bottom = minidot_dict['pv1_fundo']['  T (deg C)'].values.tolist()
    do_lr_surf = minidot_dict['lr_sup']['  DO (mg/l)'].values.tolist()
    t_lr_surf = minidot_dict['lr_sup']['  T (deg C)'].values.tolist()
    do_pv1_surf = minidot_dict['pv1_sup']['  DO (mg/l)'].values.tolist()
    t_pv1_surf = minidot_dict['pv1_sup']['  T (deg C)'].values.tolist()
    do_bottom_test = mwhitney_test({'LR_BOTTOM': do_lr_bottom, 'PV1_BOTTOM': do_pv1_bottom})
    do_surf_test = mwhitney_test({'LR_SURF': do_lr_surf, 'PV1_SURF': do_pv1_surf})
    t_bottom_test = mwhitney_test({'LR_BOTTOM': t_lr_bottom, 'PV1_BOTTOM': t_pv1_bottom})
    t_surf_test = mwhitney_test({'LR_SURF': t_lr_surf, 'PV1_SURF': t_pv1_surf})
    print(t_surf_test)
    do_df_dict = {
        'Hipótese': ['LR = PV1', 'LR > PV1', 'LR < PV1'],
        'Superfície': [f"{do_surf_test['decision']['H0: PV1_SURF == LR_SURF']} (stat: {do_surf_test['stats'][0]}, p-valor: {do_surf_test['stats'][1]})",
                  do_surf_test['decision']['H1: PV1_SURF < LR_SURF'],
                  do_surf_test['decision']['H2: PV1_SURF > LR_SURF']
                  ],
        'Fundo': [f"{do_bottom_test['decision']['H0: LR_BOTTOM == PV1_BOTTOM']} (stat: {do_bottom_test['stats'][0]}, p-valor: {do_bottom_test['stats'][1]})",
                  do_bottom_test['decision']['H2: LR_BOTTOM > PV1_BOTTOM'],
                  do_bottom_test['decision']['H1: LR_BOTTOM < PV1_BOTTOM']
                  ]
        }

    t_df_dict = {
        'Hipótese': ['LR = PV1', 'LR > PV1', 'LR < PV1'],
        'Superfície': [f"{t_surf_test['decision']['H0: PV1_SURF == LR_SURF']} (stat: {t_surf_test['stats'][0]}, p-valor: {t_surf_test['stats'][1]})",
                  t_surf_test['decision']['H1: PV1_SURF < LR_SURF'],
                  t_surf_test['decision']['H2: PV1_SURF > LR_SURF']
                  ],
        'Fundo': [f"{t_bottom_test['decision']['H0: LR_BOTTOM == PV1_BOTTOM']} (stat: {t_bottom_test['stats'][0]}, p-valor: {t_bottom_test['stats'][1]})",
                  t_bottom_test['decision']['H2: LR_BOTTOM > PV1_BOTTOM'],
                  t_bottom_test['decision']['H1: LR_BOTTOM < PV1_BOTTOM']
                  ]
        }
    do_df = pd.DataFrame(do_df_dict)
    t_df = pd.DataFrame(t_df_dict)
    do_df.to_excel(f'{STATSPATH}/do_stats.xlsx')
    t_df.to_excel(f'{STATSPATH}/t_stats.xlsx')
    print(do_df)
    print(t_df)
    return jsonify(do_bottom_test), 200
