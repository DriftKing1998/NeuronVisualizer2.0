# import MyBundle
from scripts.functions import *
# from BunDLeNet import *
from scripts.MyBundle import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from sklearn.decomposition import PCA
from typing import Optional, List, Union
import mat73
from sklearn.decomposition import NMF
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.cluster import KMeans
import matplotlib.animation as anim  # FuncAnimation
from sklearn.base import clone
from sklearn.ensemble import StackingClassifier
from sklearn.manifold import TSNE

import networkx as nx
from itertools import combinations
from pyvis.network import Network
import copy


class Loader:

    def __init__(self, data_set_no):
        """
        Reads in the data from the all files corresponding to the selected dataset.
        It stores all values into numpy arrays.

        :param data_set_no: Defines which CSV files will be read.
        :type data_set_no: int
        """

        self.data_set_no = data_set_no
        data_dict = mat73.loadmat('/Users/michaelhofer/Documents/GitHub/NeuronVisualizer2.0/data/NoStim_Data.mat')
        data = data_dict['NoStim_Data']
        deltaFOverF_bc = data['deltaFOverF_bc'][self.data_set_no]
        derivatives = data['derivs'][self.data_set_no]
        NeuronNames = data['NeuronNames'][self.data_set_no]
        fps = data['fps'][self.data_set_no]
        States = data['States'][self.data_set_no]

        self.B = np.sum([n * States[s] for n, s in enumerate(States)], axis=0).astype(
            int)  # making a single states array in which each number corresponds to a behaviour
        self.states = [*States.keys()]
        self.neuron_traces = np.array(deltaFOverF_bc).T
        self.neuron_names = np.array(NeuronNames, dtype=object)
        self.fps = fps

        self.data = self.neuron_traces, self.B, self.neuron_names, self.states, self.fps


class Database:

    def __init__(self,
                 neuron_traces: Union[List[List[float]], np.ndarray],
                 behavior: Union[List[int], List[str], np.ndarray],
                 neuron_names: Optional[Union[List[str], np.ndarray]] = None,
                 states: Optional[Union[List[str], np.ndarray]] = None,
                 fps: float = None,
                 name: str = 'nc-mcm'):

        """
        Reads in the data preferably as numpy arrays or Python-lists. If the behavior array consists of strings, a
        list for translation is created (states) and the behavior is transformed into integers (index of states). Also
        creates colors for plotting. The object can be seen as a container for all the data which is used to plot later.

        :param neuron_traces: Defines which CSV files will be read.
        :type neuron_traces: float

        :param behavior: Defines which CSV files will be read.
        :type behavior: int

        :param neuron_names: Defines which CSV files will be read.
        :type neuron_names: int

        :param states: Defines which CSV files will be read.
        :type states: int

        :param fps: Defines which CSV files will be read.
        :type fps: int

        :param name: Separator to split the CSV files.
        :type name: string
        """

        #
        self.neuron_traces = np.asarray(neuron_traces)
        self.fps = fps
        self.name = name
        behavior = np.asarray(behavior)
        # If B is not an integer array we have to transform it into one
        if not (np.issubdtype(behavior.dtype, int) or np.issubdtype(behavior.dtype, np.integer)):
            print('B has to be transformed into a integer-array. Translation is accessed by\'self.states\'.')
            newB, blabs = make_integer_list(behavior)
            self.B = np.asarray(newB)
            self.states = np.asarray(blabs).astype(str)
        else:
            self.B = behavior
            self.states = states
        # If no Neuron Names are given, they are generated
        if neuron_names is None:
            self.neuron_names = np.asarray(range(self.neuron_traces.shape[0])).astype(str)
        else:
            self.neuron_names = np.asarray(neuron_names)

        self.pred_model = None
        self.B_pred = None
        self.yp_map = None
        self.p_memoryless = None
        self.p_stationary = None
        self.xc = None

        self.colordict = dict(zip(np.unique(self.B), generate_equidistant_colors(len(self.states))))
        self.colors = [self.colordict[val] for val in self.B]

        if self.B.shape[0] != self.neuron_traces.shape[1] or self.neuron_names.shape[0] != self.neuron_traces.shape[0]:
            print('Error! Data seems not to fit together.')
            print(f'Frames of behavior {self.B.shape[0]} are not the same length as frames of neuronal data: '
                  f'{self.neuron_traces.shape[1]}')
            print(f'Or Neuron-names {self.neuron_names.shape[0]} are not the same length as neurons were recorded '
                  f'{self.neuron_traces.shape[0]}')

    def exclude_neurons(self, exclude_neurons):
        """
        Excludes specified neurons from the database.

        :param exclude_neurons: List of neuron names to exclude.
        :type exclude_neurons: list
        """

        neuron_names = self.neuron_names
        mask = np.zeros_like(self.neuron_names, dtype='bool')
        for exclude_neuron in exclude_neurons:
            mask = np.logical_or(mask, neuron_names == exclude_neuron)
        mask = ~mask
        amount = len(mask) - np.count_nonzero(mask)
        self.neuron_traces = self.neuron_traces[mask]
        self.neuron_names = self.neuron_names[mask]

        print(f'{amount} neurons have been removed.')

    def createVisualizer(self, mapping=None, l_dim=3, epochs=2000, window=15, use_predictor=True):
        """
        Takes either a mapping to visualize the data (e.g.: PCA) or parameters for a BundleNet (l_dim, epochs, window)
        which will be used to visualize the data. If a BundleNet is created, it will be used to predict behaviors in
        future plots. Otherwise, the model fitted on the Database-object, will be used as a predictor, if it exists.

        :param mapping: A mapping (such as PCA) which is used for the projection into three dimension. It needs to have
         the method 'fit_transform'.

        :param l_dim: Latent dimension the BundleNet maps to (for visualisation: 3D; For further use: XD)
        :type l_dim: int

        :param epochs: Epochs for the BundleNet
        :type epochs: int

        :param window: Window-size for BundleNet
        :type window: int
        """

        # If a mapping is provided
        if mapping is not None:
            vs = Visualizer(self, mapping)
        # otherwise a BundleNet is created
        else:
            if self.fps is None:
                print('Give \'self.fps\' a value (float) first!')
                return None
            time, newX = preprocess_data(self.neuron_traces.T, self.fps)
            X_, B_ = prep_data(newX, self.B, win=window)
            model = BunDLeNet(latent_dim=l_dim)
            model.build(input_shape=X_.shape)

            optimizer = tf.keras.optimizers.legacy.Adam(learning_rate=0.001)
            loss_array = train_model(
                X_,
                B_,
                model,
                optimizer,
                gamma=0.9,
                n_epochs=epochs
            )

            vs = Visualizer(self, model.tau, transform=False)
            vs.X_ = X_
            vs.B_ = B_
            vs.model = model
            vs.loss_array = loss_array
            # print(loss_array)
            vs.tau_model = model.tau
            vs.bundle_tau = True
            # I need to do this later, since X_ is not defined yet
            vs._transform_points(vs.mapping)
            if use_predictor:
                vs.useBundlePredictor()
        return vs

    # NEEDS SOME WORK
    def loadBundleVisualizer(self, weights_path=None, l_dim=3, window=15):
        time, newX = preprocess_data(self.neuron_traces.T, self.fps)
        X_, B_ = prep_data(newX, self.B, win=window)
        model = BunDLeNet(latent_dim=l_dim)
        model.build(input_shape=X_.shape)

        if weights_path is None:
            model.load_weights('data/generated/BunDLeNet_model_' + self.name)
        else:
            model.load_weights(weights_path)

        vs = Visualizer(self, model.tau, transform=False)
        vs.X_ = X_
        vs.B_ = B_
        vs.model = model
        # vs.loss_array = loss_array
        vs.tau_model = model.tau
        vs.bundle_tau = True
        # I need to do this later, since X_ is not defined yet
        vs._transform_points(vs.mapping)
        vs.useBundlePredictor()
        return vs

    # Maybe make a 90/10 training test set split.
    def fit_model(self, base_model, prob_map=True, binary=True):
        """
        Allows to fit a model which is used to predict behaviors from the neuron traces (accuracy is printed). Its
        probabilities are used for an eventual clustering.

        :param base_model:
        :param prob_map: A boolean indicating if a probability map is created for each frame. This is used in the
        behavioral probability trajectory clustering (.cluster_BPT()).
        :param binary: A boolean indicating if the CustomEnsembleModel should be created. It makes a set of models for
        each behavior, to differentiate it from each of the others behaviors.
        :return: Boolean success indicator
        """
        if not hasattr(base_model, 'fit'):
            print('Model has no method \'fit\'.')
            return False

        # For a binary regression by hand
        if binary:
            self.pred_model = CustomEnsembleModel(base_model).fit(self.neuron_traces.T, self.B)
        # For a multiclass regression
        else:
            self.pred_model = base_model.fit(self.neuron_traces.T, self.B)

        self.B_pred = np.asarray(self.pred_model.predict(self.neuron_traces.T))
        print("Accuracy:", accuracy_score(self.B, self.B_pred))
        if prob_map:
            # get probabilities and weights
            self.yp_map = self.pred_model.predict_proba(self.neuron_traces.T)
            print(f'Probability map has shape: {self.yp_map.shape}')
        return True

    def cluster_BPT(self, nrep=200, max_clusters=20, sim_markov=200, chunks=7, kmeans_init='auto', plot_markov=True):
        if self.yp_map is None:
            print(f'You first need to fit a model (eg. Logistic Regression), '
                  f'which will be used to map to behavioral probability trajectories.\n'
                  f'Use \'.fit_model(<your_model>)\' on this instance before.')
            return False

        M = self.yp_map.shape[0]
        self.p_memoryless = np.zeros((max_clusters, nrep))
        self.p_stationary = np.zeros((max_clusters, nrep))
        self.xc = np.zeros((M, max_clusters, nrep))

        for reps in range(nrep):
            print("Testing markovianity - repetition ", reps + 1)
            for nrclusters in range(max_clusters):
                # k-means
                clusters = KMeans(n_clusters=nrclusters + 1, n_init=kmeans_init).fit(self.yp_map)
                xctmp = clusters.labels_

                p, _ = markovian(xctmp, K=sim_markov)
                # print('Memoryless test done')

                _, p_adj_stationary = test_stationarity(xctmp, parts=chunks, plot=False)
                # print('Stationary test done')

                self.p_memoryless[nrclusters, reps] = p
                self.p_stationary[nrclusters, reps] = p_adj_stationary

                self.xc[:, nrclusters, reps] = xctmp

        if plot_markov:
            self._plot_markov()

        return True

    def _plot_markov(self):
        fig, ax = plt.subplots()
        data_m = self.p_memoryless[:, :].T
        data_s = self.p_stationary[:, :].T
        # Plotting
        boxplot_m = ax.boxplot(data_m, patch_artist=True, boxprops=dict(facecolor='lightblue'))
        boxplot_s = ax.boxplot(data_s, patch_artist=True, boxprops=dict(facecolor='salmon'))

        box_label_m = 'Memoryless'
        boxplot_m['boxes'][0].set_label(box_label_m)
        box_label_s = 'Stationary'
        boxplot_s['boxes'][0].set_label(box_label_s)

        ax.set_title(f'Probability of being a Markov process for {self.name}')
        ax.set_xlabel('Number of States/Clusters')
        ax.set_ylabel('Probability')
        ax.axhline(0.05)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def step_plot(self, clusters=5, nrep=10, sim_markov=200, save=False, show=True, png_name=None):
        if self.p_memoryless is None:
            print('There were no BPT-clusterings computed. It will be done now...')
            self.fit_model(LogisticRegression(solver='lbfgs', max_iter=1000), binary=True)
            self.cluster_BPT(nrep=nrep, max_clusters=clusters, sim_markov=sim_markov, plot_markov=False)

        # Neuronal trajectories preprocessing
        fig, ax = plt.subplots(2, 2, figsize=(16, 8))
        pca = PCA(n_components=2)
        plot_values = pca.fit_transform(self.neuron_traces.T)
        x_nt, y_nt = plot_values.T
        handles = []
        for idx, state in enumerate(self.states):
            patch = mpatches.Patch(color=self.colordict[idx], label=state)
            handles.append(patch)

        # Behavioral probability trajectories preprocessing
        pca = PCA(n_components=2)
        plot_values = pca.fit_transform(self.yp_map)
        x_bpt, y_bpt = plot_values.T
        colordict_cog = dict(zip(list(range(clusters)), generate_equidistant_colors(clusters)))
        best_clustering_idx = np.argmax(self.p_memoryless[clusters - 1, :])  # according to mr.markov himself
        best_clustering = self.xc[:, clusters - 1, best_clustering_idx].astype(int)
        cog_colors = [colordict_cog[l] for l in best_clustering]
        handles_cog = []
        for idx in range(clusters):
            patch = mpatches.Patch(color=colordict_cog[idx], label=f'C{idx + 1}')
            handles_cog.append(patch)

        # UPPER LEFT PLOT
        ax[0, 0] = self._add_quivers2D(ax[0, 0], x_nt, y_nt, None)
        ax[0, 0].legend(handles=handles, loc='best')
        ax[0, 0].set_title('Neuronal trajectories with behavioral labels')

        # UPPER RIGHT PLOT
        ax[0, 1] = self._add_quivers2D(ax[0, 1], x_bpt, y_bpt, None)
        ax[0, 1].set_title('Behavioral probability trajectories with behavioral labels')

        # LOWER LEFT PLOT
        ax[1, 0] = self._add_quivers2D(ax[1, 0], x_bpt, y_bpt, colors=cog_colors)
        ax[1, 0].set_title('Behavioral probability trajectories with cognitive labels')

        # LOWER RIGHT PLOT
        ax[1, 1] = self._add_quivers2D(ax[1, 1], x_nt, y_nt, colors=cog_colors)
        ax[1, 1].legend(handles=handles_cog, loc='best')
        ax[1, 1].set_title('Neuronal trajectories with cognitive labels')

        # GENERAL
        fig.suptitle(f'{self.name} with {clusters} cognitive states')
        if save:
            if png_name:
                plt.savefig(f'data/plots/{png_name}.png', format='png')
            else:
                plt.savefig(f'data/plots/step_plot_{self.name}.png', format='png')
        if show:
            plt.show()

    def _add_quivers2D(self, ax, x, y, colors=None):
        if colors is None:
            colors = self.colors[:-1]
        dx = np.diff(x)  # Differences between x coordinates
        dy = np.diff(y)  # Differences between y coordinates
        ax.quiver(x[:-1], y[:-1], dx, dy, color=colors, alpha=0.5)
        return ax

    def behavioral_state_diagram(self,
                                 cog_stat_num=3,
                                 threshold=None,
                                 offset=2.5,
                                 adj_matrix=True,
                                 save=True,
                                 interactive=False):
        if self.p_memoryless is None:
            print('You need to run the behavioral probability trajectory clustering first (\'.cluster_BPT\').')
            return False
        if threshold is None:
            threshold = 1 / (500 * cog_stat_num)
            print('threshold is: ', threshold)
        # make the graph
        G = nx.DiGraph()
        node_colors = list(self.colordict.values()) * cog_stat_num

        T, cog_beh_states = adj_matrix_ncmcm(self, cog_stat_num=cog_stat_num)
        G.add_nodes_from(cog_beh_states)

        # adding edges
        for idx1, n1 in enumerate(cog_beh_states):
            for idx2, n2 in enumerate(cog_beh_states):
                if n1 != n2:
                    if T[idx1, idx2] > threshold:
                        G.add_edge(n1, n2, weight=T[idx1, idx2] * 1000)

        edge_colors = [node_colors[np.where(cog_beh_states == u)[0][0]] for u, v in G.edges()]
        node_sizes = np.diag(T) * 500 * (np.sqrt(T.shape[0]) / offset)
        mapping = {node: self.map_names(str(node)) for node in G.nodes()}

        G = nx.relabel_nodes(G, mapping)

        if adj_matrix:
            plt.imshow(T, cmap='Reds', interpolation='nearest', vmin=0, vmax=0.03)
            plt.title('Adjacency Matrix Heatmap')
            plt.colorbar()
            plt.yticks(np.arange(T.shape[0]), G.nodes)
            plt.xlabel('Nodes')
            plt.ylabel('Nodes')
            plt.show()

        cog_groups = []
        for c_num in range(cog_stat_num):
            cog_groups.append([n for n in G.nodes if n.split(':')[0] == 'C' + str(c_num + 1)])

        all_pos = []
        for c_node_group in cog_groups:
            all_pos.append(nx.circular_layout(G.subgraph(c_node_group)))

        adjusted_pos = {}
        degrees_list = np.linspace(0, 360, num=cog_stat_num, endpoint=False)
        for idx, current_pos in enumerate(all_pos):
            adjusted_pos = shift_pos_by(current_pos, adjusted_pos, degrees_list[idx], offset)

        # Plot graph
        edges = G.edges()
        weights = [G[u][v]['weight'] for u, v in edges]

        nx.draw(G, adjusted_pos,
                with_labels=True,
                connectionstyle="arc3,rad=-0.2",
                node_color=node_colors,
                node_size=node_sizes,
                width=weights,
                arrows=True,
                arrowsize=10,
                edge_color=edge_colors)
        plt.title("Behavioral State Diagram")
        plt.show()

        if save:
            nx.draw(G, adjusted_pos,
                    with_labels=True,
                    connectionstyle="arc3,rad=-0.2",
                    node_color=node_colors,
                    node_size=node_sizes,
                    width=weights,
                    arrows=True,
                    arrowsize=10,
                    edge_color=edge_colors)
            plt.title("Behavioral State Diagram")
            name = str(input('File name for the plot? '))
            plt.savefig(f'data/plots/{name}.png', format='png')
            plt.close()
            # This right here will create the interactive HTML plot
            if interactive:
                net = Network(directed=True  # ,
                              # select_menu=True,  # Show part 1 in the plot (optional)
                              )
                net.from_nx(G)
                for node in net.nodes:
                    c, b = node['id'].split(':')
                    c_int = int(c[1:]) - 1
                    b_int = np.where(np.asarray(self.states) == b)[0][0]
                    r, g, b = self.colordict[b_int]
                    node['color'] = f'rgb({r * 255},{g * 255},{b * 255})'
                    node['size'] = np.sqrt(node_sizes[c_int * (len(self.states)) + b_int])

                net.show(f'data/plots/{name}.html', notebook=False)

    def map_names(self, name):
        new_name = f'C{name[:-2]}:{self.states[int(name[-2:])]}'
        return new_name

    def plotting_neuronal_behavioural(self, vmin=0, vmax=2):
        fig, axs = plt.subplots(2, 1, figsize=(10, 4))
        self._neurons(ax=axs[0])
        self._behavior(ax=axs[1])
        plt.subplots_adjust(hspace=0.5)
        plt.show()

    def _behavior(self, ax=None, sample=None):

        show = False
        if ax is None:
            show = True
            fig, ax = plt.subplots(figsize=(10, 2))

        cmap = plt.get_cmap('Pastel1', np.max(self.B) - np.min(self.B) + 1)
        im1 = ax.imshow([self.B], cmap=cmap, vmin=np.min(self.B) - 0.5, vmax=np.max(self.B) + 0.5,
                        aspect='auto')
        # tell the colorbar to tick at integers
        cax = ax.get_figure().colorbar(im1, ticks=np.arange(np.min(self.B), np.max(self.B) + 1))
        if len(np.unique(self.B)) == len(self.states):
            cax.ax.set_yticklabels(self.states)
        ax.set_xlabel("time $t$")
        ax.set_ylabel("Behaviour")
        ax.set_yticks([])
        # ax.set_title(f'Sample no#{self.data_set_no + 1}')

        if show:
            plt.show()

    def _neurons(self, ax=None, vmin=0, vmax=2):
        show = False
        if ax is None:
            show = True
            fig, ax = plt.subplots(figsize=(10, 2))

        im0 = ax.imshow(self.neuron_traces, aspect='auto', vmin=vmin, vmax=vmax, interpolation='None')
        # tell the colorbar to tick at integers
        # plt.colorbar(im0)
        ax.get_figure().colorbar(im0)
        ax.set_xlabel("time $t$")
        ax.set_ylabel("Neurons")
        ax.set_title("Neuronal activation")
        if show:
            plt.show()


class Visualizer():

    def __init__(self,
                 # X: Union[List[List[float]], np.ndarray],
                 # B: Union[List[int], List[str], np.ndarray],
                 Data: Database,
                 mapping,
                 transform=True):
        # B_pred: Union[List[int], List[str], np.ndarray],
        # xlabs: Optional[Union[List[str], np.ndarray]] = None,
        # blabs: Optional[Union[List[str], np.ndarray]] = None,
        # fps: float = None):
        """
        Takes values for features (neurons), labels (behaviors), and their corresponding names. If B is a list of strings,
        those are taken as blabs, and blabs is ignored.

        :param X: ndarray
        :type X: 2D array with each row corresponding to a neuron and each column is a timeframe.

        :param B: ndarray
        :type B: 1D array with behavior encoded as integers.

        :param xlabs: ndarray
        :type xlabs: 1D array with the names of the neurons.

        :param blabs: ndarray
        :type blabs: 1D array with translation for behavior.

        :param fps: float
        :type fps: gives the recording fps.

        Returns:
            None
        """

        # Setting Attributes
        self.data = Data
        self.B_pred = self.data.B_pred
        self.pred_model = self.data.pred_model
        self.X_ = None
        self.B_ = None
        # Mapping
        self.mapping = mapping
        if transform:
            self._transform_points(self.mapping)
        else:
            self.transformed_points = None

        # If B is not an integer array we have to transform it into one
        if not (np.issubdtype(self.data.B.dtype, int) or np.issubdtype(self.data.B.dtype, np.integer)):
            print('B has been transformed and a blabs has been created')
            newB, blabs = make_integer_list(self.data.B)
            self.data.B = np.asarray(newB)
            self.data.states = np.asarray(blabs).astype(str)

        # If no Neuron Names / State Names are given, they are generated
        if self.data.neuron_names is None:
            self.data.neuron_names = np.asarray(range(self.data.neuron_traces.shape[1])).astype(str)
        else:
            self.data.neuron_names = np.asarray(self.data.neuron_names)
        if self.data.states is None:
            self.data.states = np.asarray(np.unique(self.data.B)).astype(str)
        else:
            self.data.states = np.asarray(self.data.states)

        # generate a color-dictionary for all states and generate the colors
        # self.colordict = dict(zip(np.unique(self.data.B), generate_equidistant_colors(len(self.data.states))))
        # = [self.colordict[val] for val in self.data.B]
        self.plot_colors = None
        self.colors_diff_pred = None
        self.colors_pred = None
        # BundleNet
        self.tau_model = None
        self.bundle_tau = False
        self.model = None
        # Animation
        self.animation = None
        self.interval = None
        self.scatter = None

    def change_mapping(self, new_mapping):
        if self._transform_points(new_mapping):
            self.mapping = new_mapping
        else:
            print('Mapping was not changed.')

    ### DIAGNOSTICS ###

    def plot_mapping(self, show_legend=False, grid_off=True, quivers=False, show=True):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        if self.transformed_points.shape[0] != 3:
            print('The mapping does not map into a 3D space.')
            return False

        # We need to trim labs and colors if we have a Bundle
        if self.transformed_points.shape[1] < len(self.data.colors):
            window = len(self.data.colors) - self.transformed_points.shape[1]
            self.plot_colors = self.data.colors[window:]
        else:
            self.plot_colors = self.data.colors

        if quivers:
            ax = self._add_quivers3D(ax, *self.transformed_points, colors=self.plot_colors)
        else:
            ax.scatter(*self.transformed_points, label=self.data.states, color=self.plot_colors, s=1, alpha=0.5)

        # plot the legend if wanted
        if show_legend:
            legend_elements = self._generate_legend(self.data.B)
            ax.legend(handles=legend_elements, loc='best')
        else:
            legend_elements = False

        if grid_off:
            ax.grid(False)
            ax.set_axis_off()

        if show:
            plt.show()
            return True
        else:
            return fig, ax, legend_elements

    def _transform_points(self, mapping):
        if mapping is None:  # This should not happen normally
            print('No mapping present. CREATING PCA MODEL ...')
            mapping = PCA(n_components=3)
            transformed_points = mapping.fit_transform(self.data.neuron_traces.T)
        # If we are using the TAU model to map into 3D space
        elif isinstance(mapping, tf.keras.Sequential):
            # If the mapping is BundleNet we use the 'windowed' input
            if mapping.input_shape[1] == self.X_.shape[2]:
                self.bundle_tau = True
                transformed_points = np.asarray(mapping(self.X_[:, 0]))
            else:
                transformed_points = np.asarray(mapping(self.data.neuron_traces.T))
        # This happens if we give some mapping which is not a NN
        elif hasattr(mapping, 'fit_transform'):
            if mapping.get_params()['n_components'] == 3:
                print('HAVE mapping MODEL')
                if isinstance(mapping, NMF):
                    scaler = MinMaxScaler(feature_range=(0, np.max(self.data.neuron_traces.T)))
                    X_scaled = scaler.fit_transform(self.data.neuron_traces.T)
                    transformed_points = mapping.fit_transform(X_scaled)
                else:
                    transformed_points = mapping.fit_transform(self.data.neuron_traces.T)
            else:
                print('The selected model does not project to a 3 dimensional space.')
                return False
        else:
            print('The selected mapping has no attribute \'fit_transform\'. (SKLEARN models are recommended)')
            return False

        print('Points have coordinate shape: ', transformed_points.shape)
        # self.x, self.y, self.z = transformed_points.T
        self.transformed_points = transformed_points.T
        return True

    def _generate_legend(self, blabs, diff=False):
        # if the legend for the difference plot is requested
        if diff:
            y_labels_diff = {
                label: {wrong: count for wrong, count in self.diff_label_counts[c_idx].items() if count}
                for c_idx, label in enumerate(self.data.states)
            }

            legend_elements = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.data.colordict[idx],
                                          markersize=10,
                                          label=r'$\mathbf{' + keyval[0] + '}$' + ' to ' +
                                                "; ".join(
                                                    [r"$\mathbf{" + w_behav + "}$" + f"({amount})"
                                                     for w_behav, amount in keyval[1].items()]
                                                )
                                          if keyval[1] else r'$\mathbf{' + keyval[
                                              0] + '}$' + " predictions were always correct")
                               for idx, keyval in enumerate(y_labels_diff.items())]

            return legend_elements

        # Create custom legend handles
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.data.colordict[idx],
                                      markersize=10,
                                      label=r'$\mathbf{' + lab + '}$' + f' ({list(blabs).count(idx)})')
                           for idx, lab in enumerate(self.data.states)]

        return legend_elements

    def _generate_diff_label_counts(self, diff_predict):
        # Create dictionary to count different predictions for each label
        self.diff_label_counts = {l: {state: 0 for state in self.data.states} for l in np.unique(self.data.B)}
        for idx, wrong_predict in enumerate(diff_predict):
            pred_label = self.B_pred[idx]
            true_label = self.data.B[idx]
            if wrong_predict > -1:
                self.diff_label_counts[true_label][self.data.states[pred_label]] += 1

    def attachBundleNet(self, l_dim=3, train=True, epochs=2000, window=15, use_predictor=True):
        if self.data.fps is None:
            print('In order to attach the BundleNet \'self.data.fps\' has to have a value!')
            return False

        time, newX = preprocess_data(self.data.neuron_traces.T, self.data.fps)
        self.X_, self.B_ = prep_data(newX, self.data.B, win=window)
        self.model = BunDLeNet(latent_dim=l_dim)
        self.model.build(input_shape=self.X_.shape)

        if train:
            optimizer = tf.keras.optimizers.legacy.Adam(learning_rate=0.001)
            self.loss_array = train_model(
                self.X_,
                self.B_,
                self.model,
                optimizer,
                gamma=0.9,
                n_epochs=epochs
            )

            self.tau_model = self.model.tau
            self.bundle_tau = True
            self.change_mapping(self.model.tau)
            if use_predictor:
                self.useBundlePredictor()
        return self.model

    def plot_loss(self):
        if self.model is not None:
            plt.figure()
            for i, label in enumerate(
                    ["$\mathcal{L}_{{Markov}}$", "$\mathcal{L}_{{Behavior}}$", "Total loss $\mathcal{L}$"]):
                plt.semilogy(self.loss_array[:, i], label=label)
            plt.legend()
            plt.show()
        else:
            print('No model was trained.')

    def train_model(self, epochs=2000, learning_rate=0.001):
        optimizer = tf.keras.optimizers.legacy.Adam(learning_rate=learning_rate)
        self.loss_array = train_model(
            self.X_,
            self.B_,
            self.model,
            optimizer,
            gamma=0.9,
            n_epochs=epochs
        )
        self.tau_model = self.model.tau
        self.bundle_tau = True

    def use_latent_dim_as_input(self):
        if self.bundle_tau:
            names = np.asarray([f'axis{i}' for i in range(self.transformed_points.shape[0])])
            ###
            print('X', self.transformed_points.shape)
            print('Y', self.B_.shape)
            print('Y-names', self.data.states.shape)
            print('X-names', names.shape)

        else:
            print('Attach a bundleNet first!')
            return False

        return Database(self.transformed_points, self.B_, names, self.data.states, self.data.fps)

        exit()

        new_data = copy.copy(self)

        ###
        # We need to trim labs and colors if we have a Bundle
        if len(self.x) < len(self.data.colors):
            window = len(self.data.colors) - len(self.x)
            self.plot_colors = self.data.colors[window:]
        else:
            self.plot_colors = self.data.colors
        ###
        transformed_points = np.asarray(self.mapping(self.X_[:, 0]))
        ###
        self.x, self.y, self.z = transformed_points.T
        ###

    def _add_quivers3D(self, ax, x, y, z, colors=None):
        if colors is None:
            colors = self.data.colors[:-1]

        dx = np.diff(x)  # Differences between x coordinates
        dy = np.diff(y)  # Differences between y coordinates
        dz = np.diff(z)  # Differences between z coordinates
        # we do this so each arrowhead has the same size independent of the size of the arrow
        lengths = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

        if 0 in lengths:
            print('we replace zeros')
            zero_indices = np.where(lengths == 0)
            print(zero_indices)
            print(lengths[zero_indices])

        epsilon = 1e-8
        lengths[lengths == 0] = epsilon

        mean_length = np.mean(lengths)
        print(0.05, ' or ', mean_length)
        lengths = mean_length / lengths
        for idx in range(len(dx)):
            ax.quiver(x[idx], y[idx], z[idx], dx[idx], dy[idx], dz[idx], color=colors[idx],
                      arrow_length_ratio=lengths[idx], alpha=0.8, linewidths=0.8)

        return ax

    def make_movie(self, interval=None, save=False, show_legend=False, grid_off=True, quivers=False):
        """
        Makes a movie out of each frame in the imaging data. It uses the tau model or a model given as a parameter to
        map the data to a 3-dimensional space.
        """
        if self.transformed_points.shape[0] != 3:
            print('The mapping does not map into a 3D space.')
            return False

        if interval is None:
            if self.data.fps is not None:
                print('The movie well be played in real time.')
                interval = 1000 / self.data.fps
            else:
                interval = 10
        self.interval = interval
        fig, self.movie_ax, legend_elements = self.plot_mapping(show_legend=show_legend,
                                                                grid_off=grid_off,
                                                                quivers=quivers,
                                                                show=False)

        self.scatter = None
        self.animation = anim.FuncAnimation(fig, self._update,
                                            fargs=(grid_off, legend_elements,),
                                            # frames=len(self.x),
                                            frames=self.transformed_points.shape[1],
                                            interval=self.interval)
        plt.show()
        if save:
            name = str(input('What should the movie be called?')) + '.gif'
            self.save_gif(name)
        return True

    def _update(self, frame, grid_off, legend_elements):
        if self.scatter is not None:
            self.scatter.remove()

        x, y, z = self.transformed_points[:, frame]
        self.scatter = self.movie_ax.scatter(x, y, z, s=20, alpha=0.8, color='red')
        # self.scatter = self.movie_ax.scatter(self.x[frame], self.y[frame], self.z[frame], s=20, alpha=0.8, color='red')
        self.movie_ax.set_title(f'Frame: {frame}\nBehavior: {self.data.states[self.data.B[frame]]}')

        if legend_elements:
            self.movie_ax.legend(handles=legend_elements, loc='best')

        if grid_off:
            self.movie_ax.grid(False)
            self.movie_ax.set_axis_off()
        else:
            self.movie_ax.set_xlabel('Axes 1')
            self.movie_ax.set_ylabel('Axes 2')
            self.movie_ax.set_zlabel('Axes 3')

        return self.movie_ax

    def save_gif(self, name, bitrate=1800, dpi=144):
        if self.animation is None:
            print('No animation created yet.\nTo create one use \'.make_movie()\'.')
        else:
            print('This may take a while...')
            path = 'movies/' + name + '.gif'
            gif_writer = anim.PillowWriter(fps=int(1000 / self.interval), metadata=dict(artist='Me'), bitrate=bitrate)
            self.animation.save(path, writer=gif_writer, dpi=dpi)

    def useBundlePredictor(self):
        if self.bundle_tau:
            window = self.X_.shape[2]
            Yt1_upper, Yt1_lower, Bt1_upper = self.model.call(self.X_)
            B_pred_new = np.argmax(Bt1_upper, axis=1).astype(int)
            self.pred_model = self.model
            self.B_pred = B_pred_new
            return True
        else:
            print('It seems there is no BundleNet attached yet. Use \'Visualizer.attachBundleNet()\'!')
            return False

    def make_comparison(self, show_legend=False, quivers=True):
        if self.transformed_points.shape[0] != 3:
            print('The mapping does not map into a 3D space.')
            return False

        if self.pred_model is None:
            if self.data.pred_model is not None:
                self.pred_model = self.data.pred_model
                self.B_pred = self.data.B_pred
            else:
                print('There was no prediction model attached to the Database-object. Either use fit_model on the '
                      'Database object or use useBundlePredictor on the Visualizer if you attached a BundleNet')
                return False

        # Creating differences in lengths needed for correct plotting of the model/mapping
        reform = False
        win_plot_p = len(self.B_pred) - self.transformed_points.shape[1]
        if win_plot_p < 0:
            # This handles the exception when a BundleNet predictor is used for prediction but the points are plotted
            # using a dim-reduction that will not reduce the amount of points
            reform = True
            t = abs(win_plot_p)
            self.transformed_points = self.transformed_points[:, t:]
            win_plot_p = 0
        win_plot_t = len(self.data.B) - self.transformed_points.shape[1]
        win_pred = len(self.data.B) - len(self.B_pred)

        # Calculating differences between prediction and true label - generating the coloring for the 3 plots
        diff_mask = self.data.B[win_plot_t:] != self.B_pred[win_plot_p:]
        diff_predicts = np.where(diff_mask, self.data.B[win_plot_t:], -1)
        self.plot_colors = self.data.colors[win_plot_t:]
        self.colors_pred = [self.data.colordict[val] for val in self.B_pred[win_plot_p:]]
        self.colors_diff_pred = [self.data.colordict[val] if val > -1 else (0.85, 0.85, 0.85) for val in
                                 diff_predicts]
        self._generate_diff_label_counts(diff_predicts)

        # print(f'All these colors should be the same shape: {len(self.plot_colors), len(self.colors_pred), len(self.colors_diff_pred)}')

        fig = plt.figure(figsize=(12, 8))

        # First subplot
        ax1 = fig.add_subplot(131, projection='3d')
        ax2 = fig.add_subplot(132, projection='3d')
        ax3 = fig.add_subplot(133, projection='3d')

        # True Labels
        ax1.grid(False)
        ax1.set_axis_off()
        if quivers:
            ax1 = self._add_quivers3D(ax1, *self.transformed_points, colors=self.plot_colors)
        else:
            ax1.scatter(*self.transformed_points, label=self.data.states, s=1, alpha=0.5, color=self.plot_colors)
        ax1.set_title(f'True Label')
        # Difference
        ax2.grid(False)
        ax2.set_axis_off()
        if quivers:
            ax2 = self._add_quivers3D(ax2, *self.transformed_points, colors=self.colors_diff_pred)
        else:
            ax2.scatter(*self.transformed_points, label=self.data.states, s=1, alpha=0.5, color=self.colors_diff_pred)
        ax2.set_title(f'\nModel: {type(self.pred_model)}\n'
                      f'Mapping: {type(self.mapping)}\n\n'
                      f'Accuracy at {round(accuracy_score(self.data.B[win_pred:], self.B_pred), 3)}\n')
        # Predictions
        ax3.grid(False)
        ax3.set_axis_off()
        if quivers:
            ax3 = self._add_quivers3D(ax3, *self.transformed_points, colors=self.colors_pred)
        else:
            ax3.scatter(*self.transformed_points, label=self.data.states, s=1, alpha=0.5, color=self.colors_pred)
        ax3.set_title(f'Predicted Label')

        # plot the legend if wanted
        if show_legend:
            legend_1 = self._generate_legend(self.data.B)
            ax1.legend(title='True Labels', handles=legend_1, loc='upper center', bbox_to_anchor=(0.5, 0.))

            legend_2 = self._generate_legend(None, diff=True)
            ax2.legend(title='Incorrect Predictions', handles=legend_2, loc='upper center', bbox_to_anchor=(0.5, 0.))

            legend_3 = self._generate_legend(self.B_pred)
            ax3.legend(title='Predicted Labels', handles=legend_3, loc='upper center', bbox_to_anchor=(0.5, 0.))

        fig.suptitle(f'{self.transformed_points.shape[1]} Frames', fontsize='x-large', fontweight='bold')
        plt.show()
        if len(self.B_pred) - len(self.B_pred[win_plot_p:]) > 0:
            print(
                f'Some points {len(self.B_pred) - len(self.B_pred[win_plot_p:])} used for accuracy calculation of the model '
                f'are not plotted, since the mapping does not include them.')

        if reform:
            print(f'The prediction has fewer points than the true labels. Therefore {t} points are not plotted and also'
                  f' not used for accuracy calculation of the model')
            self._transform_points(self.mapping)
        return True


class CustomEnsembleModel:
    """
    This ensemble takes a model and creates binary predictors for each label-combination.
    As a prediction for each instance it gives the most abundant prediction from its sub-models.
    """

    def __init__(self, base_model):
        """
        :param base_model: a model from which the binary classifiers will be built (e.g. Logistic Regression)
        """
        self.base_model = base_model
        self.combinatorics = []
        self.ensemble_models = []

    def fit(self, neuron_traces, labels):
        self.ensemble_models = []
        self.combinatorics = list(combinations(np.unique(labels), 2))
        for idx, class_mapping in enumerate(self.combinatorics):
            b_model = clone(self.base_model)
            mapped_labels = np.array([label if label in class_mapping else -1 for label in labels])
            mask = mapped_labels != -1
            # apply mask to the dataset and only use instances of 'A' or 'B' to train
            neuron_traces_filtered = neuron_traces[mask]
            mapped_labels_filtered = mapped_labels[mask]
            b_model.fit(neuron_traces_filtered, mapped_labels_filtered)
            self.ensemble_models.append(b_model)
        return self

    def predict(self, neuron_traces):
        results = np.zeros((neuron_traces.shape[0], len(self.combinatorics))).astype(int)
        for idx, b_model in enumerate(self.ensemble_models):
            results[:, idx] = b_model.predict(neuron_traces)
        return [np.bincount(results[row, :]).argmax() for row in range(results.shape[0])]

    def predict_proba(self, neuron_traces):
        y_prob_map = np.zeros((neuron_traces.shape[0], len(self.combinatorics)))
        for idx, model in enumerate(self.ensemble_models):
            prob = model.predict_proba(neuron_traces)[:, 0]
            y_prob_map[:, idx] = prob
        return y_prob_map
