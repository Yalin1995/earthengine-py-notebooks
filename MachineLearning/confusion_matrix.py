'''
<table class="ee-notebook-buttons" align="left">
    <td><a target="_blank"  href="https://github.com/giswqs/earthengine-py-notebooks/tree/master/MachineLearning/confusion_matrix.ipynb"><img width=32px src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" /> View source on GitHub</a></td>
    <td><a target="_blank"  href="https://nbviewer.jupyter.org/github/giswqs/earthengine-py-notebooks/blob/master/MachineLearning/confusion_matrix.ipynb"><img width=26px src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Jupyter_logo.svg/883px-Jupyter_logo.svg.png" />Notebook Viewer</a></td>
    <td><a target="_blank"  href="https://mybinder.org/v2/gh/giswqs/earthengine-py-notebooks/master?filepath=MachineLearning/confusion_matrix.ipynb"><img width=58px src="https://mybinder.org/static/images/logo_social.png" />Run in binder</a></td>
    <td><a target="_blank"  href="https://colab.research.google.com/github/giswqs/earthengine-py-notebooks/blob/master/MachineLearning/confusion_matrix.ipynb"><img src="https://www.tensorflow.org/images/colab_logo_32px.png" /> Run in Google Colab</a></td>
</table>
'''

# %%
'''
## Install Earth Engine API
Install the [Earth Engine Python API](https://developers.google.com/earth-engine/python_install) and [geehydro](https://github.com/giswqs/geehydro). The **geehydro** Python package builds on the [folium](https://github.com/python-visualization/folium) package and implements several methods for displaying Earth Engine data layers, such as `Map.addLayer()`, `Map.setCenter()`, `Map.centerObject()`, and `Map.setOptions()`.
The magic command `%%capture` can be used to hide output from a specific cell.
'''


# %%
# %%capture
# !pip install earthengine-api
# !pip install geehydro

# %%
'''
Import libraries
'''


# %%
import ee
import folium
import geehydro

# %%
'''
Authenticate and initialize Earth Engine API. You only need to authenticate the Earth Engine API once. Uncomment the line `ee.Authenticate()` 
if you are running this notebook for this first time or if you are getting an authentication error.  
'''


# %%
# ee.Authenticate()
ee.Initialize()

# %%
'''
## Create an interactive map 
This step creates an interactive map using [folium](https://github.com/python-visualization/folium). The default basemap is the OpenStreetMap. Additional basemaps can be added using the `Map.setOptions()` function. 
The optional basemaps can be `ROADMAP`, `SATELLITE`, `HYBRID`, `TERRAIN`, or `ESRI`.
'''

# %%
Map = folium.Map(location=[40, -100], zoom_start=4)
Map.setOptions('HYBRID')

# %%
'''
## Add Earth Engine Python script 

'''

# %%
# Define a region of interest as a point.  Change the coordinates
# to get a classification of any place where there is imagery.
roi = ee.Geometry.Point(-122.3942, 37.7295)

# Load Landsat 5 input imagery.
landsat = ee.Image(ee.ImageCollection('LANDSAT/LT05/C01/T1_TOA')
  # Filter to get only one year of images. \
  .filterDate('2011-01-01', '2011-12-31')
  # Filter to get only images under the region of interest. \
  .filterBounds(roi)
  # Sort by scene cloudiness, ascending. \
  .sort('CLOUD_COVER')
  # Get the first (least cloudy) scene. \
  .first())

# Compute cloud score.
cloudScore = ee.Algorithms.Landsat.simpleCloudScore(landsat).select('cloud')

# Mask the input for clouds.  Compute the min of the input mask to mask
# pixels where any band is masked.  Combine that with the cloud mask.
input = landsat.updateMask(landsat.mask().reduce('min').And(cloudScore.lte(50)))

# Use MODIS land cover, IGBP classification, for training.
modis = ee.Image('MODIS/051/MCD12Q1/2011_01_01') \
    .select('Land_Cover_Type_1')

# Sample the input imagery to get a FeatureCollection of training data.
training = input.addBands(modis).sample(**{
  'numPixels': 5000,
  'seed': 0
})

# Make a Random Forest classifier and train it.
classifier = ee.Classifier.randomForest(10) \
    .train(training, 'Land_Cover_Type_1')

# Classify the input imagery.
classified = input.classify(classifier)

# Get a confusion matrix representing resubstitution accuracy.
trainAccuracy = classifier.confusionMatrix()
print('Resubstitution error matrix: ', trainAccuracy)
print('Training overall accuracy: ', trainAccuracy.accuracy())

# Sample the input with a different random seed to get validation data.
validation = input.addBands(modis).sample(**{
  'numPixels': 5000,
  'seed': 1
  # Filter the result to get rid of any {} pixels.
}).filter(ee.Filter.neq('B1', {}))

# Classify the validation data.
validated = validation.classify(classifier)

# Get a confusion matrix representing expected accuracy.
testAccuracy = validated.errorMatrix('Land_Cover_Type_1', 'classification')
print('Validation error matrix: ', testAccuracy)
print('Validation overall accuracy: ', testAccuracy.accuracy())

# Define a palette for the IGBP classification.
igbpPalette = [
  'aec3d4', # water
  '152106', '225129', '369b47', '30eb5b', '387242', # forest
  '6a2325', 'c3aa69', 'b76031', 'd9903d', '91af40',  # shrub, grass
  '111149', # wetlands
  'cdb33b', # croplands
  'cc0013', # urban
  '33280d', # crop mosaic
  'd7cdcc', # snow and ice
  'f7e084', # barren
  '6f6f6f'  # tundra
]

# Display the input and the classification.
Map.centerObject(ee.FeatureCollection(roi), 10)
Map.addLayer(input, {'bands': ['B3', 'B2', 'B1'], 'max': 0.4}, 'landsat')
Map.addLayer(classified, {'palette': igbpPalette, 'min': 0, 'max': 17}, 'classification')



# %%
'''
## Display Earth Engine data layers 

'''


# %%
Map.setControlVisibility(layerControl=True, fullscreenControl=True, latLngPopup=True)
Map