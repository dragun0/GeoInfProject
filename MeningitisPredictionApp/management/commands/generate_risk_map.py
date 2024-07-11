from django.core.management.base import BaseCommand
from ecmwf.opendata import Client
import ecmwf.data as ecdata
from eccodes import *
import rasterio
from rasterio.mask import mask
import numpy as np
from netCDF4 import Dataset
import xarray as xr
from netCDF4 import num2date
import os
from datetime import date
from datetime import timedelta
from django.contrib.gis.gdal import DataSource
from raster.models import RasterLayer
from django.conf import settings

from .data_processing_fun import ccds_to_simple, transform_grib2_to_TIFF, create_mask_from_shapefile, multiply_raster_by_scalar, subtract_scalar_from_raster, resample_resolution, compute_risk_map



class Command(BaseCommand):
    help = 'Fetch data, compute risk map, and store it in the database'

    def handle(self, *args, **kwargs):
        
        dirname = os.getcwd()
        #********************************************************************************************************
        # Forecast data of the past -                                                                           *
        # used for the outbreak risk predictions for week 1                                                     *
        #********************************************************************************************************

        # Fetching of NASA's GEOS-FP Assimilation Forecast data of the last 7 days of the variables: relative humidity, surface dust concentration, 2m air temperature
        
        # Relative humidity
        url_rh = 'https://opendap.nccs.nasa.gov/dods/GEOS-5/fp/0.25_deg/assim/tavg3_3d_asm_Nv'
        # Surface dust concentration
        url_dusm = 'https://opendap.nccs.nasa.gov/dods/GEOS-5/fp/0.25_deg/assim/tavg3_2d_aer_Nx'
        # 2m air temperature
        url_2mt = 'https://opendap.nccs.nasa.gov/dods/GEOS-5/fp/0.25_deg/assim/inst3_2d_asm_Nx'
        
        # Access the data for the 3 variables through the OPeNDAP server
        d_rh = xr.open_dataset(url_rh, engine='netcdf4')
        d_dusm = xr.open_dataset(url_dusm, engine='netcdf4')
        d_2mt = xr.open_dataset(url_2mt, engine='netcdf4')

        print('accessed GEOS-FP past forecasts')

        # Prepare the time slices that describe the timeframe we are interested i.e.:
        # from today-7 to yesterday (= last week)
        
        # get today's date
        today = date.today()
        # get date from 7 days ago
        seven_days_in_past = today - timedelta(days=7)
        # get yesterday's date
        yesterday = today - timedelta(days = 1)
        
        # First time step of every day = 01:30 - last time step of every day = 22:30 for relative humidity and surface concentration dataset
        slice_yesterday = '{}T22:30:00.000000000'.format(yesterday)
        slice_7d_past = '{}T01:30:00.000000000'.format(seven_days_in_past)
        # the 2mt dataset has time steps starting at 00 everyday with 3h steps
        slice_7d_past_2mt = '{}T00:00:00.000000000'.format(seven_days_in_past)

        # slice the dataset to the variable of interest('rh', 'dusmass', 't2m'), the geographic extend of africa and the temporal extend of the last 7 days
        ds_rh = d_rh.rh.sel(lat=slice(-51, 38), lon=slice(-26,78), time=slice(slice_7d_past, slice_yesterday), lev=72)
        ds_dusm = d_dusm.dusmass.sel(lat=slice(-51, 38), lon=slice(-26,78), time=slice(slice_7d_past, slice_yesterday))
        ds_2mt = d_2mt.t2m.sel(lat=slice(-51, 38), lon=slice(-26,78), time=slice(slice_7d_past, slice_yesterday))

        # compute the weekly mean values of all three variables
        ds_rh_mean = ds_rh.mean(dim='time')
        ds_dusm_mean = ds_dusm.mean(dim='time')
        ds_2mt_mean = ds_2mt.mean(dim='time')

        print('computed mean values of GEOS-FP past forecasts')

        # save the mean forecast values of all three variables of the last week to a netcdf files
        ds_rh_mean.to_netcdf(os.path.join(dirname,"IntermediateDataFiles","rh_assi_africa_past7days_mean.nc"), engine='netcdf4')
        ds_dusm_mean.to_netcdf(os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean.nc"), engine='netcdf4')
        ds_2mt_mean.to_netcdf(os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean.nc"), engine='netcdf4')

        print('stored means of past forecasts as .nc files')

        # convert the 3 nc files to tif files:

        # Construct the full path to the .nc file
        nc_file_path_assi_rh = os.path.join(dirname,"IntermediateDataFiles","rh_assi_africa_past7days_mean.nc")

        # Prepend the "netcdf:" prefix to the path
        netcdf_path_assi_rh = f"netcdf:{nc_file_path_assi_rh}"

        # turn the .nc file into a .tif file
        reader = rasterio.open(netcdf_path_assi_rh)
        prof = reader.profile
        prof.update(driver='GTiff', crs="EPSG:4326",)
        array = reader.read(1)
        with rasterio.open(os.path.join(dirname,"IntermediateDataFiles","rh_assi_africa_past7days_mean.tif"), "w", **prof) as dst:
            dst.write(array,1)

        nc_file_path_assi_dusm = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean.nc")
        netcdf_path_assi_dusm = f"netcdf:{nc_file_path_assi_dusm}"

        reader = rasterio.open(netcdf_path_assi_dusm) 
        prof = reader.profile
        prof.update(driver='GTiff', crs="EPSG:4326",)
        array = reader.read(1)
        with rasterio.open(os.path.join(dirname,"IntermediateDataFiles","dusm_assi_africa_past7days_mean.tif"), "w", **prof) as dst:
            dst.write(array,1)      

        nc_file_path_assi_2mt = os.path.join(dirname, "IntermediateDataFiles", "2mt_assi_africa_past7days_mean.nc")
        netcdf_path_assi_2mt = netcdf_path_assi_dusm = f"netcdf:{nc_file_path_assi_2mt}"

        reader = rasterio.open(netcdf_path_assi_2mt) 
        prof = reader.profile
        prof.update(driver='GTiff', crs="EPSG:4326",)
        array = reader.read(1)
        with rasterio.open(os.path.join(dirname, "IntermediateDataFiles","2mt_assi_africa_past7days_mean.tif"), "w", **prof) as dst:
            dst.write(array,1)  
        
        print('turned past forecasts .nc files into .tif files')

# turn .nc to .tif conversion into a function?
# sometimes NASA's GEOS OPeNDAP server is down. write an if statement to not proceed w the script if that is the case


        # Clip the weekly mean forecast of the past week of the 3 variables to the outlines of Africa
        input_raster_rh = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean.tif")
        output_file_rh = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean_mask.tif")
        input_shapefile = os.path.join(dirname,"AfricaOutlines", "Africa_Boundaries.shp")
        create_mask_from_shapefile(input_shapefile, input_raster_rh, output_file_rh)

        input_raster_dusm = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean.tif")
        output_file_dusm = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean_mask.tif")
        create_mask_from_shapefile(input_shapefile, input_raster_dusm, output_file_dusm)

        input_raster_2mt = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean.tif")
        output_file_2mt = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean_mask.tif")
        create_mask_from_shapefile(input_shapefile, input_raster_2mt, output_file_2mt)

        print('clipped past forecast tif files to africa')

        # multiply the relative humidity (rh) raster (nominal 0-1) by 100 to obtain unit of percentages
        input_raster_rh = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean_mask.tif")
        output_raster_rh = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean_mask_percent.tif")
        scalar_rh = 100
        multiply_raster_by_scalar(input_raster_rh, output_raster_rh, scalar_rh)

        # multiply the surface dust concentration (dusmass/sdc) raster (unit kg m^-3) by 1x10^9 to obtain unit of ug m^-3
        input_raster_dusm = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean_mask.tif")
        output_raster_dusm = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean_mask_ugm3.tif")
        scalar_sdc = 10**9
        multiply_raster_by_scalar(input_raster_dusm, output_raster_dusm, scalar_sdc)

        # substract 273.15 from 2mt raster (K) to obtain unit of celsius (C)
        input_raster_2mt = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean_mask.tif")
        output_raster_2mt = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean_mask_celsius.tif")
        scalar_2mt = 273.15
        subtract_scalar_from_raster(input_raster_2mt, output_raster_2mt, scalar_2mt)

        #------------------------------------------------------------------------
        
        #********************************************************************************************************
        # Forecast data for the future -                                                                        *
        # used for the outbreak risk predictions for week 2                                                     *
        #********************************************************************************************************

        # Fetching of ECMWF Ensemble Forecast data (for 2m air temperature and relative humidity) for the next 7 days
        
        # Data is fetched daily (after 7:55) for ref time stamp of 00 on that day for the next 7 days: 00 of the next day to 00 7 days from now
        # with reference to 00z on today that means steps: 24 to 192
        # Data is available 3 hourly for 00 to 144 and 6 hourly for 150 to 360
        # steps needed are (24, 144, 3) and (150, 192, 6)
        steps= [i for i in range (24, 144, 3)]
        steps_set2 = [i for i in range (144, 198, 6)]
        steps.extend(steps_set2)
        
        # Download 2m air temperature variable
        # Request Ensemble forecasts for the defined timesteps above
        # Setting the type to pf (perturbed forecast), cf (control forecast) will download all 50 ensemble members as well as the control forecast. (total of 51 values per step)
        # levtype = sfc = surface level or single level
        client = Client("ecmwf", beta=True)
        client.retrieve(
            date= 0,
            time= 0,
            step= steps,
            stream="enfo", 
            type=['cf', 'pf'],
            levtype="sfc",
            param='2t',
            target= os.path.join(dirname,"IntermediateDataFiles", "ccsds2mt_ensemble_all_steps.grib2")  
        )

        print('accessed and stored ECMWF 2t forecast')

        data_2mt = ecdata.read(os.path.join(dirname,"IntermediateDataFiles", "ccsds2mt_ensemble_all_steps.grib2"))  #"ccsds2mt_ensemble_all_steps.grib2")

        # mean of 2mt for 1 week is calculated from all ensemble members for all time steps for all days
        # end result = 1 mean value for 1 week
        t2m_mean = ecdata.mean(data_2mt)
        t2m_mean.write(os.path.join(dirname,"IntermediateDataFiles", "ccds_2mt_ensemble_mean.grib"))  #'ccds_2mt_ensemble_mean.grib'
        ccds_to_simple(os.path.join(dirname,"IntermediateDataFiles", "ccds_2mt_ensemble_mean.grib"), os.path.join("IntermediateDataFiles", "simple_2mt_ensemble_mean.grib"))                         

        print('calculated and stored ECMWF 2t mean forecast as grib file')

        # Retrieve data for all the defined steps for relative humidity "r"
        # levtype = pl = pressure - 1000 hPa corresponds to surface level
        client = Client("ecmwf", beta=True)
        client.retrieve(
            date= 0,
            time= 0,
            step= steps,
            stream="enfo", 
            type=['cf', 'pf'],
            levtype="pl",
            levelist = "1000",
            param='r',
            target= os.path.join(dirname,"IntermediateDataFiles", "ccsds_r_ensemble_all_steps.grib2") 
        )

        print('accessed and stored ECMWF r forecast')

        data_r = ecdata.read(os.path.join(dirname,"IntermediateDataFiles", "ccsds_r_ensemble_all_steps.grib2"))
        # calculate the mean value for the whole week
        r_mean = ecdata.mean(data_r)
        r_mean.write(os.path.join(dirname,"IntermediateDataFiles", "ccds_r_ensemble_mean.grib"))  #'ccds_r_ensemble_mean.grib')

        ccds_to_simple(os.path.join(dirname,"IntermediateDataFiles", "ccds_r_ensemble_mean.grib"), os.path.join(dirname,"IntermediateDataFiles", "simple_r_ensemble_mean.grib")) 

        print('calculated and stored ECMWF r mean forecast as grib file')
        # Save both variable weekly mean forecasts as GeoTIFF files
        transform_grib2_to_TIFF (os.path.join(dirname,"IntermediateDataFiles", "simple_2mt_ensemble_mean.grib"), os.path.join(dirname,"IntermediateDataFiles", "2mt_fc_weekly_mean.tif"))
        transform_grib2_to_TIFF (os.path.join(dirname,"IntermediateDataFiles", "simple_r_ensemble_mean.grib"), os.path.join(dirname,"IntermediateDataFiles", "RH_fc_weekly_mean.tif"))

        # Clip both tif files to the outlines of Africa
        input_raster_2mt = os.path.join(dirname,"IntermediateDataFiles", "2mt_fc_weekly_mean.tif")
        input_shapefile = os.path.join(dirname,"AfricaOutlines", "Africa_Boundaries.shp")
        output_file_2mt = os.path.join(dirname,"IntermediateDataFiles", "2mt_fc_weekly_mean_mask.tif")
        create_mask_from_shapefile(input_shapefile, input_raster_2mt, output_file_2mt)

        input_raster_RH = os.path.join(dirname,"IntermediateDataFiles", "RH_fc_weekly_mean.tif")
        output_file_RH = os.path.join(dirname,"IntermediateDataFiles", "RH_fc_weekly_mean_mask.tif")
        create_mask_from_shapefile(input_shapefile, input_raster_RH, output_file_RH)
       
        print('r and 2t mean forecasts turned into tif files and clipped to africa')
        # -------------
        # Fetching of NASA GEOS-FP Ensemble Forecast (of surface dust concentration) for the next 7 days 

        # get today's date
        today = date.today()
        # get yesterday's date
        yesterday = today - timedelta(days = 1)
        tomorrow = today + timedelta(days = 1)
        seven_days_from_now = today + timedelta(days = 6)
        yest_year_month_day = yesterday.strftime("%Y%m%d")

        # construct the url for the opendap server to access the forecast published yesterday at 00 (for the next 10 days)
        url = 'https://opendap.nccs.nasa.gov/dods/GEOS-5/fp/0.25_deg/fcast/tavg3_2d_aer_Nx/tavg3_2d_aer_Nx.{}_00'.format(yest_year_month_day)
        
        # access the dataset from the opendap server
        d = xr.open_dataset(url, engine='netcdf4')
        print('accessed GEOS-FP sdc forecast data')

        # prepare the slices of the timeframe we are interested in
        slice_today = '{}T01:30:00.000000000'.format(today)
        slice_7d_ahead = '{}T22:30:00.000000000'.format(seven_days_from_now)

        # slice the dataset to the variable surface dust concentration ('dusmass'), the geographic extend of africa and the temporal extend of the next 7 days
        ds = d.dusmass.sel(lat=slice(-51, 38), lon=slice(-26,78), time=slice(slice_today, slice_7d_ahead))

        # calculate the mean value of the surface dust concentration for the whole 7 days ahead
        ds_mean = ds.mean(dim='time')
        print('calculated GEOS-FP sdc forecast mean')
        # save the mean sdc of the next week to a netcdf file
        ds_mean.to_netcdf(os.path.join(dirname,"IntermediateDataFiles","xarray_subset_fp_africa_7days_mean.nc"), engine='netcdf4')
        print('stored GEOS-FP sdc mean as nc file')

        # Construct the full path to the .nc file
        nc_file_path_fp_sdc = os.path.join(dirname,"IntermediateDataFiles", "xarray_subset_fp_africa_7days_mean.nc")

        # Prepend the "netcdf:" prefix to the path
        netcdf_path_fp_sdc = f"netcdf:{nc_file_path_fp_sdc}"

        # turn the .nc file into a .tif file
        reader = rasterio.open(netcdf_path_fp_sdc)
        prof = reader.profile
        prof.update(driver='GTiff', crs="EPSG:4326")
        array = reader.read(1)
        with rasterio.open(os.path.join(dirname,"IntermediateDataFiles","xarray_subset_fp_africa_7days_mean.tif"), "w", **prof) as dst:
            dst.write(array,1)

        # Clip the weekly mean forecast of surface dust concentration to the outlines of Africa
        input_raster = os.path.join(dirname,"IntermediateDataFiles","xarray_subset_fp_africa_7days_mean.tif")
        input_shapefile = os.path.join(dirname,"AfricaOutlines","Africa_Boundaries.shp")
        output_file_name = os.path.join(dirname,"IntermediateDataFiles","xarray_subset_fp_africa_7days_mean_mask.tif")

        create_mask_from_shapefile(input_shapefile, input_raster, output_file_name)

        print('turned GEOS-FP sdc forecast mean nc file into tif and clipped to africa')

        # original data unit of the raster is kg/m^3 - we turn the data into unit values of ug/m^3
        input_raster = os.path.join(dirname,"IntermediateDataFiles","xarray_subset_fp_africa_7days_mean_mask.tif")
        output_raster_filename = os.path.join(dirname,"IntermediateDataFiles", "sdc_fc_7days_mean_mask_ug3.tif")
        scalar = 10**9
# uncomment the inputraster location path in the functon, since the input we will give will probably be a path instead of file
# name bc otherwise we design our system to just store files in one folder with our script instead of neatly storing it
# in a data folder
        multiply_raster_by_scalar(input_raster, output_raster_filename, scalar)

# N.B. check if it will be a proplem that we reuse input names e.g. input_raster for different functions?
# do we have to flush the disk or somehting?

        #----------------------------------------------------
        
        #*************************************************************************************************************************************************************************
        # Meningitis outbreak risk prediction calculation                                                                                                                        *
        # Risk map computation for week 1 is based on NASA's GEOS-FP assimilation past forecasts of the past week (week 0) (2m temp, relative humidity, sdc)                     *
        # Risk map computation for week 2 is based on the ECMWF ensemble forecast for week 1 (of 2m temp and relative humidity (ECMWF)) and dust surface concentration (GEOS-FP) *
        #*************************************************************************************************************************************************************************
        """    
        print('Get current working directory : ', os.getcwd())
        print('example path:', os.path.join("IntermediateDataFiles", "sdc_fc_7days_mean_mask_ug3.tif"))
        dirname = os.getcwd()
        filename = os.path.join(dirname, 'rasters', 'riskmap.tif')
        print(filename)

        """   
        
        # dates for the meningitis risk fc for week 1 
        six_d_from_now = today + timedelta(days=6)

        today_ymd = today.strftime("%Y%m%d")
        six_d_from_now_ymd = six_d_from_now.strftime("%Y%m%d")

        # dates for the meningitis risk fc of week 2: today+7 - today+14
        seven_d_from_now = today + timedelta(days = 7)
        fourteen_d_from_now = today + timedelta(days = 13)

        seven_d_from_now_ymd = seven_d_from_now.strftime("%Y%m%d")
        fourteen_d_from_now_ymd = fourteen_d_from_now.strftime("%Y%m%d")
        
        # resample the surface dust concentration (pixel size: 0.3125,-0.25.) (GEOS-FP forecast) to match the 2mt and rh raster (pixel size: 0.25,-0.25) (ECMWF forecast)
        inputfile_sdc_fc = os.path.join(dirname,"IntermediateDataFiles", "sdc_fc_7days_mean_mask_ug3.tif")
        outputfile_sdc_fc = os.path.join(dirname,"IntermediateDataFiles", "dust_fc_weekly_mean_mask_ug3_resampled.tif")
        resample_resolution(inputfile_sdc_fc, outputfile_sdc_fc)
        
        # resample the surface dust concentration, 2mt, rh (pixel size: 0.3125,-0.25.) (GEOS-FP assimilation past fc) 
        # to match the 2mt and RH raster (pixel size: 0.25,-0.25) (ECMWF forecast)
        inputfile_sdc_past = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean_mask_ugm3.tif")
        outputfile_sdc_past = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean_mask_ugm3_resampled.tif")
        resample_resolution(inputfile_sdc_past, outputfile_sdc_past)

        inputfile_rh_past = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean_mask_percent.tif")
        outputfile_rh_past = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean_mask_percent_resampled.tif")
        resample_resolution(inputfile_rh_past, outputfile_rh_past)

        inputfile_2mt_past = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean_mask_celsius.tif")
        outputfile_2mt_past = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean_mask_celsius_resampled.tif")
        resample_resolution(inputfile_2mt_past, outputfile_2mt_past)

        print('resampled all 4 GEOS-FP files to the resolution of ECMWF')

        today_dmy = today.strftime("%d/%m/%Y")
        six_d_from_now_dmy = six_d_from_now.strftime("%d/%m/%Y")
        seven_d_from_now_dmy = seven_d_from_now.strftime("%d/%m/%Y")
        fourteen_d_from_now_dmy = fourteen_d_from_now.strftime("%d/%m/%Y")

        
        
        # compute Risk Map for week 1
        input_2mt_past = os.path.join(dirname,"IntermediateDataFiles", "2mt_assi_africa_past7days_mean_mask_celsius_resampled.tif")
        input_rh_past = os.path.join(dirname,"IntermediateDataFiles", "rh_assi_africa_past7days_mean_mask_percent_resampled.tif")
        input_sdc_past = os.path.join(dirname,"IntermediateDataFiles", "dusm_assi_africa_past7days_mean_mask_ugm3_resampled.tif")
        RiskMap_week1_file_name = os.path.join(dirname, "rasters", "Risk_map_week1_{}-{}.tif".format(today_ymd, six_d_from_now_ymd))

        compute_risk_map(input_2mt_past, input_rh_past, input_sdc_past, RiskMap_week1_file_name)

        print('computed risk map for week 1')
       
        # compute Risk Map for week 2
        input_2mt_fc = os.path.join(dirname,"IntermediateDataFiles", "2mt_fc_weekly_mean_mask.tif")
        input_rh_fc = os.path.join(dirname,"IntermediateDataFiles", "RH_fc_weekly_mean_mask.tif")
        input_sdc_fc = os.path.join(dirname,"IntermediateDataFiles", "dust_fc_weekly_mean_mask_ug3_resampled.tif")
        RiskMap_week2_file_name = os.path.join(dirname, "rasters", "Risk_map_week2_{}-{}.tif".format(seven_d_from_now_ymd, fourteen_d_from_now_ymd))

        compute_risk_map(input_2mt_fc, input_rh_fc, input_sdc_fc, RiskMap_week2_file_name)

        print('computed risk map for week 2')
        
        # Load the .tif file into the database
        # ds = DataSource(os.path.join("RiskMapFiles", "Risk_map_week1_{}-{}.tif".format(today_ymd, six_d_from_now_ymd)))

        # layer = ds[0]

        # Clear existing data (optional)
        # RasterLayer.objects.all().delete()

        # Save the new data
        # for feat in layer:
        #     raster = feat.geom.geos
        #     RasterLayer.objects.create(rasterfile=geom)

        #self.stdout.write(self.style.SUCCESS('Successfully generated and stored the risk map'))
        

        tif_path_week1 = os.path.join(dirname,"rasters", "Risk_map_week1_{}-{}.tif".format(today_ymd, six_d_from_now_ymd))

        # Save the raster file to the database
        raster_layer, created = RasterLayer.objects.get_or_create(name="{} - {}".format(today_dmy, six_d_from_now_dmy), datatype='ca') #datatype= 'ca'
        raster_layer.rasterfile.name = os.path.relpath(tif_path_week1, settings.MEDIA_ROOT)
        raster_layer.save()

        print ('stored risk map week 1 to db')
        
        tif_path_week2 = os.path.join(dirname,"rasters", "Risk_map_week2_{}-{}.tif".format(seven_d_from_now_ymd, fourteen_d_from_now_ymd))

        # Save the raster file to the database
        raster_layer, created = RasterLayer.objects.get_or_create(name="{} - {}".format(seven_d_from_now_dmy, fourteen_d_from_now_dmy), datatype= 'ca') #datatype= 'ca'
        raster_layer.rasterfile.name = os.path.relpath(tif_path_week2, settings.MEDIA_ROOT)
        raster_layer.save()

        print ('stored risk map week 2 to db')
        
        self.stdout.write(self.style.SUCCESS('Successfully computed and stored both risk maps'))
    
       
#after adding the 2 risk maps to the database, empty both folders; IntermediateDataFiles and RiskMapFiles
        