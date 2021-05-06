# This scipt iterates through the folders of all the dates and 
# orbits where SAR data was acquired to create three different change detection images as 
# well as to ptoject all the rasters into a PCS (UTM 33 N).  The three change detection 
# images are three different RGB compositions that can be used to develop training data 
# as well as visually assess if an avalanche has occurred. They are composed as follows:

# - original change detection image: 

    # - This is an RGB composite using VV backscatter images with the prior acquisition 
    # date of a given orbit in the R and B channels and the current (or activity) VV 
    # backscatter raster in the G channel.


# - exaggerated change detection (TfMSSmall transformations):

    # - This RGB composite with VVact-VVref in R and VHact-VHref in the B and the 
    # product of the rescales squares of each individual image in the G channel. 

import datetime
import os
import arcpy
from arcpy.sa import *
import shutil

arcpy.env.overwriteOutput=True

def get_path_dts(orbit_folder):
    
    """returns the list of dates where SAr data was recorded from a folder.  returned object is a list of
    datetime objects"""
    
    dates = []
    dirs = [d for d in os.listdir(orbit_folder) if os.path.isdir('{}\\{}'.format(orbit_folder, d))]
    for fldr in dirs:
        date = fldr.split('_')[-1].split('-')
        dt = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))
        dates.append(dt)
    return dates

def two_dig(num):

    """convenience function to make sure any month of day with only one character is converted to two
    in accordance with filenames of GEE downloaded data"""

    if len(str(num)) == 2:
        return num
    elif len(str(num)) == 1:
        return '0{}'.format(num)

def move_data():

    """convenience function to move SAR data from 'year' folder into 'orbit' folder based on 
    filename of the foler"""

    years = [2016,2017, 2019]

    for year in years:
        base_folder = 'D:\\new_imagery\\{}'.format(year)

        for folder in os.listdir(base_folder):
            if 'Tromsoe' in folder:
                files = os.listdir('{}\\{}'.format(base_folder, folder))
                path = files[0].split('_')[-1].split('.')[0]
            
                source = '{}\\{}'.format(base_folder, folder)
                dest = '{}\\{}'.format(base_folder, path, folder)
                print('moving {} to {}'.format(source, dest))
            
                shutil.move(source, dest)

def generate_rasters(ref_vv, act_vv, ref_vh, act_vh, out_gdb):
    
    """executes transformations of VV and VH SAR products and return change detection
    images that will be used totrain the model as well as change detection image to assist in 
    manual inspection of possible avy paths"""

    try:
        arcpy.env.workspace = arcpy.env.scratchGDB
        print('executing minus functions')
        vv_minus = Minus(act_vv, ref_vv)
        vh_minus = Minus(act_vh, ref_vh)
        
        print('executing intitial rescale ')
        vv_minus_rescale_1_255 = RescaleByFunction(vv_minus, TfLinear(), from_scale=1, to_scale=255)
        vh_minus_rescale_1_255 = RescaleByFunction(vh_minus, TfLinear(), from_scale=1, to_scale=255)
    
        vv_minus_rescale_0_1_linear = RescaleByFunction(vv_minus, TfLinear(), from_scale=0, to_scale=1)
        vh_minus_rescale_0_1_linear = RescaleByFunction(vh_minus, TfLinear(), from_scale=0, to_scale=1)
    
        vv_minus_rescale_0_1_mssmall = RescaleByFunction(vv_minus, TfMSSmall(), from_scale=0, to_scale=1)
        vh_minus_rescale_0_1_mssmall = RescaleByFunction(vh_minus, TfMSSmall(), from_scale=0, to_scale=1)
        
        print('executing square functions')
        vv_square_linear = Square(vv_minus_rescale_0_1_linear)
        vh_square_linear = Square(vh_minus_rescale_0_1_linear)
    
        vv_square_mssmall = Square(vv_minus_rescale_0_1_mssmall)
        vh_square_mssmall = Square(vh_minus_rescale_0_1_mssmall)
        
        print('executing times functions')
        linear_times = Times(vv_square_linear, vh_square_linear)
        mssmall_times = Times(vv_square_mssmall, vh_square_mssmall)
    
        linear_times_rgb = RescaleByFunction(linear_times, TfLinear(), from_scale=1, to_scale=255)
        mssmall_times_rgb = RescaleByFunction(mssmall_times, TfLinear(), from_scale=1, to_scale=255)
        
        print('generating composite rasters')
        arcpy.management.CompositeBands([ref_vv, 
                                         act_vv, 
                                         ref_vv], 
                                         '{}\\original_change_detection'.format(out_gdb))
        
        arcpy.management.CompositeBands([vv_minus_rescale_1_255, 
                                         linear_times_rgb, 
                                         vh_minus_rescale_1_255], 
                                         '{}\\training_image_linear_composite'.format(out_gdb))
        
        arcpy.management.CompositeBands([vv_minus_rescale_1_255, 
                                         mssmall_times_rgb, 
                                         vh_minus_rescale_1_255], 
                                         '{}\\training_image_mssmall_composite'.format(out_gdb))
    except Exception as e:
        print(str(e))

def generate_training_shapes(gdb):
    
    """creates an empty polygon feature class in every gdb called 'training_polys' to be manually populated
    with avalanche masks using ArcGIS Pro Editing environment."""
                    
    arcpy.management.AddField('{}\\training_rectangles'.format(gdb), 'classvalue', 'LONG')
    
    arcpy.management.CreateFeatureclass(gdb, 
                                        'training_polys', 
                                        'POLYGON', 
                                        spatial_reference=arcpy.SpatialReference(32633))
                    
    arcpy.management.AddField('{}\\training_polys'.format(gdb), 'classvalue', 'LONG')

def main():
    
    """iterates through geodatabases to create training rasters and empty polygon feature classes 
    to use in manually creating avalanche masks"""

    move_data()
    
    years = ['2016', '2017', '2019']
    orbits = ['66', '95', '131', '160']

    for year in years:
        for orbit in orbits:
            base_folder = 'D:\\new_imagery\\{}\\{}'.format(year, orbit)
            avy_dates = get_path_dts(base_folder)
            for date in avy_dates:
                folder = 'S1_Tromsoe_DEM_surface_buf_0_date_{}-{}-{}'.format(date.year, two_dig(date.month), two_dig(date.day))
                
                # set workspace to the folder with the downloded raster data
                workspace = '{}\\{}'.format(base_folder, folder)
                
                arcpy.env.workspace = workspace
                
                # create a file gdb in every folder for which there is avy data
                gdb = arcpy.management.CreateFileGDB(workspace, 
                                                    'avy_data_{}_{}_{}.gdb'.format(date.year, date.month, date.day))[0]
                print('creating {}'.format(gdb))
                
                out_sr = arcpy.SpatialReference(32633) # UTM_33_North
                in_sr = arcpy.SpatialReference(4326) # WGS 1984
                
                # project all the rasters into the proper coordinate system and store in file gdb
                for raster in arcpy.ListRasters():
                    
                    clean_raster = raster.split('.')[0].replace('-', '_')
                    out_raster = '{}\\{}_projected'.format(gdb, clean_raster) # basename of raster as gdb featureclass
                    print('creating {}'.format(out_raster))
                    
                    arcpy.management.ProjectRaster(raster, 
                                                out_raster, 
                                                out_coor_system=out_sr, 
                                                resampling_type='NEAREST',
                                                in_coor_system=in_sr)
                
            for i in range(len(avy_dates)-1):
                
                ref_date = avy_dates[i]
                act_date = avy_dates[i+1]
                
                ref_folder = folder = 'S1_Tromsoe_DEM_surface_buf_0_date_{}-{}-{}'.format(ref_date.year, 
                                                                                        two_dig(ref_date.month), 
                                                                                        two_dig(ref_date.day))
                
                act_folder = folder = 'S1_Tromsoe_DEM_surface_buf_0_date_{}-{}-{}'.format(act_date.year, 
                                                                                        two_dig(act_date.month), 
                                                                                        two_dig(act_date.day))
                
                ref_gdb = '{}\\{}\\avy_data_{}_{}_{}.gdb'.format(base_folder,
                                                            ref_folder,
                                                            ref_date.year,
                                                            ref_date.month,
                                                            ref_date.day)
                
                act_gdb = '{}\\{}\\avy_data_{}_{}_{}.gdb'.format(base_folder, 
                                                            act_folder, 
                                                            act_date.year,
                                                            act_date.month,
                                                            act_date.day)
                
                vv_base = 'VV_sigma0_'
                vh_base = 'VH_sigma0_'
                
                vv_act = '{}\\{}{}_{}_{}_{}_projected'.format(act_gdb, 
                                                            vv_base, 
                                                            act_date.year, 
                                                            two_dig(act_date.month),
                                                            two_dig(act_date.day),
                                                            orbit)
                vv_ref = '{}\\{}{}_{}_{}_{}_projected'.format(ref_gdb, 
                                                            vv_base, 
                                                            ref_date.year, 
                                                            two_dig(ref_date.month),
                                                            two_dig(ref_date.day),
                                                            orbit)
                vh_act = '{}\\{}{}_{}_{}_{}_projected'.format(act_gdb, 
                                                            vh_base, 
                                                            act_date.year, 
                                                            two_dig(act_date.month),
                                                            two_dig(act_date.day),
                                                            orbit)
                vh_ref = '{}\\{}{}_{}_{}_{}_projected'.format(ref_gdb, 
                                                            vh_base, 
                                                            ref_date.year, 
                                                            two_dig(ref_date.month),
                                                            two_dig(ref_date.day),
                                                            orbit)
                
                generate_rasters(vv_ref, vv_act, vh_ref, vh_act, act_gdb)
                generate_training_shapes(act_gdb)

if __name__ == '__main__':
    main()