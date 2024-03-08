from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from ncmcm.classes import *
from IPython.display import display
import os
import pickle
os.chdir('..')
os.chdir('ncmcm')
print(os.getcwd())


worm_num = 1
matlab = Loader(worm_num)
data = Database(*matlab.data)

time, newX = preprocess_data(data.neuron_traces.T, data.fps)
sum_array = np.sum(newX, axis=1)
noise = np.random.normal(0, 0.1, size=sum_array.shape)
sum_array_with_noise = sum_array + noise
B = (sum_array_with_noise - np.min(sum_array_with_noise)) / (np.max(sum_array_with_noise) - np.min(sum_array_with_noise))

X_, B_ = prep_data(newX, B, win=15)
model = BundDLeNet(latent_dim=3, behaviors=1)
model.build(input_shape=X_.shape)

optimizer = tf.keras.optimizers.legacy.Adam(learning_rate=0.001)
loss_array = train_model(
    X_,
    B_,
    model,
    optimizer,
    gamma=0.9,
    n_epochs=1000
)

vs = Visualizer(data, model.tau, transform=False)
vs.X_ = X_
vs.B_ = B_
vs.model = model
vs.loss_array = loss_array
vs.tau_model = model.tau
vs.bn_tau = True
# I need to do this later, since X_ is not defined yet
vs._transform_points(vs.mapping)
vs.useBundDLePredictor()

vs.plot_mapping(show_legend=True)
vs.make_comparison(show_legend=True)




exit()
# Do some cool plots

worm_num = 1
matlab = Loader(worm_num)
data = Database(*matlab.data)
#data.behavioral_state_diagram(save=True, show=False, adj_matrix=True)
rf = RandomForestClassifier()
et = ExtraTreesClassifier()
lg = LogisticRegression()
data.fit_model(rf, binary=False)

vs1 = data.createVisualizer(PCA(n_components=3))

vs1.make_comparison(show_legend=True)
data.fit_model(et, binary=True)
vs1.make_comparison(show_legend=True)
data.fit_model(lg, binary=False)
vs1.make_comparison(show_legend=True)
exit()
vs1.plot_mapping()

data_small = vs1.use_mapping_as_input()
logreg = LogisticRegression()
data_small.fit_model(logreg)

data_small.cluster_BPT(nrep=10, max_clusters=15)