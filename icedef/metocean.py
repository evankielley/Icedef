"""This module can instantiate objects which contain ECMWF ocean and atmospheric data for a particular time and space range.
"""

import scipy.interpolate as interp
import datetime
from datetime import date, timedelta
import urllib
import netCDF4 as nc
import numpy as np
import os



class Metocean(object):
    """This class acts as a superclass that defines the spatial and temporal bounds for the data of its subclasses.
    """

    def __init__(self, x_min, x_max, y_min, y_max, t_min, t_max):
        """Instantiate a metocean object with spatial and temporal bounds.
        
        Args:
            x_min (float): minimum line of longitude for data region (degrees)
            x_max (float): maximum line of longitude for data region (degrees)
            y_min (float): minimum line of latitude for data region (degrees)
            y_max (float): maximum line of latitude for data region (degrees)
            t_min (datetime.datetime): minimum time for data time space
            t_max (datetime.datetime): maximum time for data time space
        """
        self.x_min = x_min - abs(x_min-x_max) - self.xy_res
        self.x_max = x_max + abs(x_min-x_max) + self.xy_res
        self.y_min = y_min - abs(y_min-y_max) - self.xy_res
        self.y_max = y_max + abs(y_min-y_max) + self.xy_res
        self.t_min = t_min - timedelta(hours = self.t_res)
        self.t_max = t_max + timedelta(hours = self.t_res)

        
    def convert_datetime2time(self, t, t_units, t_calendar, t_offset=0):
        """This function converts a datetime into the new time format specified
        
        Args:
            t (datetime.datetime): time to be converted
            t_units (str): units of time (specified in NetCDF file)
            t_calendar (str): time calendar (specified in NetCDF file)
            
        Returns:
            t (float): converted time (hours since some date)
        """
                                                
        dt += timedelta(hours = t_offset)
        t = nc.date2num(t, t_units, t_calendar)
        
        return t
    
    
    def get_filenames(self):
        """This function returns the NetCDF files needed to access the desired metocean data (and their filenames)
            
        Returns:
            filenames (list of str): list of the filenames of the files returned
            files (list): list of files accessed through server or cache
        """
        
        if self.cache:
            cache_path = 'cache/' + self.model_id
            if not os.path.exists(cache_path):
                try:
                    os.makedirs(cache_path)
                except:
                    print("Could not make cache directory, continuing without it...")
        else:
            cache_path = None
        
        # Calculate range of dates needed for data
        d1 = date(self.t_min.year, self.t_min.month, self.t_min.day)  # start date
        d2 = date(self.t_max.year, self.t_max.month, self.t_max.day)  # end date
        delta = d2 - d1  # timedelta
    
        filenames = []
        files = []

        for i in range(delta.days + 1):
            new_date = d1 + timedelta(days=i)
            filename = str(new_date).replace('-', '') + '.nc'
            filenames.append(filename)
            cache_file = cache_path + filename
            
            if os.path.isfile(cache_file):
                files.append(cache_file)
            else:
                if self.cache and os.path.exists(cache_path):
                    files.append(urllib.request.urlretrieve(self.path + filename, cache_path + filename)[0])
                else:
                    files.append(urllib.request.urlretrieve(self.path + filename)[0])
        
        return filenames, files


    
    
class ECMWF_Ocean(Metocean):
    """This class creates an object which contains ocean data for surface current velocity and SST amongst other attributes.
    
    Note: 
        Product identifier: GLOBAL_ANALYSIS_FORECAST_PHY_001_024
    
    Args:
        Metocean (class): parent class
        
    Attributes:
        model_id (str): product identifier for the dataset
        path (str): path to the directory of data files needed
        xy_res (float): spatial resolution of the ocean model (degrees)
        t_res (float): temporal resolution of the ocean model (hours)
        t_units (str): time units used in NetCDF data files
        t_calendar (str): time calendar used in NetCDF files
    """
    
    model_id = "GLOBAL_ANALYSIS_FORECAST_PHY_001_024"
    path = 'ftp://data.munroelab.ca/pub/ECMWF/ocean/daily/'
    xy_res = 1/12  # spatial resolution in degrees lat/lon
    t_res = 1  # temporal resolution in hours
    t_units = 'hours since 1950-01-01 00:00:00'
    t_calendar = 'standard'
    
    def __init__(self, x_min, x_max, y_min, y_max, t_min, t_max, cache=True):
        
        super().__init__(x_min, x_max, y_min, y_max, t_min, t_max)
        
        #: bool: will attempt to cache data files if True
        self.cache = cache
        
        #: list of str: filenames is a list of data filenames, files is a list of their associated file handles
        self.filenames, self.files = self.get_filenames()
        
        #: netCDF4._netCDF4.MFDataset: dataset of NetCDF4 files
        self.ds = nc.MFDataset(self.files)
        
        #: list of float: list of times for the data in format according to t_units  
        self.times = self.ds.variables['time'][:]
        
        #: datetime.datetime: list of datetimes for the corresponding data times
        self.datetimes = nc.num2date(self.times, self.t_units, self.t_calendar)
        
        #: list of float: list of times for the data in hours since the year 1900
        self.t1900 = nc.date2num(self.datetimes, 'hours since 1900-01-01 00:00:00.0 00:00', 'standard')
        
        #: list of float: list of times for the data in hours since the year 1950
        self.t1950 = nc.date2num(self.datetimes, 'hours since 1950-01-01 00:00:00.0 00:00', 'standard')
        
        #: list of float: list of times for the data in hours since the year 2000
        self.t2000 = nc.date2num(self.datetimes, 'hours since 2000-01-01 00:00:00.0 00:00', 'standard')
        
        #: list of float: list of latitudes for the data
        self.lats = self.ds.variables['latitude'][:]
        
        #: list of float: list of longitudes for the data
        self.lons = self.ds.variables['longitude'][:]
        
        #: numpy.ndarray: 3-D data field ([time, lat, lon]) for the u-component of current velocity (m/s)
        self.UW = np.asarray(self.ds.variables['uo'][:,0,:,:])
        
        #: numpy.ndarray: 3-D data field ([time, lat, lon]) for the v-component of current velocity (m/s)
        self.VW = np.asarray(self.ds.variables['vo'][:,0,:,:])
        
        #: numpy.ndarray: 3-D data field ([time, lat, lon]) for the sea-surface temperature (C)
        self.SST = np.asarray(self.ds.variables['thetao'][:,0,:,:])
        
        #: scipy.interpolate.interpolate.RegularGridInterpolator: interpolator of UW
        self.iUW = interp.RegularGridInterpolator((self.times, self.lats, self.lons), self.UW)
        
        #: scipy.interpolate.interpolate.RegularGridInterpolator: interpolator of VW
        self.iVW = interp.RegularGridInterpolator((self.times, self.lats, self.lons), self.VW)
        
        #: scipy.interpolate.interpolate.RegularGridInterpolator: interpolator of SST
        self.iSST = interp.RegularGridInterpolator((self.times, self.lats, self.lons), self.SST)
    
 



class ECMWF_Atm(Metocean):
    """This class creates an object which contains atmospheric data for 10 meter wind velocity amongst other attributes.
    
    Note: 
        Product identifier: WIND_GLO_WIND_L4_NRT_OBSERVATIONS_012_004
    
    Args:
        Metocean (class): parent class
        
    Attributes:
        model_id (str): product identifier for the dataset
        path (str): path to the directory of data files needed
        xy_res (float): spatial resolution of the atmospheric model (degrees)
        t_res (float): temporal resolution of the atmospheric model (hours)
        t_units (str): time units used in NetCDF data files
        t_calendar (str): time calendar used in NetCDF files
    """
    
    model_id = "WIND_GLO_WIND_L4_NRT_OBSERVATIONS_012_004"
    path = 'ftp://data.munroelab.ca/pub/ECMWF/atm/daily/'
    xy_res = 1/4  # spatial resolution in degrees lat/lon
    t_res = 6  # temporal resolution in hours
    t_units = 'hours since 1900-01-01 00:00:00.0 00:00'
    t_calendar = 'standard'
    
    def __init__(self, x_min, x_max, y_min, y_max, t_min, t_max, cache=True):
        
        super().__init__(x_min, x_max, y_min, y_max, t_min, t_max)
        
        #: bool: will attempt to cache data files if True
        self.cache = cache
        
        #: list of str: filenames is a list of data filenames, files is a list of their associated file handles
        self.filenames, self.files = self.get_filenames()
        
        #: netCDF4._netCDF4.MFDataset: dataset of NetCDF4 files
        self.ds = nc.MFDataset(self.files)
        
        #: list of float: list of times for the data in format according to t_units
        self.times = self.ds.variables['time'][:]
        
        #: datetime.datetime: list of datetimes for the corresponding data times
        self.datetimes = nc.num2date(self.times, self.t_units, self.t_calendar)
        
        #: list of float: list of times for the data in hours since the year 1900
        self.t1900 = nc.date2num(self.datetimes, 'hours since 1900-01-01 00:00:00.0 00:00', 'standard')
        
        #: list of float: list of times for the data in hours since the year 1950
        self.t1950 = nc.date2num(self.datetimes, 'hours since 1950-01-01 00:00:00.0 00:00', 'standard')
        
        #: list of float: list of times for the data in hours since the year 2000
        self.t2000 = nc.date2num(self.datetimes, 'hours since 2000-01-01 00:00:00.0 00:00', 'standard')
        
        #: list of float: list of latitudes for the data
        self.lats = self.ds.variables['latitude'][:]
        
        #: list of float: list of longitudes for the data
        self.lons = self.ds.variables['longitude'][:]
        
        #: numpy.ndarray: 3-D data field ([time, lat, lon]) for the u-component of wind velocity (m/s)
        self.UA = np.asarray(self.ds.variables['eastward_wind'][:,0,:,:])
        
        #: numpy.ndarray: 3-D data field ([time, lat, lon]) for the u-component of wind velocity (m/s)
        self.VA = np.asarray(self.ds.variables['northward_wind'][:,0,:,:])
        
        #: scipy.interpolate.interpolate.RegularGridInterpolator: interpolator of UA
        self.iUA = interp.RegularGridInterpolator((self.times, self.lats, self.lons), self.UA)
        
        #: scipy.interpolate.interpolate.RegularGridInterpolator: interpolator of VA
        self.iVA = interp.RegularGridInterpolator((self.times, self.lats, self.lons), self.VA)
