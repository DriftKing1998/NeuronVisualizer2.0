# NC-MCM-Visualizer 
<a href=https://github.com/DriftKing1998/NC-MCM-Visualizer>See on GitHub</a>
## A toolbox to visualize neuronal imaging data and apply the NC-MCM framework to it

This is a toolbox uses neuronal & behavioral data and visualizes it. NCMCM stands for Neuro-Cognitive Multilevel-Causel-Modeling, but also for: 
* `N`umerous options to visualize neuronal data and create diagnostic plots 
* `C`reating neural manifolds using `sklearn` dimensionality reduction algorithms or `BunDLeNet`
* `M`ake interactive behavioral state diagrams using `pyvis`
* `C`luster behavioral probability trajectories and test them for non-markovianity
* `M`ovies of behavioral/neuronal trajectories saved as `.gif`-files


## Getting Started (for end-users)
1. **Installation:** Open a terminal window in your Python project directory and run
    ```
    pip install ncmcm
    ```
2. **Importing the package:** In your Python script or notebook, import the package
    ```
    import ncmcm as nc
    ```
3. **Usage:** Now you can already start with creating a `Database` instance with your data, to start your analysis:
   ```
   db = nc.Database(neuron_traces=X, behavior=B, neuron_names=x_names, states=b_names, fps=fps)
   ```
   Or you can use one of the 5 the included C.elegans dataset to explore the package:
   ```
   loaded_data = Loader(data_set_no=1)
   nc.Database(*loaded_data.data)
   ```
4. **Structure:** the framework is divided into three main parts which can be imported separately:
   - **Cognitive Graphs and 3D Visualizations:** This includes the classes necessary for creating cognitive graphs and 3D visualizations. These are available under the module: `ncmcm.ncmcm_classes` 
   - **Helper Functions:** These are functions that are used by some of the classes and can also be accessed independently. You can find them under: `ncmcm.helpers` 
   - **BunDLe-Net:** This module is used to create Markovian 3D embeddings and is accessible via: `ncmcm.bundlenet`

5. **Tutorial:** Check out the demo-notebooks on the GitHub (<a href=https://github.com/DriftKing1998/NC-MCM-Visualizer/tree/main/demos>here</a>). They serve as a useful starting point to explore the functionalities of `ncmcm`.

## Installation and usage information (for contributors)

If you're interested in contributing to this project or creating your own versions based on the existing code, follow these steps:

### Installation

1. **Clone the Repository**: 
   Clone this repository to your local machine using Git:
   ```
   git clone https://github.com/DriftKing1998/NC-MCM-Visualizer.git
   ```

2. **Install Dependencies**: 
   Navigate to the project directory and install the required dependencies using pip:
   ```
   cd <project_directory>
   pip install -r requirements.txt
   ```

### New Branches

1. **Explore the Code**:
    <br>`ncmcm.ncmcm_classes` module contains the classes used by ncmcm:
   1. `Loader` can be used to load data from a certain MATLAB-file.
   2. `Database` is a container for data, which can be used to generate the behavioral probability maps by adding a sklearn-model. It also allows to create different plots and diagnostics.
   3. `Visualizer` is created by adding a mapping or a BundDLeNet (=default). It allows to create 3D plots and movies.
   4. `CustomEnsembleModel` is a model that creates an ensemble of models, specializing each model to detect a label.

    <br>`ncmcm.helpers` module contains some auxiliary functions:
   1. Functions to prepare data
   2. Functions to test for stationarity & non-markovianity
   3. Plotting functions for the tests
   4. And many more...

    <br>`ncmcm.BundDLeNet` module contains all the parts of BundDLeNet:
   1. Class for creating/training the model 
   2. Functions to prep data and get loss
    
2. **Make Changes**:
   Make your desired changes or enhancements to the codebase. Feel free to add new features, fix bugs, or improve documentation.

3. **Testing**:
   Ensure that your changes are tested thoroughly. You can run existing tests or write new ones to validate your modifications.

4. **Create a Branch**:
   Create a new branch for your changes:
   ```
   git checkout -b <new_branch>
   ```

5. **Commit Your Changes**:
   Once you're satisfied with your changes, commit them to your branch:
   ```
   git add .
   git commit -m "description of changes"
   ```

6. **Push Changes**:
   Push your changes to your forked repository:
   ```
   git push origin <new_branch>
   ```
### Add to the Codebase
Since this project is a first step, any additions are more than welcome. 
1. **Pull request**:
   Go to the repository and open a pull request from your branch. Provide a clear description of your changes and why they're beneficial.

2. **Review**:
   Await feedback from me and address any requested changes. Once approved, your changes will be merged into the main branch.

###### This project was created as part of the masters project of *Hofer Michael* 
