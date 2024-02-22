import matplotlib.pyplot as plt
from scripts.functions import *
import numpy as np
import random
import statsmodels.stats.multitest as smt
from scripts.classes import *

# Assuming 'A' and 'B' are encoded as strings in your 'Y' variable
b_neurons = [
    'AVAR',
    'AVAL',
    'SMDVR',
    'SMDVL',
    'SMDDR',
    'SMDDL',
    'RIBR',
    'RIBL'
]

worm_num = 0

data = Database(worm_num, verbose=1)
data.exclude_neurons(b_neurons)

# Adding prediction Model & Cluster BPT
logreg = LogisticRegression(solver='lbfgs', multi_class='multinomial', max_iter=1000)
data.fit_model(logreg, binary=True)

data.cluster_BPT(nrep=10, max_clusters=15, plot_markov=False)

def test_params_s(axes, parts=10, reps=3, N_states=10):
    print(f'For {N_states} Clusters!')
    result = np.zeros((5, parts-1, reps))
    #unadj_result = np.zeros((5, parts-1, reps))
    for p in range(parts-1):
        print(f'Divided into {p + 2} chunks.')
        for i in range(reps):
            worm_seq = data.xc[:, N_states-1, i].astype(int)
            true_seq = generate_markov_process(M=3000, N=N_states, order=1)
            rand_seq = simulate_random_sequence(M=3000, N=N_states)
            lag2_seq = generate_markov_process(M=3000, N=N_states, order=2)
            not_stat = non_stationary_process(M=3000, N=N_states, changes=10)

            x, adj_x = test_stationarity(true_seq, parts=p + 2, plot=False, sim_stationary=800)
            y, adj_y = test_stationarity(rand_seq, parts=p + 2, plot=False, sim_stationary=800)
            z, adj_z = test_stationarity(lag2_seq, parts=p + 2, plot=False, sim_stationary=800)
            a, adj_a = test_stationarity(not_stat, parts=p + 2, plot=False, sim_stationary=800)
            b, adj_b = test_stationarity(worm_seq, parts=p + 2, plot=False, sim_stationary=800)

            #print(f'Mean p-values for all 4 sequences:\n{adj_x, adj_y, adj_z, adj_a}')

            result[0, p, i] = np.mean(adj_x)
            result[1, p, i] = np.mean(adj_y)
            result[2, p, i] = np.mean(adj_z)
            result[3, p, i] = np.mean(adj_a)
            result[4, p, i] = np.mean(adj_b)

            #unadj_result[0, p, i] = x
            #unadj_result[1, p, i] = y
            #unadj_result[2, p, i] = z
            #unadj_result[3, p, i] = a
            #unadj_result[4, p, i] = b

    axes.plot(list(range(parts + 1))[2:], np.mean(result[0, :, :], axis=1), label='markov')
    lower_bound = np.percentile(result[0, :, :], 12.5, axis=1)
    upper_bound = np.percentile(result[0, :, :], 87.5, axis=1)
    axes.fill_between(list(range(parts + 1))[2:], lower_bound, upper_bound, alpha=0.3)

    axes.plot(list(range(parts + 1))[2:], np.mean(result[1, :, :], axis=1), label='random')
    lower_bound = np.percentile(result[1, :, :], 12.5, axis=1)
    upper_bound = np.percentile(result[1, :, :], 87.5, axis=1)
    axes.fill_between(list(range(parts + 1))[2:], lower_bound, upper_bound, alpha=0.3)

    axes.plot(list(range(parts + 1))[2:], np.mean(result[2, :, :], axis=1), label='2-order markov')
    lower_bound = np.percentile(result[2, :, :], 12.5, axis=1)
    upper_bound = np.percentile(result[2, :, :], 87.5, axis=1)
    axes.fill_between(list(range(parts + 1))[2:], lower_bound, upper_bound, alpha=0.3)

    axes.plot(list(range(parts + 1))[2:], np.mean(result[3, :, :], axis=1), label='non-stationary markov')
    lower_bound = np.percentile(result[3, :, :], 12.5, axis=1)
    upper_bound = np.percentile(result[3, :, :], 87.5, axis=1)
    axes.fill_between(list(range(parts + 1))[2:], lower_bound, upper_bound, alpha=0.3)

    axes.plot(list(range(parts + 1))[2:], np.mean(result[4, :, :], axis=1), label='worm')
    lower_bound = np.percentile(result[4, :, :], 12.5, axis=1)
    upper_bound = np.percentile(result[4, :, :], 87.5, axis=1)
    axes.fill_between(list(range(parts + 1))[2:], lower_bound, upper_bound, alpha=0.3)

    axes.axhline(0.05, color='black', linestyle='--')
    for tmp in list(range(parts + 1))[2:]:
        axes.axvline(tmp, color='black', alpha=0.1)
    axes.legend()
    return axes


parts = 17
reps = 10

fig, axes = plt.subplots(3, 3, figsize=(12, 9))
_ = test_params_s(axes[0, 0], parts=parts+10, reps=reps, N_states=2)
axes[0, 0].set_title('States 2')
axes[0, 0].set_ylim(0, 1)
#_ = test_params_s(axes[0, 1], parts=parts, reps=reps, N_states=3)
#axes[0, 1].set_title('States 3')
#axes[0, 1].set_ylim(0, 1)
_ = test_params_s(axes[0, 2], parts=parts+7, reps=reps, N_states=5)
axes[0, 2].set_title('States 5')
axes[0, 2].set_ylim(0, 1)
#_ = test_params_s(axes[1, 0], parts=parts, reps=reps, N_states=7)
#axes[1, 0].set_title('States 7')
#axes[1, 0].set_ylim(0, 1)
_ = test_params_s(axes[1, 1], parts=parts+5, reps=reps, N_states=10)
axes[1, 1].set_title('States 10')
axes[1, 1].set_ylim(0, 1)
#_ = test_params_s(axes[1, 2], parts=parts, reps=reps, N_states=12)
#axes[1, 2].set_title('States 12')
#axes[1, 2].set_ylim(0, 1)
_ = test_params_s(axes[2, 0], parts=parts+2, reps=reps, N_states=15)
axes[2, 0].set_title('States 15')
axes[2, 0].set_ylim(0, 1)
#_ = test_params_s(axes[2, 1], parts=parts, reps=reps, N_states=17)
#axes[2, 1].set_title('States 17')
#axes[2, 1].set_ylim(0, 1)
#_ = test_params_s(axes[2, 2], parts=parts, reps=reps, N_states=20)
#axes[2, 2].set_title('States 20')
#axes[2, 2].set_ylim(-0.1, 1.1)
fig.suptitle(f'Mean p-values (CI 75%) of Stationary Test for 2 to {parts} chunks')
plt.show()