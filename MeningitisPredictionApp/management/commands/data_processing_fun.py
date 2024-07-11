#from django.core.management.base import BaseCommand
#from ecmwf.opendata import Client
#import ecmwf.data as ecdata
from eccodes import *
import rasterio
import fiona
from rasterio.mask import mask
import numpy as np
from osgeo import gdal
import os


# Function to decompress ccds grib2 to simple grib2
def ccds_to_simple (input_file, output_file):
    with open(input_file, "rb") as f:
        # Create a GRIB handle for the input file
        gid = codes_grib_new_from_file(f)

        # Get the values for the entire message
        values = codes_get_values(gid)

        # Set the packing type to "grid_simple" for the parameter
        codes_set(gid, "packingType", "grid_simple")

        # Set the values for the parameter
        codes_set_values(gid, values)

        # Write the modified GRIB message to the output file
        with open(output_file, "wb") as fout:
            codes_write(gid, fout)

        # Release resources
        codes_release(gid)


# Function to transform a grib2 file into a GeoTIFF file
def transform_grib2_to_TIFF (grib2_file, TIFF_output_file):
    src_ds = gdal.Open(grib2_file)
    dst_filename = TIFF_output_file
    
    # Ensure number of bands in GeoTiff will be same as in GRIB file. 
    bands = [] # Set up array for gdal.Translate(). 
    if src_ds is not None:
        bandNum = src_ds.RasterCount # Get band count
    for i in range(bandNum+1): # Update array based on band count
        if (i==0): #gdal starts band counts at 1, not 0 like the Python for loop does.
            pass
        else:
            bands.append(i)
    
    # Open output format driver
    out_form= "GTiff"
    
    # Output to new format using gdal.Translate.
    dst_ds = gdal.Translate(dst_filename, src_ds, format=out_form, bandList=bands)
    
    # Properly close the datasets to flush to disk
    dst_dsTemp = None
    src_dsTemp = None


# Function to clip the raster files to the outlines of Africa
def create_mask_from_shapefile(shapefile_filepath, corresponding_orthomosaic_filepath, output_file):

    # open shapefile
    with fiona.open(shapefile_filepath, 'r') as shapefile:
        shapes = [feature['geometry'] for feature in shapefile]

    # open rasterfile
    with rasterio.open(corresponding_orthomosaic_filepath, 'r') as src:
        out_image, out_transform = mask(src, shapes, crop=True, nodata=np.nan) # setting all pixels outside of the feature zone to nan
        out_meta = src.meta

    out_meta.update({"driver": "GTiff",
    "height": out_image.shape[1],
    "width": out_image.shape[2],
    "transform": out_transform})

    output_file = output_file

    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(out_image)


# function that multiplies every pixel of the raster by a scalar
def multiply_raster_by_scalar(input_raster, output_raster, scalar):
    # Get current directory
    current_directory = os.getcwd()
    
    # Construct full paths for output rasters
    #input_raster_path = os.path.join(current_directory, input_raster_filename)
    #output_raster_path = os.path.join(current_directory, output_raster_filename)
    
    with rasterio.open(input_raster) as src:
        # Read raster data
        raster_data = src.read(1)

        # Apply scalar multiplication
        modified_raster_data = raster_data * scalar

        # Get metadata
        profile = src.profile
        
        # Convert the data type of the modified array to match the data type of the output raster file
        modified_raster_data = modified_raster_data.astype(profile['dtype'])

    # Write the modified raster to output file
    with rasterio.open(output_raster, 'w', **profile) as dst:
        dst.write(modified_raster_data, 1)

    print("Raster multiplication completed successfully.")


# Funtion that substract a scalar from every pixel in the raster file
def subtract_scalar_from_raster(input_raster, output_raster_filename, scalar):
    # Get current directory
    current_directory = os.getcwd()
    
    # Construct full paths for output rasters
    #input_raster_path = os.path.join(current_directory, input_raster_filename)
    output_raster_path = os.path.join(current_directory, output_raster_filename)
    
    with rasterio.open(input_raster) as src:
        # Read raster data
        raster_data = src.read(1)

        # Apply scalar multiplication
        modified_raster_data = raster_data - scalar

        # Get metadata
        profile = src.profile
        
        # Convert the data type of the modified array to match the data type of the output raster file
        modified_raster_data = modified_raster_data.astype(profile['dtype'])

    # Write the modified raster to output file
    with rasterio.open(output_raster_path, 'w', **profile) as dst:
        dst.write(modified_raster_data, 1)

    print("Raster substraction completed successfully.")


def resample_resolution(inputFilename, outputFilename):
    # open reference file and get resolution
    dirname = os.getcwd()
    referenceFile = os.path.join(dirname,"IntermediateDataFiles", "RH_fc_weekly_mean_mask.tif")
    reference = gdal.Open(referenceFile, 0)  # this opens the file in only reading mode
    print(type(reference))
    referenceTrans = reference.GetGeoTransform()
    x_res = referenceTrans[1]
    y_res = -referenceTrans[5]  # make sure this value is positive

    # get reference raster size
    ref_cols = reference.RasterXSize
    ref_rows = reference.RasterYSize
    
    # call gdal Warp
    kwargs = {"format": "GTiff", "xRes": x_res, "yRes": y_res, "outputBounds": [referenceTrans[0], referenceTrans[3] - ref_rows * y_res, referenceTrans[0] + ref_cols * x_res, referenceTrans[3]]}
    ds = gdal.Warp(outputFilename, inputFilename, **kwargs)

# resulting raster still shows some missing pixels at the borders where RH/2tm raster has pixels
# will this be a problem during risk map computation?


# Function that calculates the risk map based on the categories defined by Dione et al.
def compute_risk_map(twomt_inputFile, rh_inputFile, sdc_inputFile, riskMap_outputFile):
# 1 - highest risk level
# 9 - lowest risk level
# nodata - assigned to pixels that don't meet any of the conditions

    # Load the three input raster files
    with rasterio.open(twomt_inputFile) as src_2mt, \
         rasterio.open(rh_inputFile) as src_RH, \
         rasterio.open(sdc_inputFile) as src_dustmass:

        # Read raster data as numpy arrays
        data1 = src_2mt.read(1)
        data2 = src_RH.read(1)
        data3 = src_dustmass.read(1)

        # fill an array with 9999 (which will also become the nodata value) for the outputfile
        nodata_value = 9999
        output_data = np.full_like(data1, nodata_value, dtype=np.int16)
        
        # Define the threshold conditions and output values
        # Output_data file array of 9999s will be filled with these new values for pixels that meet the conditions
        # pixels that do not meet any condition will continue to have a value of 9999 = nodatas
        # Vigilence levels rank from pixel value=1 (highest risk) to =9(lowest risk)

        # Condition 1
        mask = (data1 >= 30) & (data2 <= 20) & (data3 >= 400)
        output_data[mask] = 1
        
        # Condition 2
        mask = (27 < data1) & (data1 < 30) & (data2 <= 20) & (data3 >= 400)
        output_data[mask] = 2
        
        # Condition 3
        mask = (data1 >= 30) & (data2 <= 20) & (150 < data3) & (data3 < 400)
        output_data[mask] = 3
        
        # Condition 4
        mask = (data1 >= 30) & (40 < data2) & (data2 <= 60) & (data3 >= 400)
        output_data[mask] = 4
        
        # Condition 5
        mask = (27 < data1) & (data1 < 30) & (20 < data2) & (data2 <= 40) & (150 < data3) & (data3 < 400)
        output_data[mask] = 5
        
        # Condition 6
        mask = (data1 > 27) & (data2 < 60) & (data3 < 150)
        output_data[mask] = 6
        
        # Condition 7
        mask = (data1 > 27) & (40 < data2) & (data2 <= 60) & (150 < data3) & (data3 < 400)
        output_data[mask] = 7
        
        # Condition 8
        mask = (data2 > 60)
        output_data[mask] = 8
        
        # Condition 9
        mask = (data1 < 27)
        output_data[mask] = 9
        
        # Create a new GeoTIFF file for the output
        # set the nodata value to 9999
        with rasterio.open(riskMap_outputFile, 'w', driver='GTiff', 
                            width=src_2mt.width, height=src_2mt.height,
                            nodata = 9999,
                            count=1, dtype=rasterio.int16, 
                            crs=src_2mt.crs, transform=src_2mt.transform) as dst:
            
            # Write the output data to the output raster
            dst.write(output_data, 1)

        