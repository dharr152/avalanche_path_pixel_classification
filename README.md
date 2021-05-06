### GEE SAR Data to Detect Avalanches Using ArcGIS

#### Introduction
This repo contains python scripts and jupyter notebooks to retrieve radiometrically terrain corrected Sentinel-1 SAR data from Google Earth Engine (GEE) and process the data in an area of interest to generate UNet Classifier to detect avalanche runout zones using ArcGIS Pro software.  Much of the training data was evaluated using a proprietary shapefile as a reference so at this time that is not included in the The following outlines how to use this code to repeat this analysis. The python scripts and notebooks contain

#### Step 1: notebooks/retrieve_gee_sar_data.ipynb
This notebook contains code derived from earlier research (https://github.com/ESA-PhiLab/radiometric-slope-correction) to download Sentinel-1 SAr data from google earth engine.  The GEE python api is not compatible with default ArcGIS Pro Python libraries so this notebooks must be run from a fresh environment.  The necessary installs are contained within the notebook. The data derived from the code is made available through a users google account.  In order for all the scripts to run as written, this data must be manually downloaded and placed in a folder structure as documented in the scripts.  As written, this notebook will download up to 90 gb of data to a users google drive.  

#### Step 2: scripts/process_sar.py
The Sentinel-1 data is projected, and processed to generate change detection imaages to evaluate data for avalanche paths, and to create exaggerated change detection images that will used to train the model.  This script relies on ArcPy and must be run from an ArcGIS User with an authorized spatial analyst extension.  

#### Step 3: (manual digitization of avalanche masks)
Using the empty feature classes generated in step 2 to create avalanche masks as polygon feature using the ArcGIs Pro editing environment.  

#### Step 4: scripts/export_training_shapes.py
This script will export the manually digitized polygons and the exaggerated change detectio images as image chips to be used as inputs to train the UNet Classifier.  This script relies on the installation of deep learning python libraries in addition to ArcPy.  A user can created  a cloned environment as documented by the following resource: (https://github.com/Esri/deep-learning-frameworks)

Step 2 and Step 4 are also included as a notebook in notebooks/process_sar_export_training_data.ipynb

#### Step 5: notebooks/train_unet_model.ipynb
This notebook contains several cells that will use the exported training data to train the UNet classifier and return a trained model. 

### Additional Resources:

#### toolbox/create_detection_image.pyt

This is a toolbox that will output the appropriate change detection image to train the data or to classify pixels.  It requires the VV and VH polarity of two suceeding sentinel-1 SAR datasets, and optionally accepts a polygons mask as an input to limit the area of the output image. 

#### model/unet_sar_model

This folder contains a folder with all the content of the trained model.  The .emd or .dlpk files in the unet_sar_model folder may be used to classify pixels of the ouput from the .pyt tool.