# -*- coding: utf-8 -*-
"""
Connectome-informed reservoir - Echo-State Network
=======================================================================
This example demonstrates how to use the conn2res toolbox to implement
perform multiple tasks across dynamical regimes, and using different
types local dynamics
"""
import warnings

import os
os.environ['OPENBLAS_NUM_THREADS'] = "1"
os.environ['MKL_NUM_THREADS'] = "1"

import time
import multiprocessing as mp

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

from conn2res import tasks
from conn2res.tasks import Conn2ResTask
from conn2res.connectivity import Conn
from conn2res.reservoir import EchoStateNetwork
from conn2res.readout import Readout
from conn2res import readout, plotting, utils

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# -----------------------------------------------------
PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJ_DIR, 'data')
OUTPUT_DIR = os.path.join(PROJ_DIR, 'results')
if not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# -----------------------------------------------------
N_PROCESS = 15
TASK = 'MemoryCapacity'
METRIC = ['corrcoef']
metric_kwargs = {
    'multioutput': 'sum',
    'nonnegative': 'absolute'
}
INPUT_GAIN = 0.01
ALPHAS = np.linspace(0, 2, 11)[1:]  # 41
RSN_MAPPING = np.load(os.path.join(DATA_DIR, 'rsn_mapping.npy'))
CORTICAL = np.load(os.path.join(DATA_DIR, 'cortical.npy'))
RSN_MAPPING = RSN_MAPPING[CORTICAL == 1]

def run_workflow(w, x, y, rand=True, filename=None):

    conn = Conn(w=w)
    if rand:
        conn.randomize(swaps=10)
        np.save(os.path.join(OUTPUT_DIR, f'{filename}.npy'), conn.w)

    conn.scale_and_normalize()

    input_nodes = conn.get_nodes(
        nodes_from=None,
        node_set='subctx',
    )

    output_nodes = conn.get_nodes(
        nodes_from=None,
        node_set='ctx',
    )

    w_in = np.zeros((1, conn.n_nodes))
    w_in[:, input_nodes] = np.eye(1)

    esn = EchoStateNetwork(w=conn.w, activation_function='tanh')
    readout_module = Readout(estimator=readout.select_model(y))

    x_train, x_test, y_train, y_test = readout.train_test_split(x, y)

    df_alpha = []
    for alpha in ALPHAS:

        print(f'\n\t\t\t----- alpha = {alpha} -----')

        esn.w = alpha * conn.w

        rs_train = esn.simulate(
            ext_input=x_train, w_in=w_in, input_gain=INPUT_GAIN,
            output_nodes=output_nodes
        )

        rs_test = esn.simulate(
            ext_input=x_test, w_in=w_in, input_gain=INPUT_GAIN,
            output_nodes=output_nodes
        )

        plotting.plot_reservoir_states(
            x=x_train, reservoir_states=rs_train,
            title=TASK,
            savefig=True,
            fname=os.path.join(OUTPUT_DIR, f'res_states_{INPUT_GAIN}_{np.round(alpha,2)}'),
            rc_params={'figure.dpi': 300, 'savefig.dpi': 300},
            show=False
        )

        df_res = readout_module.run_task(
            X=(rs_train, rs_test), y=(y_train, y_test),
            sample_weight=None, metric=METRIC,
            readout_modules=RSN_MAPPING, readout_nodes=None,
            **metric_kwargs
        )

        df_res['alpha'] = np.round(alpha, 3)
        df_alpha.append(df_res)

    df_alpha = pd.concat(df_alpha, ignore_index=True)
    df_alpha = df_alpha[['alpha', 'module', 'n_nodes', METRIC[0]]]
    df_alpha.to_csv(
        os.path.join(OUTPUT_DIR, f'res_{filename}.csv'),
        index=False
        )


def main():
    # w = np.load(os.path.join(DATA_DIR, 'connectivity.npy'))
    # coords = np.load(os.path.join(DATA_DIR, 'coords.npy'))
    # hemiid = np.load(os.path.join(DATA_DIR, 'hemiid.npy'))
    #
    # def consensus_network(w, coords, hemiid):
    #
    #     # remove bad subjects
    #     bad_subj = [7, 12, 43] #SC:7,12,43 #FC:32
    #     w = np.delete(w, bad_subj, axis=2)
    #
    #     # remove nans
    #     nan_subjs = np.unique(np.where(np.isnan(w))[-1])
    #     w = np.delete(w, nan_subjs, axis=2)
    #     stru_conn_avg = utils.struct_consensus(data=w.copy(),
    #                                            distance=cdist(coords, coords, metric='euclidean'),
    #                                            hemiid=hemiid[:, np.newaxis]
    #                                            )
    #
    #     return stru_conn_avg*np.mean(w, axis=2)
    # w_consensus = consensus_network(w, coords, hemiid)
    # np.save(os.path.join(DATA_DIR, 'w_consensus.npy'), consensus)

    w = np.load(os.path.join(DATA_DIR, 'consensus.npy'))

    task = Conn2ResTask(name=TASK)
    # x, y = task.fetch_data(n_trials=1000)
    # np.save(os.path.join(OUTPUT_DIR, 'input.npy'), x)
    # np.save(os.path.join(OUTPUT_DIR, 'output.npy'), y)

    x = np.load(os.path.join(OUTPUT_DIR, 'input.npy'))
    y = np.load(os.path.join(OUTPUT_DIR, 'output.npy'))

    # params = []
    # for i in range(1000):
    #     params.append(
    #         {
    #             'w': w.copy(),
    #             'x': x.copy(),
    #             'y': y.copy(),
    #             'filename': f'null_{i}'
    #         }
    #     )

    # run workflow in parallel
    print('\nINITIATING PROCESSING TIME')
    t0 = time.perf_counter()

    run_workflow(w, x, y, rand=False, filename='empirical')

    # pool = mp.Pool(processes=N_PROCESS)
    # res = [pool.apply_async(run_workflow, (), p) for p in params]
    # for r in res: r.get()
    # pool.close()

    print('\nTOTAL PROCESSING TIME')
    print(time.perf_counter()-t0, "seconds process time")
    print('END')


if __name__ == '__main__':
    main()
