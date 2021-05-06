# -*- coding: utf-8 -*-
import arcpy
from arcpy.sa import *
import shutil
import tempfile

class Toolbox(object):
    def __init__(self):
        """
        This toolbox contains a single tool that returns a change detection image from two succeeding VV and VH
        Sentinel-1 SAR Granules.
        """
        self.label = "CreateChangeDetectionImage"
        self.alias = "CreateChangeDetectionImage"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]

class Tool(object):
    def __init__(self):
        """

        """
        self.label = "CreateChangeDetectionImageMSSmall"
        self.description = "Tool to create exaggerated change detection image using MSSmall rescaling of difference " \
                           "raster data-sets."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """
        param 1: VVRef- This is the VV polarity of a Sentinel-1 raster that was acquired on the reference date
        param 2: VHRef- This is the VH polarity of a Sentinel-1 raster that was acquired on the reference date
        param 3: VVAct- This is the VV polarity of a Sentinel-1 raster that was acquired on the activity date
        param 4: VHAct- This is the VH polarity of a Sentinel-1 raster that was acquired on the activity date
        param 5: PolyMask- This is a polygon mask that may be used to limit the extent of returned raster to only
                           include areas that are of interest to avalanche researchers/forecasters
        """

        param0 = arcpy.Parameter(
            displayName="VVRef",
            name="vv_ref",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="VHRef",
            name="vh_ref",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="VVAct",
            name="vv_act",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="VHAct",
            name="vh_act",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Polygon Mask",
            name="poly_mask",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Output Raster",
            name="out_ras",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5]
        return params

    def isLicensed(self):
        """This tool requires the Spatial Analyst Extension"""
        arcpy.AddMessage("Checking Spatial Analyst Extension status...")
        try:
            if arcpy.CheckExtension("Spatial") != "Available":
                raise Exception
            else:
                arcpy.AddMessage("Spatial Analyst Extension is available.")
                if arcpy.CheckOutExtension("Spatial") == "CheckedOut":
                    arcpy.AddMessage("Spatial Analyst Extension is checked out and ready for use.")
                elif arcpy.CheckOutExtension("Spatial") == "NotInitialized":
                    arcpy.CheckOutExtension("Spatial")
                    arcpy.AddMessage("Spatial Analyst Extension has been checked out.")
                else:
                    arcpy.AddMessage("Spatial Analyst Extension is not available for use.")
        except Exception:
            arcpy.AddMessage(
                "Spatial Analyst extension is not available for use. Check your licensing to make sure you have "
                "access to this extension.")
            return False

        return True

    def make_tempdir(self):
        """creates and returns a temporary directory"""
        try:
            tempdir = tempfile.mkdtemp()
            return tempdir
        except Exception as e:
            arcpy.AddError(str(e))

    def del_tempdir(self, tempdir):
        """deletes an entire directory tree"""
        try:
            shutil.rmtree(tempdir)
            return True
        except Exception as e:
            arcpy.AddError(str(e))

    def execute(self, parameters, messages):
        """"""
        ref_vv = parameters[0].valueAsText
        ref_vh = parameters[1].valueAsText
        act_vv = parameters[2].valueAsText
        act_vh = parameters[3].valueAsText
        poly_mask = parameters[4].valueAsText
        out_ras = parameters[5].valueAsText

        temp_dir = self.make_tempdir()
        work_gdb = arcpy.management.CreateFileGDB(temp_dir, 'temp.gdb')[0]

        try:
            arcpy.env.workspace = work_gdb
            # executing minus functions
            vv_minus = Minus(act_vv, ref_vv)
            vh_minus = Minus(act_vh, ref_vh)

            # executing intitial rescale
            vv_minus_rescale_1_255 = RescaleByFunction(vv_minus, TfLinear(), from_scale=1, to_scale=255)
            vh_minus_rescale_1_255 = RescaleByFunction(vh_minus, TfLinear(), from_scale=1, to_scale=255)

            vv_minus_rescale_0_1_mssmall = RescaleByFunction(vv_minus, TfMSSmall(), from_scale=0, to_scale=1)
            vh_minus_rescale_0_1_mssmall = RescaleByFunction(vh_minus, TfMSSmall(), from_scale=0, to_scale=1)

            vv_square_mssmall = Square(vv_minus_rescale_0_1_mssmall)
            vh_square_mssmall = Square(vh_minus_rescale_0_1_mssmall)

            # executing times functions
            mssmall_times = Times(vv_square_mssmall, vh_square_mssmall)

            mssmall_times_rgb = RescaleByFunction(mssmall_times, TfLinear(), from_scale=1, to_scale=255)

            result = arcpy.management.CompositeBands([vv_minus_rescale_1_255,
                                             mssmall_times_rgb,
                                             vh_minus_rescale_1_255],
                                            '{}\\training_image_mssmall_composite'.format(work_gdb))

            if poly_mask:
                result = arcpy.management.Clip(result, "#",
                                                 "{}//clip.tif".format(temp_dir),
                                                 poly_mask, "0",
                                                 "ClippingGeometry")

            cd_ras = arcpy.management.CopyRaster(result, out_ras, pixel_type='8_BIT_UNSIGNED')[0]
            return cd_ras

        except Exception as e:
            print(str(e))

        finally:
            if temp_dir:
                self.del_tempdir(temp_dir)