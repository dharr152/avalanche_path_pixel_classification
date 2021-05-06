# Following the structure of the geodatabases developed in a step 2, 
# this script assumes that all possible masks have been developed in 
# feature classes called 'training_polys' in each geodatabase that 
# stores the processed SAR data.  This script will iterate through 
# the gdb's, and export all the training data based on these masks.

import os
import shutil
import arcpy
from arcpy.sa import *
from process_sar import *

arcpy.env.overwriteOutput=True

def populate_field(gdb):

    """locates feature class named 'training_polys' in geodatabase and assigns 'classvalue' field = 1 """      

    polys = '{}\\training_polys'.format(gdb)
    p_count = arcpy.management.GetCount(polys)[0]
    if int(p_count) > 0:
        arcpy.management.CalculateField(polys, 'classvalue', 1)
    
def has_detections(gdb):

    """determines if 'training_polys' feature class has any detected avalanches recorded"""

    polys = '{}\\training_polys'.format(gdb)
    p_count = arcpy.management.GetCount(polys)[0]
    if int(p_count) > 0:
        return int(p_count)
    else:
        return 0

def main():

    """iterates through gdb's, and creates a folder called training rasters omne level above to store th
    change detection images as 8-bit unsigned .tif images, and exports training chips from these images
    to a folder"""

    years = ['2016', '2017', '2019']
    orbits = ['66', '95', '131', '160']
    for year in years:
        for orbit in orbits:
            base_folder = 'D:\\new_imagery\\{}\\{}'.format(year, orbit)
            avy_dates = get_path_dts(base_folder)
            for date in avy_dates:
                folder = 'S1_Tromsoe_DEM_surface_buf_0_date_{}-{}-{}'.format(date.year, 
                                                                            two_dig(date.month), 
                                                                            two_dig(date.day))
                gdb = '{}\\{}\\avy_data_{}_{}_{}.gdb'.format(base_folder, 
                                                            folder, 
                                                            date.year, 
                                                            date.month, 
                                                            date.day)
                num = has_detections(gdb)
                if num > 0:
                    print(gdb)
                    populate_field(gdb)
                    r_folder = '{}\\{}\\training_rasters'.format(base_folder, folder)
                    if os.path.exists(r_folder):
                        shutil.rmtree(r_folder)
                    os.mkdir(r_folder)
                    print('copying rasters')
                    arcpy.management.CopyRaster('{}\\training_image_linear_composite'.format(gdb),
                                            '{}\\training_image_linear_composite.tif'.format(r_folder),
                                            pixel_type='8_BIT_UNSIGNED')
                    arcpy.management.CopyRaster('{}\\training_image_mssmall_composite'.format(gdb),
                                            '{}\\training_image_mssmall_composite.tif'.format(r_folder),
                                            pixel_type='8_BIT_UNSIGNED')
                    print('exporting training data')
                    with arcpy.EnvManager(scratchWorkspace=r"C:\\capstone\\avy_resources\\sentinelsat\\sentinel_sat\sentinel_sat.gdb", 
                        workspace=r"C:\\capstone\\avy_resources\\sentinelsat\\sentinel_sat\\sentinel_sat.gdb"):
                        arcpy.ia.ExportTrainingDataForDeepLearning(r"{}\\training_image_mssmall_composite.tif".format(r_folder), 
                                                r"D:\\new_imagery\\UNET_TRAINING_IMAGES_MSSMALL", 
                                                r"{}\\training_polys".format(gdb), 
                                                "TIFF", 
                                                128, 
                                                128, 
                                                64, 
                                                64, 
                                                "ONLY_TILES_WITH_FEATURES", 
                                                "Classified_Tiles", 
                                                0, 
                                                "classvalue", 
                                                0, 
                                                None, 
                                                0, 
                                                "MAP_SPACE", 
                                                "PROCESS_AS_MOSAICKED_IMAGE", 
                                                "NO_BLACKEN", 
                                                "FIXED_SIZE")
                    with arcpy.EnvManager(scratchWorkspace=r"C:\\capstone\\avy_resources\\sentinelsat\\sentinel_sat\sentinel_sat.gdb", 
                        workspace=r"C:\\capstone\\avy_resources\\sentinelsat\\sentinel_sat\\sentinel_sat.gdb"):
                        arcpy.ia.ExportTrainingDataForDeepLearning(r"{}\\training_image_linear_composite.tif".format(r_folder), 
                                                r"D:\\new_imagery\\UNET_TRAINING_IMAGES_LINEAR", 
                                                r"{}\\training_polys".format(gdb), 
                                                "TIFF", 
                                                128, 
                                                128, 
                                                64, 
                                                64, 
                                                "ONLY_TILES_WITH_FEATURES", 
                                                "Classified_Tiles", 
                                                0, 
                                                "classvalue", 
                                                0, 
                                                None, 
                                                0, 
                                                "MAP_SPACE", 
                                                "PROCESS_AS_MOSAICKED_IMAGE", 
                                                "NO_BLACKEN", 
                                                "FIXED_SIZE")
if __name__ == '__main__':
    main()