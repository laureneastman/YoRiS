import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import os
from astropy import constants as const
import astropy.units as u
from astropy.cosmology import FlatLambdaCDM
import scipy.optimize as opt
from matplotlib.colors import Normalize
from colorama import Fore, Style
from tqdm import tqdm
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable




##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# LOADING IN THE ANT DATA




def load_ANT_data():
    """
    loads in the ANT data files

    INPUTS:
    -----------
    None


    OUTPUTS:
    ----------
    dataframes: a list of the ANT data in dataframes
    names: a list of the ANT names
    ANT_bands: a list of lists, each inner list is a list of all of the bands which are present in the light curve

    """
    phils_ANTs = "C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS Data/modified Phil's lightcurves"
    other_ANT_data = "C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS Data/other ANT data/ALL_FULL_LCs" 
    directories = [phils_ANTs, other_ANT_data]

    dataframes = []
    names = []
    ANT_bands = []
    for dir in directories:
        for file in os.listdir(dir): # file is a string of the file name such as 'file_name.dat'
            # getting the ANT name from the file name
            if dir == other_ANT_data:
                ANT_name = file[:-12]
            else:
                ANT_name = file[:-7] # the name of the transient

            # load in the files
            file_path = os.path.join(dir, file)
            file_df = pd.read_csv(file_path, delimiter = ',') # the lightcurve data in a dataframe
            bands = file_df['band'].unique() # the bands in which this transient has data for

            dataframes.append(file_df)
            names.append(ANT_name)            
            ANT_bands.append(bands)

    return dataframes, names, ANT_bands





##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# REST FRAME LUMINOSITY CALCULATION



def restframe_luminosity(d_l_cm, bandZP, z, m, m_err):
    """
    Calculates the rest frame luminosity 

    INPUTS:
    -----------------------
    d_l_cm: luminosity distance in cm ( can be calculated using astropy.cosmology.luminosity_distance(z) )

    bandZP: observed band's AB mag zeropoint in ergs/s/cm^2/Angstrom

    z: object's redshift

    m: magnitude (either abs or apparent, just account for this with d_l)

    m_err: magnitude error


    OUTPUTS
    -----------------------
    L_rf: rest frame luminosity in ergs/s/Angstrom

    L_rf_err: the rest frame luminosity's error, propagated from the error on the magnitude only - in ergs/s/Angstrom

    """
    L_rf = 4 * np.pi * (d_l_cm**2) * bandZP * (1 + z) * (10**(-0.4 * m)) # in ergs/s/Angstrom

    L_rf_err = 0.4 * np.log(10) * L_rf * m_err # in ergs/s/Angstrom

    return L_rf, L_rf_err





##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################




def obs_wl_to_em_wl(obs_wavelength, z):
    return obs_wavelength / (1+z)




##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################




def ANT_data_L_rf(ANT_df_list, ANT_names, dict_ANT_z, dict_ANT_D_lum, dict_band_ZP, dict_band_obs_cent_wl):
    """

    INPUTS
    ---------------
    ANT_df_list: (list) a list of dataframes for each ANT, with the columns: MJD, mag, magerr, band

    ANT_names: (list) a list of names of each ANT, MUST be in the same order as the dataframes, so ANT_df_list[i] and ANT_names[i] MUST correspond to the same ANT

    dict_ANT_z: (dict) dictionary of ANT redshift values (found in plotting preferences as 'ANT_redshift_dict' - this has PS1-10adi's redshift = 0.0 since we are given abs 
    mag rather than app mag)

    dist_ANT_D_lum: (dict) dictioanry of ANT luminosity distances (calculated under a few assumptions, which can be checked in the plotting_preferences file)

    dict_band_ZP: (dict) dictioanry of the zeropoints of each of the bands present for any ANT (found in plotting_preferences)

    dict_band_obs_cent_wl: (dict) dictionary of the observed central wavelengths of the bands present for each of the ANTs (found in plotting_preferences)
    


    OUTPUTS
    ---------------
    new_ANT_df_list: (list) a list of dataframes of the ANTs, in the same order as ANT_df_list and ANT_names. Each dataframe will have the columns:
                    MJD, mag, magerr, band, em_cent_wl (in Angstrom), L_rf (in ergs/(s * cm^2 * Angstrom)), L_rf_err (in ergs/(s * cm^2 * Angstrom)).
    
    """

    band_names = list(dict_band_obs_cent_wl.keys()) # a list of the band names for all ANTs
    observed_wl_list = list(dict_band_obs_cent_wl.values())

    new_ANT_df_list = [] # the list of ANT_dfs with the new data added such as L_rf, L_rf_err and em_cent_wl
    for i, ANT_df in enumerate(ANT_df_list):
        name = ANT_names[i] # ANT name
        z = dict_ANT_z[name] # redshift
        d_lum = dict_ANT_D_lum[name] # luminosity distance in cm


        # we need to create a dictionary of the observed band's ecntral wavelength which has been converted into the rest-frame by correcting for the redshift
        band_em_cent_wl = [obs_wl_to_em_wl(obs_wl, z) for obs_wl in observed_wl_list] # emitted central wavelength for each observed band
        band_em_cent_wl_dict = dict(zip(band_names, band_em_cent_wl)) # a dictionary of the observed band, and its central wavelength converted into the rest-frame wavelength

        ANT_df['em_cent_wl'] = ANT_df['band'].map(band_em_cent_wl_dict) # producing a column in ANT_df which gives the band's central wavelength converted into the rest-frame


        # rest frame luminosity
        rf_L = []
        rf_L_err = []
        for i in range(len(ANT_df['MJD'])):
            band = ANT_df['band'].iloc[i] # the datapoint's band
            band_ZP = dict_band_ZP[band] # the band's zeropoint
            mag = ANT_df['mag'].iloc[i] # the magnitude
            magerr = ANT_df['magerr'].iloc[i] # the mag error

            L_rest, L_rest_err = restframe_luminosity(d_lum, band_ZP, z, mag, magerr) # the rest frame luminosity and its error
            rf_L.append(L_rest)
            rf_L_err.append(L_rest_err)

        # add these columns to the ANT's dataframe
        ANT_df['L_rf'] = rf_L
        ANT_df['L_rf_err'] = rf_L_err

        new_ANT_df_list.append(ANT_df)


    return new_ANT_df_list







##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# BINNING FUNCTION




def weighted_mean(data, errors):
    if not isinstance(data, np.ndarray):
        data = np.array(data)

    if not isinstance(errors, np.ndarray):
        errors = np.array(errors)
    
    if len(data) == 0: # if the bin has no data within it, then the weighted mean and its error = NaN
        wm = pd.NA
        wm_err = pd.NA

    if (sum(errors)) == 0.0: # if the errors in the bin all == 0.0 (like with Gaia_G) then just take the regular mean and set its error to NA
        wm = np.mean(data)
        wm_err = pd.NA

    else: # if the bin has data within it, then take the weighted mean
        weights = 1/(errors**2)
        wm = np.sum(data * weights) / (np.sum(weights))
        wm_err = np.sqrt( 1/(np.sum(weights)) )

    return wm, wm_err





##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################





def bin_lc(list_lc_df, MJD_binsize, drop_na_bins = True):
    """
    Takes each band within the light curve data provided and puts it into MJD bins, taking the weighted mean of the rest frame luminosity, its error and the weighted mean 
    MJD to match this, with the upper and lower errors on the MJD indicating the range of MJD values within the bin.

    INPUTS
    -----------
    list_lc_df: (list) a list of dataframes for each ANT's light curve data across all bands. Each DataFrame must contain the columns:  MJD, L_rf, L_rf_err, band, em_cent_wl

    MJD_binsize: (int or float) the size of the MJD bins that you want

    
    OUTPUTS
    -----------
    list_binned_lc_dfs: (list) a list of dataframes of the whole ANT light curve binned into bin size = MJD_binsize. Each band within the light curve is binned separately.
                        Each df contains the columns:  MJD_bin, wm_L_rf (ergs/s/cm^2/Angstrom), wm_L_rf_err (args/s/cm^2/Angstrom), wm_MJD, band, em_cent_wl, MJD_lower_err, MJD_upper_err

    """
    list_binned_lc_dfs = []
    for idx, lc_df in enumerate(list_lc_df):
        #print(f'index = {idx}')
        lc_df = lc_df.copy() # this creates a copy rather than a view of the dataframe so that we don't modify the original dataframe
        
        bands_present = lc_df['band'].unique()
        for i, b in enumerate(bands_present):
            b_df = lc_df[lc_df['band'] == b].copy()

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # cretaing the bins 
            # this rounds the min_MJD present in V_band data for the transient to the nearest 10, then goes to the bin below this to ensure that 
            # we capture the first data point, in case this rounded the first bin up. Since we need data for both V_band and B_band within each
            # MJD bin, it's fine to base the min MJD bin to start at on just the V_band data, since even if we had B_band data before this date, 
            # we wouldn't be able to pair it with data from V_band to calculcte the color anyways
            MJD_bin_min = int( round(b_df['MJD'].min(), -1) - 10 )
            MJD_bin_max = int( round(b_df['MJD'].max(), -1) + 10 )
            MJD_bins = range(MJD_bin_min, MJD_bin_max + MJD_binsize, MJD_binsize) # create the bins

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # binning the data
            # data frame for the binned band data  - just adds a column of MJD_bin to the data, then we can group by all datapoints in the same MJD bin
            b_df['MJD_bin'] = pd.cut(b_df['MJD'], MJD_bins)
            
            # binning the data by MJD_bin
            b_binned_df = b_df.groupby('MJD_bin', observed = drop_na_bins).apply(lambda g: pd.Series({
                                                                'wm_L_rf': weighted_mean(g['L_rf'], g['L_rf_err'])[0], 
                                                                'wm_L_rf_err': weighted_mean(g['L_rf'], g['L_rf_err'])[1], 
                                                                'wm_MJD': weighted_mean(g['MJD'], g['L_rf_err'])[0], 
                                                                'min_MJD': g['MJD'].min(), 
                                                                'max_MJD': g['MJD'].max(), 
                                                                'count': g['MJD'].count(), 
                                                                'band': g['band'].iloc[0],
                                                                'em_cent_wl': g['em_cent_wl'].iloc[0]
                                                                })).reset_index()

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # creating the upper and lower MJD errorbars
            MJD_lower_err = []
            MJD_upper_err = []
            for j in b_binned_df.index: 
                if b_binned_df['count'].loc[j] == 1.0: # accounting for the casae if we have one datapoint in the bin, hence the MJD range within the bin = 0.0, but if we don't set it to 0.0 explicitly, it'll be calculated as like -1e-12
                    mjd_lerr = 0.0
                    mjd_uerr = 0.0

                else: # if there are > 1 datapoints within the bin
                    mjd_lerr = b_binned_df['wm_MJD'].iloc[j] - b_binned_df['min_MJD'].iloc[j] # lower errorbar value in MJD
                    mjd_uerr = b_binned_df['max_MJD'].iloc[j] - b_binned_df['wm_MJD'].iloc[j] # upper errorbar value in MJD

                    # getting rid of any negative mjd upper or lower errors, since the only way that it's possible for these numbers to be negative is that the MJD of the datapoints 
                    # in the bin are so close together, you're essentially doing mjd upper/lower = a - (~a), which, due to floating point errors, could give a value like -1e-12
                    if mjd_lerr < 0.0:
                        mjd_lerr = 0.0
                    elif mjd_uerr < 0.0:
                        mjd_uerr = 0.0

                MJD_lower_err.append(mjd_lerr)
                MJD_upper_err.append(mjd_uerr)

            b_binned_df['MJD_lower_err'] = MJD_lower_err
            b_binned_df['MJD_upper_err'] = MJD_upper_err
            b_binned_df = b_binned_df.drop(columns = ['min_MJD', 'max_MJD', 'count']) # drop these intermediate step columns

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # we should now have a light curve which is binned up with weighted mean flux + its error, the weighed mean MJD, with its error bar showing the range of MJD values 
            # within the bin, and the band
            # concatenate together the band dataframes to produce a dataframe for the whole light curve across all bands again 
            if i == 0:
                whole_lc_binned_df = b_binned_df
            else:
                whole_lc_binned_df = pd.concat([whole_lc_binned_df, b_binned_df], ignore_index = True)

        list_binned_lc_dfs.append(whole_lc_binned_df) # a list of the binned ANT dataframes


    return list_binned_lc_dfs







##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# CONVERTING FROM REST FRAME LUMINOSITY TO APPARENT MAGNITUDE








def L_rf_to_mag(d_l_cm, bandZP, z, L_rf, L_rf_err):
    """
    Calculates the magnitude from the rest frame luminosity 

    INPUTS:
    -----------------------
    d_l_cm: luminosity distance in cm ( can be calculated using astropy.cosmology.luminosity_distance(z) )

    bandZP: observed band's AB mag zeropoint in ergs/s/cm^2/Angstrom

    z: object's redshift

    L_rf: rest frame luminosity in ergs/s/Angstrom

    L_rf_err: rest frame luminosity error in ergs/s/Angstrom


    OUTPUTS
    -----------------------
    m: magnitude (either abs or apparent, depending on d_l_cm)

    m_err: magnitude error

    """
    denom = 4 * np.pi * (d_l_cm**2) * bandZP * (1 + z)
    m = -2.5 * np.log10(L_rf / denom)

    m_err = (2.5 / (np.log(10) * L_rf)) * L_rf_err # THIS HAD A NEGATIVE SIGN IN IT BUT I THINK ITS FINE TO TAKE THE POSITIVE, CHECK GOODNOTES NOTEs

    return m, m_err







##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# AFTER BINNING THE LIGHT CURVE USING THE REST FRAME LUMINOSITY, WE CAN RE-CALCULATE THE APPARENT MAGNITUDE OF THE BIN









def ANT_data_mags(ANT_df_list, ANT_names, dict_ANT_z, dict_ANT_D_lum, dict_band_ZP):
    """
    Once we've binned the light curves (which we can only do using rest frame luminosity or flux), we can calculate the apparent ot absolute magnitude associated with this averaged rest frame luminosity in the bin. 
    This funciton calculates the apparent of absolute magnitude + its error given the rest frame luminosity and its error and adds these columns to each ANT light curve

    INPUTS
    ---------------
    ANT_df_list: a list of dataframes for each ANT, with the columns: MJD, mag, magerr, band

    ANT_names: a list of names of each ANT, MUST be in the same order as the dataframes, so ANT_df_list[i] and ANT_names[i] MUST correspond to the same ANT

    dict_ANT_z: dictionary of ANT redshift values

    dist_ANT_D_lum: dictioanry of ANT luminosity distances (calculated under a few assumptions, which can be checked in the plotting_preferences file)

    dict_band_ZP: dictioanry of the zeropoints of each of the bands present for any ANT
    


    OUTPUTS
    ---------------
    new_ANT_df_list: a list of dataframes of the ANTs, in the same order as ANT_df_list and ANT_names. Each dataframe will have the columns mag amd magerr added to it
    
    """

    new_ANT_df_list = [] # the list of ANT_dfs with the new data added such as L_rf, L_rf_err and em_cent_wl
    for i, ANT_df in enumerate(ANT_df_list):
        name = ANT_names[i] # ANT name
        z = dict_ANT_z[name] # redshift
        d_lum = dict_ANT_D_lum[name] # luminosity distance in cm

        # rest frame luminosity
        mag_list = []
        magerr_list = []
        for i in range(len(ANT_df['wm_MJD'])):
            band = ANT_df['band'].iloc[i] # the datapoint's band
            band_ZP = dict_band_ZP[band] # the band's zeropoint
            L_rf = ANT_df['wm_L_rf'].iloc[i] # the magnitude
            L_rf_err = ANT_df['wm_L_rf_err'].iloc[i] # the mag error

            mag, magerr = L_rf_to_mag(d_lum, band_ZP, z, L_rf, L_rf_err) # the rest frame luminosity and its error
            mag_list.append(mag)
            magerr_list.append(magerr)

        # add these columns to the ANT's dataframe
        ANT_df['mag'] = mag_list
        ANT_df['magerr'] = magerr_list

        new_ANT_df_list.append(ANT_df)


    return new_ANT_df_list













##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# CHI SQUARED FUNCTION



def chisq(y_m, y, yerr, M, reduced_chi = False, chi_AND_redchi = False):
    """
    Calculates the chi squared, as well as the reduced chi squared and its 1 sigma uncertainty allowance if wanted

    INPUTS:
    --------------
    y_m: model y data

    y: observed y data

    yerr: observed y errors

    M: number of model paramaters

    reduced_chi: if True, this function will return chi, reduced_chi and red_chi_1sig, if False (default) it will just return chi

    chi_AND_redchi: if True, this function will return the chi squared, the reduced chi squared and the reduced chi squared 1 sigma error tolerance. 

    OUTPUTS 
    ----------------
    chi: the chi squared of the model (returned if reduced_chi == False)

    red_chi: the reduced chi squared (returned if reduced_chi == True)

    red_chi_1sig: the 1 sigma error tolerance on the reduced chi squared. If the reduced chi squared falls within 1 +/- red_chi_1sig, it's considered a good model 
                (returned if reduced_chi == True)
    """
    if not isinstance(y_m, np.ndarray):
        y_m = np.array(y_m)

    if not isinstance(y, np.ndarray):
        y = np.array(y)

    if not isinstance(yerr, np.ndarray):
        yerr = np.array(yerr)

    chi = np.sum( ((y - y_m )**2) / (yerr**2))
    
    if (reduced_chi == True) or (chi_AND_redchi == True): 
        N = len(y) # the number of datapoints
        N_M = N-M # (N - M) the degrees of freedom

        if N_M <= 0.0: # if the number of parameters >= number of datapoints to fit
            red_chi = np.nan
            red_chi_1sig = np.nan
        else:
            red_chi = chi / (N_M)
            red_chi_1sig = np.sqrt(2/N_M) # red_chi is a good chisq if it falls within (1 +/- red_chi_1sig)
        
        if (reduced_chi == True) and (chi_AND_redchi == False): # if you just want red chi and red_chi_1sig
            return red_chi, red_chi_1sig
        elif (reduced_chi == False) and (chi_AND_redchi == True): # if you want chi squared, red chi and red_chi_1sig
            return chi, red_chi, red_chi_1sig
    
    elif (reduced_chi == False) and (chi_AND_redchi == False): # if you just want chi squared
        return chi
    

    





##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# POLYFITTING A LIGHT CURVE








#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================



def identify_straggler_datapoints(b_df, min_band_datapoints = 5, min_non_straggler_count = 4, straggler_dist = 200):
    """
    We want to target bands which have a few straggling datapoints near the start/end of the light curve and we don't want to include these in our data for polyfitting. Instead, we want to put these datapoints in a bin
    and put them with the closest interpolated datapoint position, provided that it's not too far away. For example, if ZTF_g has one datapoint 400 days after the rest of the light curve, at MJD = 58100 and L_rf = L_Rf_dp, we don't want this
    influencing our polynomial fit. Lets say that our reference band has nearby datapoints at [..., 58079, 58090, 58125, ...] we will assume that the L_rf is unchanged over a period of a maximum of 20 days, so we
    will set an interpolated interp_L_rf point at 58090 = L_rf_dp. Basically, we're assuming that there will be no significant evolution of L_rf over a maximum fo a 20 day period. We should caluclate the error on this value as
    we would with the usual interpolated datapoints, removing the term which calculates the error required to set the local reduced chi squared to 1, so just the mean error of the vlosest 20 datapoints, then a term proportional 
    to the number of days interpolated. 
    
    INPUTS:
    --------------
    b_df: dataframe. A single band's dataframe

    min_band_datapoints: (int) the minimum number of datapoints of a band for us to even bother polyfitting it. 

    straggler_dist: int. The number of days out which the datapoint has to be to be considered a potential straggler. i.e. if it's > straggler_dist away from either side of the data, an
    

    OUTPUTS
    -------------
    stragglers: a dataframe with all the same columns as b_df, where we have taken the rows in b_df which are considered to have 'straggler' data and we have put them into this dataframe. This is the part
    of the light curve that we don't want to fit to, but we will put into bins with the nearest interpolated datapoints (as long as this isn't too far away)

    non_stragglers: a dataframe, similar to stragglers which contains all of the 'non-straggler' rows from b_df. This is the part of the light curve that we want to fit to
    """
    b_count = b_df['wm_MJD'].count()
    colnames = b_df.columns.tolist()

    if b_count < min_band_datapoints: # if there are less than 5 datapoints, consider each point in the band a straggler
        stragglers = b_df.copy()
        non_stragglers = pd.DataFrame(columns = colnames) # an empty dataframe

    
    else: # if we have a decent number of datapoints in the band, then we're just looking for general straggling datapoints at the start or end of the band's light curve that we want to cut out
        if len(b_df['wm_MJD']) > 20:
            check_for_stragglers1 = b_df.iloc[:10].copy()
            check_for_stragglers2 = b_df.iloc[-10:].copy()
            check_for_stragglers_df = pd.concat([check_for_stragglers1, check_for_stragglers2], ignore_index=False) # the first and last 10 datapoints, keep original indicies from b_df

        else:
            check_for_stragglers_df = b_df.copy()

        straggler_indicies = []
        check_for_stragglers_idx = check_for_stragglers_df.index
        for j in range(len(check_for_stragglers_idx)):
            i = check_for_stragglers_idx[j] # the row index in check_for_stragglers
            dp_row = check_for_stragglers_df.loc[i].copy() # the row associated with this index
            mjd = dp_row['wm_MJD']
            directional_MJD_diff = b_df['wm_MJD'] - mjd
            mjd_diff_before = directional_MJD_diff[directional_MJD_diff < 0.0] # don't put <= here or below since it will then take the MJD diff with itself into account. 
            mjd_diff_after = directional_MJD_diff[directional_MJD_diff > 0.0]
            no_dps_50_days = (abs(directional_MJD_diff) <= 50.0 ).sum()

            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # counting the number of datapoints before and after this mjd
            no_dps_before = len(mjd_diff_before)
            no_dps_after = len(mjd_diff_after)

            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # calculating the closest mjd difference before and after the datapoint
            closest_MJD_diff_before = abs(max(mjd_diff_before)) if no_dps_before > 0 else None # if this datapoint isn't the very first one. This part is more used to catch out stragglers at the end of the light curve. It will catch the last datapoint
            closest_MJD_diff_after = abs(min(mjd_diff_after)) if no_dps_after > 0 else None # if this datapoint isn't the very last one. This part is more used to catch out stragglers at the start of the light curve. It will catch the first datapoint

            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # given the straggler criteria, put this datapoint's row in either the stragglers or non-stragglers dataframe
            if (no_dps_before > 0) and (no_dps_after > 0): # if the datapoint is not the first or last datapoint
                if ((closest_MJD_diff_before >= straggler_dist) and (closest_MJD_diff_after >= straggler_dist)) and (no_dps_50_days < 4): 
                    
                    if (no_dps_after < 3): # looking to the end of the light curve
                        if i not in straggler_indicies:
                            straggler_indicies.append(i)
                        b = j
                        for k in range(no_dps_after): # # iterate through the datapoints after the straggler and add them to the stragglers list
                            b = b + 1
                            idx = check_for_stragglers_idx[b]

                            if idx not in straggler_indicies:
                                straggler_indicies.append(idx)


                    elif (no_dps_before < 3): # looking to the start of the light curve
                        if i not in straggler_indicies:
                            straggler_indicies.append(i)

                        b = j
                        for k in range(no_dps_before): # iterate through the datapoints before the straggler and add them to the stragglers list
                            b = b - 1
                            idx = check_for_stragglers_idx[b]

                            if idx not in straggler_indicies:
                                straggler_indicies.append(idx)


            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            elif no_dps_before == 0: # if it's the very first datapoint
                if closest_MJD_diff_after >= straggler_dist:
                    if i not in straggler_indicies:
                        straggler_indicies.append(i)

            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            elif no_dps_after == 0: # if it's the very last datapoint
                if closest_MJD_diff_before >= straggler_dist:
                    if i not in straggler_indicies:
                        straggler_indicies.append(i)

        stragglers = b_df.loc[straggler_indicies].copy().reset_index(drop = True)
        non_stragglers = b_df.drop(index = straggler_indicies).reset_index(drop = True)

    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # if, after all of those checks, we are now left with a non-straggler dataframe of very few datapoints, we may as well not fit the light curve at all
    if len(non_stragglers.index) < min_non_straggler_count:
        stragglers = b_df
        non_stragglers = pd.DataFrame(columns = colnames)      

    return stragglers, non_stragglers






#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================







def allow_interpolation(interp_x, all_data_x, b_coverage_quality, local_density_region = 50, interp_cap = 150, gapsize = 100, factor = 100, simple_cutoff = False, simple_cut = 50):
    """
    Here I have written a formula to determine whether or not to interpolate a band at a given mjd value based on
    how well-sampled the band is, so that poorly sampled bands cannot interpolate very far, and well-sampled bands can interpolate much further

    NOTE: there are edge cases where the band may be very well sampled over a small MJD range, at which point the formula may allow this to interpolate
    further than it should. However, if you bin the light curve into somehting like 1 day bins before polyfitting, at least you won't get weird little spikes of loads of 
    data making this worse. 

    INPUTS
    ------------
    interp_x: float, the x value at which we're trying to interpolate

    all_data_x: array of the x values of teh actual data that we're interpolating

    b_coverage_density: float. output in the function check_lightcurve_coverage. A score based on how many datapoints the band has and how well distrbuted this data is. The higher, the better the lightcurve

    local_density_region: The region over which we count the lcoal datapoint density. This would be: (interp_x - local_density_region) <= x <= (interp_x + local_density_region)

    interp_cap: the maximum value out to which we can interpolate. Only the well-sampled bands would reach this cap

    gapsize: float. The distance between 2 consecutive datapoints which is considered to be a 'gap'. Since polyfits vary wildly over gaps, we will not interpolate whatsoever across a gap, so if there is a 
            gap in the data > gapsize, we will not interpolate at all here

    factor: a factor in ther equation. 

    RETURNS
    ------------
    interp_alowed: Bool. If True, then interpolation is allowed at interp_x, if False, interpolation si not allowed at interp_x

    """

    directional_MJD_diff = all_data_x - interp_x # takes the MJD difference between interp_x and the MJDs in the band's real data. Directional because there will be -ve values for datapoints before interp_x and +ve ones for datapoints after
   
    # calculating the closest MJD difference between the closest datapoints before and after interp_x, if there is one (there only wouldn't be one if interp_x was at the very edge of )
    # in the equations below I have allowed directional_MJD_diff >=/<= 0.0 because if directional_MJD_diff == 0.0, then we'd be interpolating at an MJD at which we have a real datapoint, so we're allowed to interpolate at interp_x here, regardlesss 
    # if there's a gap afterwrads because this wouldn't be considered interpolating over a gap, we're interpolating at a point which already had a true datapoint there
    closest_MJD_diff_before = abs(max(directional_MJD_diff[directional_MJD_diff <= 0.0])) # closest MJD diff of datapoints before 

    closest_MJD_diff_after = min(directional_MJD_diff[directional_MJD_diff >= 0.0])


    MJD_diff = abs(directional_MJD_diff) # takes the MJD difference between interp_x and the MJDs in the band's real data
    local_density = (MJD_diff <= local_density_region).sum() # counts the number of datapoints within local_density_region days' of interp_x
    closest_MJD_diff = min(MJD_diff)

    if simple_cutoff == False:
        interp_lim = (b_coverage_quality * local_density * factor) 
        interp_lim = min(interp_cap, interp_lim) # returns the smaller of the two, so this caps the interpolation limit at interp_cap

        # THE MIDDLE SECTIONS GET PREFERENTIAL TREATMENT COMPARED TO THE CENTRAL ONES
        #if ((interp_x - local_density_region) <= min(all_data_x)) or ((interp_x + local_density_region) >= max(all_data_x)): # if interp_x is near thestart/end of the band's lightcurve
        #    interp_lim = interp_lim*2
        

        if (closest_MJD_diff < interp_lim) and (closest_MJD_diff_before < gapsize) and (closest_MJD_diff_after < gapsize): # if interp_x lies within our calculated interpolation limit, then allow interpolation here. Also don't allow interpolation over gaps
            interp_allowed = True
        else: 
            interp_allowed = False
        
    else:
        if (closest_MJD_diff <= simple_cut) and (closest_MJD_diff_before < gapsize) and (closest_MJD_diff_after < gapsize): # if interp_x lies within our calculated interpolation limit, then allow interpolation here. Also don't allow interpolation over gaps
            interp_allowed = True
        else: 
            interp_allowed = False


    return interp_allowed
    


#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================



def check_lightcurve_coverage(b_df, mjd_binsize = 50):
    """
    Bins the light curve into mjd bins and counts the number of dapoints in each bin. Can be used as a measure of the light curve data coverage for the band. It's an improvement on just doing 
    (number of datapoints in the band)/(MJD span of the band) because a lot of the data could be densely packed in a particular region and sparsely distributed across the rest, and this would give the 
    impression that the light curve was quite well sampled when it's not really. 

    coverage_term = mean(count of datapoints in mjd_binsize bin) * (no datapoints across the lightcurve) / (1 + std dev(count of datapoints in mjd_binsize bin)) as a calculation of the light curve coverage. 

    INPUTS
    -------------
    b_df: a dataframe containing the band's data. We only actually look at the column 'wm_MJD'

    mjd_binsize: int. The size of the bins within which we would like to count the number of datapoints in. This is to test how well-distributed the light curve's data is


    RETURNS
    ----------
    
    coverage_term = A score based on light curve coverage. The higher, the better. Higher scores will come from lightcurves which have well-distributed data across the light curve and lots of data in general. 

    """

    MJD_bin_min = int( round(b_df['wm_MJD'].min(), -1) - mjd_binsize )
    MJD_bin_max = int( round(b_df['wm_MJD'].max(), -1) + mjd_binsize )
    MJD_bins = range(MJD_bin_min, (MJD_bin_max + mjd_binsize), mjd_binsize) # create the bins

    # binning the data
    # data frame for the binned band data  - just adds a column of MJD_bin to the data, then we can group by all datapoints in the same MJD bin
    b_df['MJD_bin'] = pd.cut(b_df['wm_MJD'], MJD_bins)

    # binning the data by MJD_bin
    b_binned_df = b_df.groupby('MJD_bin', observed = False).apply(lambda g: pd.Series({'count': g['wm_MJD'].count()})).reset_index()
    mean_count = b_binned_df['count'].mean()
    std_count = b_binned_df['count'].std()
    coverage_term = mean_count * len(b_df['wm_MJD']) / (1 + std_count) # = mean * no datapoints / (1 + std)

    return coverage_term


#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================



def polyfitting(b_df, band_coverage_quality, mjd_scale_C, L_rf_scalefactor, max_poly_order):
    """
    This function uses chi squred minimisation to optimise the choice of the polynomial order to fit to a band in a light curve, and also uses curve_fit to find
    the optimal parameters for each polynomial fit. Bands with little data are not allowed to use higher order polynomials to fit them

    INPUTS:
    ---------------
    b_df: a dataframe of the (single-band) lightcurve which has been MJD-limited to the region that you want to be polyfitted. 

    band_coverage_quality: (float). A score calculated within teh check_lightcurve_coverage function which si large for light curves with lots fo datapoints
    which are well-distributed across the light curve's mjd span

    mjd_scale_C: float. best as the mean MJD in the band or overall lightcurve. Used to scale-down the MJD values that we're fitting

    L_rf_scalefactor: float. Used to scale-down the rest frame luminosity. Usually = 1e-41.   

    max_poly_order: int between 3 <= max_poly_order <= 14. The maximum order of polynomial that you want to be allowed to fit. 


    OUTPUTS
    --------------------
    optimal_params: a list of the coefficients of from the polyfit in descenidng order, e.g. if we have ax^2 + bx + c, optimal params = [a, b, c] so the coefficient of the highest
                    order term goes first

    plot_polt_MJD: a list of MJD values at which we have evaluated the polyfit, for plotting purposes

    plot_polt_L: a list of rest frame luminosity values calculated using the polyfit, for plotting purposes

    best_redchi: the reduced chi squared of the optimal polynomial fit

    best_redchi_1sig: the reduced chi squared's one sigma tolerance of the optimal polynomial fit

    poly_sigma_dist: the reduced chi squared's sigma distance for the optimal polynomial fit (should ideally be 1)

    """
    def poly1(x, a, b):
        return b*x + a

    def poly2(x, a, b, c):
        return c*x**2 + b*x + a

    def poly3(x, a, b, c, d):
        return d*x**3 + c*x**2 + b*x + a

    def poly4(x, a, b, c, d, e):
        return e*x**4 + d*x**3 + c*x**2 + b*x + a

    def poly5(x, a, b, c, d, e, f):
        return f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a

    def poly6(x, a, b, c, d, e, f, g):
        return g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a

    def poly7(x, a, b, c, d, e, f, g, h):
        return h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a

    def poly8(x, a, b, c, d, e, f, g, h, i):
        return i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a

    def poly9(x, a, b, c, d, e, f, g, h, i, j):
        return j*x**9 + i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a
    
    def poly10(x, a, b, c, d, e, f, g, h, i, j, k):
        return k*x**10 + j*x**9 + i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a
    
    def poly11(x, a, b, c, d, e, f, g, h, i, j, k, l):
        return l*x**11 + k*x**10 + j*x**9 + i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a
    
    def poly12(x, a, b, c, d, e, f, g, h, i, j, k, l, m):
        return m*x**12 + l*x**11 + k*x**10 + j*x**9 + i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a
    
    def poly13(x, a, b, c, d, e, f, g, h, i, j, k, l, m, n):
        return n*x**13 + m*x**12 + l*x**11 + k*x**10 + j*x**9 + i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a
    
    def poly14(x, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o):
        return o*x**14 + n*x**13 + m*x**12 + l*x**11 + k*x**10 + j*x**9 + i*x**8 + h*x**7 + g*x**6 + f*x**5 + e*x**4 + d*x**3 + c*x**2 + b*x + a


    poly_order_dict = {1: poly1,  # a dictionary of polynomial orders and their associated functions, used for curve_fit in the polyfitting function
                        2: poly2, # feels like there should be a much more efficient way to write this I am slightly ashamed lol
                        3: poly3, 
                        4: poly4, 
                        5: poly5, 
                        6: poly6, 
                        7: poly7, 
                        8: poly8, 
                        9: poly9, 
                        10: poly10, 
                        11: poly11, 
                        12: poly12, 
                        13: poly13, 
                        14: poly14}

    # prepping the data for fitting
    b_L_scaled = b_df['wm_L_rf'].copy() * L_rf_scalefactor # scaled L_rf
    b_L_err_scaled = b_df['wm_L_rf_err'].copy() * L_rf_scalefactor # scaled_L_rf_err
    b_MJD_scaled = b_df['wm_MJD'].copy() - mjd_scale_C # scaled MJD

    # calculate how well-sampled the band is 
    b_MJD_span = b_df['wm_MJD'].max() - b_df['wm_MJD'].min() # the span of MJDs that the band makes
    b_count = len(b_df['wm_MJD']) # the number of datapoints in the band's data
    

    # restrict the order of polynomial available to poorly sampled band lightcurves
    if band_coverage_quality >= 80.0: # the best covered light curves are allowed to try the max order of polynomial
        poly_orders_available = np.arange(1, (max_poly_order + 1), 1)

    elif (band_coverage_quality >= 50) and (band_coverage_quality < 80):
        poly_orders_available = np.arange(1, (12 + 1), 1)

    elif  (band_coverage_quality >= 30) and (band_coverage_quality < 50):
        poly_orders_available = np.arange(1, (10 + 1), 1)

    elif  (band_coverage_quality >= 20) and (band_coverage_quality < 30):
        poly_orders_available = np.arange(1, (8 + 1), 1)

    elif  (band_coverage_quality >= 16) and (band_coverage_quality < 20):
        poly_orders_available = np.arange(1, (7 + 1), 1)

    elif  (band_coverage_quality >= 6) and (band_coverage_quality < 16):
        poly_orders_available = np.arange(1, (6 + 1), 1)

    elif  (band_coverage_quality >= 2) and (band_coverage_quality < 6):
        poly_orders_available = np.arange(1, (3 + 1), 1)

    elif  (band_coverage_quality >= 1) and (band_coverage_quality < 2):
        poly_orders_available = [1, 2]

    elif  (band_coverage_quality >= 0) and (band_coverage_quality < 1): # the worst covered lightcurves have very restricted access to polynomial orders
        poly_orders_available = [1]

    if b_MJD_span < 50.0:
        poly_orders_available = [1]

    elif b_MJD_span < 100:
        poly_orders_available = [1, 2]
    
    

    if b_count in poly_orders_available: # if the number of datapoints = polynomial order
        idx = poly_orders_available.index(b_count)
        print(f'FLAG: {b_count}, {poly_orders_available}')
        poly_orders_available = poly_orders_available[:(idx - 1)] # this should be fine since we have a lower limit of 2 datapoints right now
        print(f'NEW polyorders = {poly_orders_available}')

    # iterate thriugh different polynomial orders
    best_redchi = 1e10 # start off very high so it's immediately overwritten by the first fit's results
    for order in poly_orders_available: 
        poly_function = poly_order_dict[order]
        popt, pcov = opt.curve_fit(poly_function, xdata = b_MJD_scaled, ydata = b_L_scaled, sigma = b_L_err_scaled)
        
        # now calculate the reduced chi squared of the polynomial fit
        polyval_coeffs = popt[::-1] # using popt[::-1] just reverses the array because my polynomial functions inputs go in ascending order coefficients, whereeas polyval does the opposite
        chi_sc_poly_L = np.polyval(polyval_coeffs, b_MJD_scaled) 
        redchi, redchi_1sig = chisq(chi_sc_poly_L, b_L_scaled, b_L_err_scaled, M = order + 1, reduced_chi = True)
        
        # if we get a better reduced chi squared than before, overwrite the optimal parameters
        if pd.notna(redchi):
            if (redchi < best_redchi): 
                best_redchi = redchi
                best_redchi_1sig = redchi_1sig
                optimal_params = polyval_coeffs
        
    
    poly_sigma_dist = abs(1 - best_redchi)/(best_redchi_1sig)
    plot_poly_sc_MJD = np.arange(min(b_MJD_scaled), max(b_MJD_scaled), 1.0) # for plotting the polynomial fit
    plot_poly_sc_L = np.polyval(optimal_params, plot_poly_sc_MJD)

    plot_poly_MJD = plot_poly_sc_MJD + mjd_scale_C
    plot_poly_L = plot_poly_sc_L/L_rf_scalefactor

    return optimal_params, plot_poly_MJD, plot_poly_L, best_redchi, best_redchi_1sig, poly_sigma_dist



#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================



def fudge_interpolation_error_formula(mean_err, mjd_dif, L):
        """
        A fudge formula inspired by superbol which calculates an error for interpolated datapoints. 

        INPUTS
        -----------
        mean_err: (float) the mean error on the nearest X datapoints. If you're utilising straggler data, just input the error on your straggler datapoint

        mjd_dif: (float) the mjd span over which we are interpolating

        L: (float) the rest frame luminosity of the interpolated datapoint. Ideally, this would be scaled down


        RETURNS
        -------------
        er: (float). The fudged error calculated for the interpolated datapoint. If you input L as a scaled value, er will be scaled by the same value as well. 

        """

        fraction = 0.05

        x = abs( L * (mjd_dif / 10) ) 
        #er = np.sqrt(mean_err**2 + (fraction * x)**2)  # this adds some % error for every 10 days interpolated - inspired by Superbol who were inspired by someone else
        er = mean_err + fraction*x
        if er > abs(L):
            er = abs(L)

        return er



#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================




def fudge_polyfit_L_rf_err(real_b_df, scaled_polyfit_L_rf, scaled_reference_MJDs, MJD_scaledown, L_rf_scaledown, optimal_params):
    """
    Fudges the uncertainties on the rest frame luminosity values calculated using the polynomial fit of the band,
    evaluated at the trusted_band's MJD values. 

    Fudged_L_rf_err = mean(L_rf_err values of the 20 closest datapoints in MJD) + 0.05*polyfit_L_rf*|mjd - mjd of 
    closest datapoint in the band's real data|/10

    The first term is the mean of the closest 20 datapoints in MJD's rest frame luminosity errors. The second term 
    adds a 5% error for every 10 dats interpolated. For this fudge errors formula, I took inspo from
    Superbol who took inspo from someone else.
    
    INPUTS
    ---------------
    real_b_df: the actual band's dataframe (assuming the light curve has been through the binning function to be 
                binned into like 1 day MJD bins). This data should not be limited by
                the MJD values which we selected (fit_MJD_range in the outer funciton), 
                just input the whole band's dataframe. 

    scaled_polyfit_L_rf: a list/array of the polyfitted scaled rest frame luminosity values which were evaluated at the 
                    trusted band's MJD values (the reference_MJDs)

    scaled_reference_MJDs: a list/array of scaled MJD values which are the values at which the trusted band has data. This should
                    be restricted to the region chosen to fit the polynomials to, not the
                    entire light curve with any little stragglers far before the start/'end', i.e. should be limited 
                    by fit_MJD_range from the outer function. 

    MJD_scaledown: float. A scale constant to scale-down the MJD values. 

    L_rf_scaledown: float. A scale factor to scale-down the rest frame luminosity

    optimal_params: a list of the coefficients of from the polyfit in descenidng order, e.g. if we have ax^2 + bx + c, optimal params = [a, b, c] so the coefficient of the highest
                    order term goes first

                    
    OUTPUTS
    ---------------
    poly_L_rf_err_list: a list of our fudged L_rf_err values for our polyfit interpolated data. 

    """
    def invert_redchi(y, y_m, y_m_err, M):
        """
        Calculates an error term based on 
        """
        return


    rb_df = real_b_df.sort_values(by = 'wm_MJD', ascending = True) # making sure that the dataframe is sorted in ascending order of MJD, just in case. The real band's dataframe
    rb_MJDs = np.array(rb_df['wm_MJD'].copy())
    scaled_rb_MJDs = rb_MJDs - MJD_scaledown # scaled down band's real MJD values
    sc_rb_L_rf = np.array(real_b_df['wm_L_rf'].copy()) * L_rf_scaledown # scaled down band's real weighted mean rest frame luminosity values
    rb_L_rf_err = np.array(real_b_df['wm_L_rf_err'].copy()) # an array of the band's real L_rf errors
    scaled_rb_L_rf_err = rb_L_rf_err * L_rf_scaledown # scaled down band's real weighted mean rest frame luminosity error values


    fudge_err_list = [] # a list of fudged rest frame luminosity uncertainties on the L_rf values calculated by polyfit, at the reference MJDs
    if isinstance(scaled_polyfit_L_rf, float): # accounting for the possibilit that scaled_polyfit_L_rf isn't a list of values but a list of one value or a float. This would only really happen when we evaluate the reference band at the straggler datapoint MJDs
        sc_ref_mjd = scaled_reference_MJDs
        sc_L = scaled_polyfit_L_rf
        MJD_diff = [abs(sc_ref_mjd - sc_mjd) for sc_mjd in scaled_rb_MJDs] # take the abs value of the difference between the mjd of the datapoint and the mjd values in the band's actual data
        sort_by_MJD_closeness = np.argsort(MJD_diff) # argsort returns a list of the index arrangement of the elements within the list/array its given that would sort the list/array in ascending order
            
        # calculate the mean of the closest 20 datapoint's errors
        closest_20_idx = sort_by_MJD_closeness[:20] 
        sc_closest_20_err = [scaled_rb_L_rf_err[j] for j in closest_20_idx] #  a list of the wm_L_rf_err values for the 20 closest datapoints to our interpolated datapoint
        sc_mean_L_rf_err = np.mean(np.array(sc_closest_20_err)) # part of the error formula = mean L_rf_err of the 20 closest datapoints in MJD
        closest_MJD_diff = MJD_diff[sort_by_MJD_closeness[0]]

        # use the fudged error formula
        sc_poly_L_rf_er = fudge_interpolation_error_formula(sc_mean_L_rf_err, closest_MJD_diff, sc_L)
        poly_L_rf_er =  sc_poly_L_rf_er / L_rf_scaledown # to scale L_rf (fudged) error
        
        if poly_L_rf_er < 0.0:
            print(sc_L, poly_L_rf_er)
        fudge_err_list.append(poly_L_rf_er)



    else:
        for i, sc_L in enumerate(scaled_polyfit_L_rf): # iterate through each interpolated L_rf value calculated by evaluating the polyfit at the reference band's MJDs
            sc_ref_mjd = scaled_reference_MJDs[i] # scaled MJD value of the reference band
            MJD_diff = [abs(sc_ref_mjd - sc_mjd) for sc_mjd in scaled_rb_MJDs] # take the abs value of the difference between the mjd of the datapoint and the mjd values in the band's actual data
            sort_by_MJD_closeness = np.argsort(MJD_diff) # argsort returns a list of the index arrangement of the elements within the list/array its given that would sort the list/array in ascending order
            
            # calculate the mean of the closest 20 datapoint's errors
            closest_20_idx = sort_by_MJD_closeness[:20] 
            sc_closest_20_err = [scaled_rb_L_rf_err[j] for j in closest_20_idx] #  a list of the wm_L_rf_err values for the 20 closest datapoints to our interpolated datapoint
            sc_mean_L_rf_err = np.mean(np.array(sc_closest_20_err)) # part of the error formula = mean L_rf_err of the 20 closest datapoints in MJD
            closest_MJD_diff = MJD_diff[sort_by_MJD_closeness[0]]

            # calculate the error on the datapoints which would force the reduced chi squared of the nearest 5 datapoints (using the errors for the interpolated datapoints) to 1
            #closest_5_idx = sort_by_MJD_closeness[:5]
            #sc_closest_rb_L = [sc_rb_L_rf[j] for j in closest_5_idx] # the scaled luminosity values of the closest 5 datapoints in the real band's data
            #sc_closest_rb_MJD = np.array([scaled_rb_MJDs[j] for j in closest_5_idx]) # the scaled MJD values of the closest 5 datapoints in the real band's data
            #sc_closest_interp_L = np.polyval(optimal_params, sc_closest_rb_MJD) * L_rf_scaledown
            
            # use the fudged error formula
            sc_poly_L_rf_er = fudge_interpolation_error_formula(sc_mean_L_rf_err, closest_MJD_diff, sc_L)
            poly_L_rf_er =  sc_poly_L_rf_er / L_rf_scaledown # to scale L_rf (fudged) error
            
            if poly_L_rf_er < 0.0:
                print(sc_L, poly_L_rf_er)
            fudge_err_list.append(poly_L_rf_er)

    return fudge_err_list



#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================



def choose_reference_band(ANT_name, df_bands, df_band_coverage_qualities, override_choice_dict):
    """
    Chooses the reference band for each band's interpolation. The polynomial fits to each band in the light curve (besides the reference band) will be evaluated at
    the reference band data's MJD values to produce an interpolated light curve which has lots of data at exact MJD values to be used for BB fitting. This function
    chooses the band with the highest band coverage quality score given by check_lightcurve_coverage(), but can override this decision if there is a preferred band
    specified in override_choice_dict. 

    INPUTS
    --------------
    ANT_name: (str) the ANT's name

    df_bands: (list) of the band names present in the light curve which we are fitting and interpolating

    df_band_coverage_qualities: (list) of the band coverage quality scores given by check_lightcurve_coverage()

    override_choice_dict: (distionary). The keys are the ANT names and the values are your choice to override the decision made on the reference band based on maximising the light curve
    coverage quality score. 

    OUTPUTS
    ---------------
    ref_band: (str) the name of the reference band for the ANT
    """

    override = override_choice_dict[ANT_name] 
    if override is not None:
        ref_band = override

    else:
        best_band_score = 0 # start off with a score which the first band is guaranteed to beat
        for i, b in enumerate(df_bands):
            band_score = df_band_coverage_qualities[i]

            if band_score > best_band_score: # every time the band's coverage quality score gets larger, we overwrite ' best_band_score' and 'ref_band'
                best_band_score = band_score
                ref_band = b


    return ref_band



#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================




def restrict_dataframe(df, min_value, max_value, column = 'wm_MJD'):
    """
    Applying a limit to a dataframe based on the values in a particular column.

    INPUTS
    ----------------
    df: (dataframe) the ANT's entire dataframe containing all bands

    min_value: (float) the minimum column value that you want to limit the dataframe to. Can be None if you don't want to limit the dataframe to a minimum value

    max_value: (float) the maximum column value  that you want to limit the dataframe to. Can be None if you don't want to limit the dataframe to a maximum value

    column: (str) the column in the dataframe which you want to limit the dataframe by. Default is 'wm_MJD'

    OUTPUT
    ---------------
    lim_df: (DataFrame). The ANT's dataframe which has been limited to the bounds specified in fit_MJD_range
    """

    lim_df = df.copy()
    if min_value != None:
        lim_df = lim_df[lim_df[column] > min_value].copy() 

    if max_value != None:
        lim_df = lim_df[lim_df[column] < max_value].copy()
    
    return lim_df






#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================









class polyfit_lightcurve:
    def __init__(self, ant_name, ant_z, df, bands, override_ref_band_dict, min_band_dps, manual_straggler_input_dict, 
                straggler_dist, gapsize, fit_MJD_range, max_interp_distance, b_colour_dict, 
                b_marker_dict, max_poly_order = 14, plot_polyfit = True, save_interp_df = True):
        """
        A class which can fit a polynomial to each band of a an ANT's light curve, then use this to interpolate the light curve according to user input interpolation restrictions
        to prevent interpolating in regions where the polynomial is more unreliable. 

        INPUTS
        -------------
        ant_name: (str) the ANT's name

        ant_z: (float) the ANT's redshift

        df: (DataFrame) the ANT's entire light curve dataframe, containing all bands. This light curve dataframe must have been passed through bin_lc() first (which is a function define)
        above in this file). 

        override_ref_band_dict: (dict) a distionary where the keys are the ANT names and the values are the band names which you want to choose as the refrence band, if the code picks
        a reference band which you don't like. The reference band is chosen by the code as the band with the highest coverage quality score. This dictionary can be found in plotting_preferences

        min_band_dps: (int) the minimum number of data points a band should have to be considered for polyfitting. 

        manual straggler_input_dict: (dict) a dictionary where the keys are the ANT names and the values are DataFrames containing the manually identified stragglers, with the columns 'MJD' and 'band'

        straggler_dist: (float) the minimum distance in MJD that a data point must be from the nearest one in the same band to be considered a straggler. 

        gapsize: (float) the minimum MJD distance to be defined as a gap in the light curve. If the distance between 2 consecutive data points is larger than this, then
        no polynomial interpolation will take place in this region. This i sbecause the polynomial is unconstrained across gaps in the light curve, so shouldn't be used
        to interpolate. 

        fit_MJD_range: (tuple). Containing the minimum and maximum MJDs over which you want this ANT to undergo polynomial fitting. This can be seen in plotting_preferences under 'MJDs_for_fit'

        max_interp_distance: (float) the maximum distance in MJD that you want to interpolate away from the nearest real data point. 

        b_colour_dict: (dict) a dictionary where the keys are the band names and the values are the colours you want to use when plotting them (can be found in plotting_preferences)

        b_marker_dict: (dict) a dictionary where the keys are the band names and the values are the markers you want to use when plotting them (can be found in plotting_preferences)

        max_poly_order: (int) I would recommend to leave as 14. The maximum polynomial order which can be used to fit the bands. The code will automatically restrict the polynomial 
        order available to bands with little data, so you don't have to worry about this too much. Can only choose values >=13

        plot_polyfit: (bool) whether to plot and save the polynomial fits to the bands. 

        save_interp_df: (bool) whether to save the polynomial interpolated light curve in a dataframe. 

        """
        
        self.ant_name = ant_name
        self.ant_z = ant_z
        self.df = df
        self.bands = bands
        self.override_ref_band = override_ref_band_dict[ant_name]
        self.interp_at_ref_band = True # leave as True, since we want to interpolate the reference band at the straggler MJDs
        self.min_band_dps = min_band_dps
        self.manual_straggler_input = manual_straggler_input_dict[self.ant_name] # if not None, is a dataframe containing manually identified stragglers
        self.straggler_dist = straggler_dist
        self.gapsize = gapsize
        self.fit_MJD_range = fit_MJD_range
        self.max_interp_distance = max_interp_distance
        self.max_poly_order = max_poly_order
        self.b_colour_dict = b_colour_dict
        self.b_marker_dict = b_marker_dict
        self.plot_polyfit = plot_polyfit
        self.save_interp_df = save_interp_df

        self.b_df_dict = {b: df[df['band'] == b].copy() for b in bands} # a dictionary of band dataframes, so self.b_df_dict[band] gives the band's dataframe
        self.lim_df = None # will be set later
        self.b_lim_df_dict = None # will be set later
        self.prepping_data = pd.DataFrame(columns = ['b_coverage_score', 'straggler_df', 'non_straggler_df', 'sc_interp_MJD'], index = self.bands)
        self.plot_results = pd.DataFrame(columns = ['poly_coeffs', 'poly_plot_MJD', 'poly_plot_L_rf', 'red_chi', 'red_chi_1sig', 'chi_sigma_dist'], index = self.bands)
        self.interp_df = pd.DataFrame(columns = ['MJD', 'L_rf', 'L_rf_err', 'band', 'em_cent_wl'])


    def get_scalefactors(self):
        self.L_scalefactor = 1e-41
        self.MJD_scaleconst = self.df['wm_MJD'].mean()
        

    
    def initialise_plot(self):
        if self.plot_polyfit == True:
            self.fig = plt.figure(figsize = (16, 7.5))




    # limiting the MJD over which we are polyfitting, because for some ANTs, we have some straggling datapoints far away from the rest of the light curve and we don't want to fit these
    def MJD_limit_df(self):
        if self.lim_df is None:
            self.lim_df = restrict_dataframe(df = self.df, min_value = self.fit_MJD_range[0], max_value = self.fit_MJD_range[1], column = 'wm_MJD')
            self.lim_df['sc_MJD'] = self.lim_df['wm_MJD'] - self.MJD_scaleconst
            self.b_lim_df_dict = {b: self.lim_df[self.lim_df['band'] == b].copy() for b in self.bands} # make a dictionary for the limited dataframes for each band
            self.b_em_cent_wl_dict = {b: self.lim_df.loc[self.lim_df['band'] == b, 'em_cent_wl'].iloc[0]for b in self.bands}



    def identify_stragglers_and_score_band(self):
        self.straggler_MJDs = []
        for b in self.bands:
            straggler_df, non_straggler_df = identify_straggler_datapoints(self.b_lim_df_dict[b], min_band_datapoints = self.min_band_dps, straggler_dist = self.straggler_dist)
            
            # check to see if there were any user defined stragglers:
            if self.manual_straggler_input is not None:
                manual_straggler_bands = self.manual_straggler_input['band'].unique()
                
                if b in manual_straggler_bands: # this assumes just one manually defined straggler per band, if you had multiple, you'd want to loop through the rows too
                    manual_straggler_mjd = np.round(self.manual_straggler_input['MJD'].iloc[0], 1) # rounded to one decimal place (fine because we bin to 1 day)
                    manual_straggler_row = non_straggler_df[np.round(non_straggler_df['wm_MJD'], 1) == manual_straggler_mjd] # check that the MJDs match to 1 decimal place (this is enough because we binned the data to 1 day bins)

                    straggler_df = pd.concat([straggler_df, manual_straggler_row]) # add the row to the straggler df
                    non_straggler_df = non_straggler_df.drop(manual_straggler_row.index) # remove the row from the non straggler df

            self.prepping_data.at[b, 'straggler_df'] = straggler_df
            self.prepping_data.at[b, 'non_straggler_df'] = non_straggler_df
            
            self.straggler_MJDs.extend(straggler_df['wm_MJD'].values) # extends straggler_MJDs by the values within the straggler_df['wm_MJD'].values array

            if non_straggler_df.empty: # if the band has too few datapoints to bother polyfitting, we know that this won't be the reference band so set it's coverage score to 0
                self.prepping_data.at[b, 'b_coverage_score'] = 0

                #if self.plot_polyfit == True: # plot the bands which were too poorly sampled to bother polyfitting (100% stragglers)
                #    b_colour = self.b_colour_dict[b]
                #    plt.errorbar(self.b_df_dict[b]['wm_MJD'], self.b_df_dict[b]['wm_L_rf'], yerr = self.b_df_dict[b]['wm_L_rf_err'], fmt = 'o', markeredgecolor = 'k', markeredgewidth = '1.0', linestyle = 'None', 
                #                label = b, c = b_colour)
                #    plt.scatter(straggler_df['wm_MJD'], straggler_df['wm_L_rf'], c = 'k', marker = 'o', s = 70, zorder = 2)
                #    plt.scatter(straggler_df['wm_MJD'], straggler_df['wm_L_rf'], c = b_colour, marker = 'x', s = 20, zorder = 3)
                #continue
            
            else: # calculate the coverage score for the bands with enough non-straggler datapoints
                self.prepping_data.at[b, 'b_coverage_score'] = check_lightcurve_coverage(non_straggler_df, mjd_binsize = 50)




    def choose_reference_band(self):
        """ called within choose_interp_MJD()
        Chooses the reference band for each band's interpolation. The polynomial fits to each band in the light curve (besides the reference band) will be evaluated at
        the reference band data's MJD values to produce an interpolated light curve which has lots of data at exact MJD values to be used for BB fitting. This function
        chooses the band with the highest band coverage quality score given by check_lightcurve_coverage(), but can override this decision if there is a preferred band
        specified in override_choice_dict. 
        """
        if self.override_ref_band is not None:
            self.ref_band = self.override_ref_band

        else:
            self.ref_band = self.prepping_data['b_coverage_score'].idxmax() # the reference band is the band with the highest band coverage quality score


        
    @staticmethod
    def generate_result_df(MJD, L_rf, L_rf_err, band, em_cent_wl):
        df = pd.DataFrame({'MJD': MJD, 
                           'L_rf': L_rf, 
                           'L_rf_err': L_rf_err, 
                           'band': band, 
                           'em_cent_wl': em_cent_wl})
        return df

    

    def choose_interp_MJD(self):
        if self.interp_at_ref_band == True:
            self.choose_reference_band()
            
            # append the reference band data to the results dataframe, since we aren't interpolating at these values
            ref_lim_df = self.b_lim_df_dict[self.ref_band]
            result_df = self.generate_result_df(ref_lim_df['wm_MJD'], ref_lim_df['wm_L_rf'], ref_lim_df['wm_L_rf_err'], self.ref_band, self.b_em_cent_wl_dict[self.ref_band])
            self.interp_df = pd.concat([self.interp_df, result_df], ignore_index = True)

            interp_MJDs = list(ref_lim_df['wm_MJD']) # the reference MJD values at which we should evaluate all other bands' polyfits
            interp_MJDs.extend(self.straggler_MJDs) # adding the straggler MJD values to interp_MJDs because we want to evaluate the polynomials at the straggler points
            interp_MJDs = np.sort(np.array(interp_MJDs)) # sorting the MJDs from lowest to highest value


        else:
            self.ref_band = None
            interp_MJDs = np.arange(self.lim_df['wm_MJD'].min(), (self.lim_df['wm_MJD'].max() + 2.5) , 5.0) # if we don't want to interpolate at the reference band (+ straggler) MJDs, then interpolate every 5 days


        for b in self.prepping_data.index: # iterate through the indicies of self.prepping_data, which are the band names
            if self.interp_at_ref_band == True:
                if b == self.ref_band:
                    b_interp_MJDs = self.straggler_MJDs # making sure we still evaluate the reference band at the straggler MJD values

                else:
                    b_interp_MJDs = interp_MJDs # if it's not the reference band, then continue as normal

                b_straggler_df = self.prepping_data.at[b, 'straggler_df']
                if b_straggler_df.empty == False:
                    b_straggler_MJDs = b_straggler_df['wm_MJD'].copy().tolist()
                    b_interp_MJDs = [mjd for mjd in b_interp_MJDs if mjd not in b_straggler_MJDs] # remove the band's own straggler MJDs from the interp_MJDs list, since we aren't interpolating the band's straggler datapoints, 
                                                                                                  # we're just going to insert the straggler data into the final interp_df
            else:
                b_interp_MJDs = interp_MJDs
                    

            b_lim_df = self.b_lim_df_dict[b]
            b_non_straggler_df = self.prepping_data.at[b, 'non_straggler_df']

            filtered_interp_MJDs = [mjd for mjd in b_interp_MJDs if (mjd >= b_non_straggler_df['wm_MJD'].min()) and (mjd <= b_non_straggler_df['wm_MJD'].max())]  # make sure interp_MJD doesn't go beyond the bounds of the band's data
            
            # evaluate whether each MJD is worth interpolating, e.g. if it's like 500 days away from all other datapoints, don't interpolate there because the polyfit isn't 
            # well constrained there. We allow better sampled bands to interpolate further out than poorly sampled bands since their fits are better constrained. 
            sc_filtered_interp_MJDs = filtered_interp_MJDs - self.MJD_scaleconst
            allow_interp = []
            for sc_int_mjd in sc_filtered_interp_MJDs:
                allow_int = allow_interpolation(interp_x = sc_int_mjd, all_data_x = b_lim_df['sc_MJD'], b_coverage_quality = self.prepping_data.at[b, 'b_coverage_score'], 
                                                          local_density_region = 50, interp_cap = self.max_interp_distance, gapsize = self.gapsize, factor = 1.0, 
                                                          simple_cutoff = False, simple_cut = None)
                allow_interp.append(allow_int)

            sc_filtered_interp_MJDs = np.array(sc_filtered_interp_MJDs)
            sc_filtered_interp_MJDs = sc_filtered_interp_MJDs[allow_interp]

            self.prepping_data.at[b, 'sc_interp_MJD'] = sc_filtered_interp_MJDs
            


    

    def polynomial_fit_and_interp(self):
        for b in self.bands:
            # do the polynomial fit + calculate the reduced chi squared
            non_straggler_df = self.prepping_data.at[b, 'non_straggler_df']

            # also, add the real (not interpolated) straggler datapoints into the final result interp_df, since we're evaluating the polyfits of each band at the straggler MJDs
            straggler_df = self.prepping_data.at[b, 'straggler_df']
            if straggler_df.empty == False:
                straggler_result_df = self.generate_result_df(MJD = straggler_df['wm_MJD'], L_rf = straggler_df['wm_L_rf'], L_rf_err = straggler_df['wm_L_rf_err'], band = [b]*len(straggler_df), em_cent_wl = [self.b_em_cent_wl_dict[b]]*len(straggler_df))
                self.interp_df = pd.concat([self.interp_df, straggler_result_df], ignore_index = True)

            if non_straggler_df.empty == True: # if our band has no non-straggler data, don't bother polyfitting
                self.plot_results.loc[b] = [None, None, None, None, None, None]
                
                continue

            poly_coeffs, plot_poly_MJD, plot_poly_L_rf, redchi, redchi_1sig, chi_sig_dist = polyfitting(b_df = non_straggler_df, band_coverage_quality = self.prepping_data.at[b, 'b_coverage_score'], mjd_scale_C = self.MJD_scaleconst, L_rf_scalefactor = self.L_scalefactor, max_poly_order = self.max_poly_order)
            self.plot_results.loc[b] = [poly_coeffs, plot_poly_MJD, plot_poly_L_rf, redchi, redchi_1sig, chi_sig_dist]

            # interpolate using the polynomial fit at the MJD values determined by choose_interp_MJD
            sc_interp_MJD = self.prepping_data.at[b, 'sc_interp_MJD']
            sc_interp_L = np.polyval(poly_coeffs, sc_interp_MJD)
            final_interp_L = sc_interp_L / self.L_scalefactor
            final_interp_MJD = sc_interp_MJD + self.MJD_scaleconst

            
            # calculate the fudged errors 
            interp_L_err = fudge_polyfit_L_rf_err(real_b_df = non_straggler_df, scaled_polyfit_L_rf = sc_interp_L, scaled_reference_MJDs = sc_interp_MJD, MJD_scaledown = self.MJD_scaleconst, L_rf_scaledown = self.L_scalefactor, optimal_params = poly_coeffs)
            if isinstance(final_interp_MJD, np.ndarray): 
                len_result_df = len(final_interp_MJD)
                result_df = self.generate_result_df(MJD = final_interp_MJD, L_rf = final_interp_L, L_rf_err = interp_L_err, band = [b]*len_result_df, em_cent_wl = [self.b_em_cent_wl_dict[b]]*len_result_df)

            elif isinstance(final_interp_MJD, float): # this will only happen when b is the reference band and we have one straggler datapoint that we'd like to evaluate our polyfits at
                result_df = self.generate_result_df(MJD = final_interp_MJD, L_rf = final_interp_L, L_rf_err = interp_L_err, band = [b], em_cent_wl = [self.b_em_cent_wl_dict[b]])
            
            self.interp_df = pd.concat([self.interp_df, result_df], ignore_index = True)




    def plot_polyfit_funciton(self):
    
        raw_and_interp_handles = []
        raw_and_interp_labels = []
        polyfit_handles = []
        polyfit_labels = []

        for b in self.bands:
            b_colour = self.b_colour_dict[b]
            b_marker = self.b_marker_dict[b]
            b_df = self.b_df_dict[b]
            b_em_cent_wl = b_df['em_cent_wl'].iloc[0]
            b_plot_polyfit = self.plot_results.loc[b]
            b_coverage_score = self.prepping_data.at[b, 'b_coverage_score']
            straggler_df = self.prepping_data.at[b, 'straggler_df']
            b_non_straggler_df = self.prepping_data.at[b, 'non_straggler_df']
            b_interp_df = self.interp_df[self.interp_df['band'] == b].copy()
            
            
            h1 = plt.errorbar(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = b_df['wm_MJD'], z = self.ant_z), b_df['wm_L_rf'], yerr = b_df['wm_L_rf_err'], fmt = b_marker, markeredgecolor = 'k', markeredgewidth = '1.0', linestyle = 'None', 
                            label = b, c = b_colour)
            raw_and_interp_handles.append(h1[0])
            raw_and_interp_labels.append(b)
            
            plt.scatter(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = straggler_df['wm_MJD'], z = self.ant_z), straggler_df['wm_L_rf'], c = 'k', marker = 'o', s = 70, zorder = 3)
            plt.scatter(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = straggler_df['wm_MJD'], z = self.ant_z), straggler_df['wm_L_rf'], c = b_colour, marker = 'x', s = 20, zorder = 4)
            h2 = plt.errorbar(b_interp_df['d_since_peak'], b_interp_df['L_rf'], yerr = b_interp_df['L_rf_err'], fmt = '^', c = b_colour, markeredgecolor = 'k', markeredgewidth = '1.0', 
                            linestyle = 'None', alpha = 0.5,  capsize = 5, capthick = 5, label = f'interp {b}')
            raw_and_interp_handles.append(h2[0])
            raw_and_interp_labels.append(f'interp {b}')

            if b_non_straggler_df.empty == False: # plot the polynomial fit if we had enough non-straggler datapoints to fit it
                h3 = plt.plot(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = b_plot_polyfit['poly_plot_MJD'], z = self.ant_z), b_plot_polyfit['poly_plot_L_rf'], c = b_colour, label = f"b cov quality = {b_coverage_score:.3f} \nfit order = {(len(b_plot_polyfit['poly_coeffs'])-1)} \nred chi = {b_plot_polyfit['red_chi']:.3f}  \n +/- {b_plot_polyfit['red_chi_1sig']:.3f}")
                polyfit_handles.append(h3[0])
                polyfit_labels.append( f"{b}'s S = {b_coverage_score:.3f} \n O = {(len(b_plot_polyfit['poly_coeffs'])-1)} \nred chi = {b_plot_polyfit['red_chi']:.3f}  \n +/- {b_plot_polyfit['red_chi_1sig']:.3f}")

        savepath = f"C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS/plots/polyfits/{self.ant_name}_polyfit" 
        plt.xlabel('Days since peak (rest frame time) / days', fontweight = 'bold')
        plt.ylabel(r'Spectral luminosity density (rest-frame) / erg s$\mathbf{^{-1} \AA^{-1}}$', fontweight = 'bold')
        #plt.ylim((-1e41, 5e42))
        plt.title(f'{self.ant_name} polyfit, reference band = {self.ref_band}. Black circle = "straggler"', fontweight = 'bold')
        
        leg1 = plt.legend(handles = polyfit_handles, labels = polyfit_labels, loc = 'lower right', bbox_to_anchor = (1.275, -0.142), fontsize = 6.0, ncols = 2)
        plt.gca().add_artist(leg1) # add this legend to the plot so it doesn't get overwritten by the next legend

        plt.legend(handles = raw_and_interp_handles, labels = raw_and_interp_labels, loc = 'upper right', bbox_to_anchor = (1.275, 1.105), fontsize = 6.0, ncols = 2)
        
        #plt.legend(loc = 'lower right', bbox_to_anchor = (1.275, -0.1), fontsize = 7.5, ncols = 3)
        
        self.fig.subplots_adjust(top=0.92,
                                bottom=0.11,
                                left=0.055,
                                right=0.785,
                                hspace=0.2,
                                wspace=0.2)
        plt.grid()
        plt.savefig(savepath, dpi = 300)
        #plt.show()







    def plot_polyfit_subplot(self):
        subplot_rows_cols = {4: (2, 2),
                             6: (2, 3), 
                             7: (2, 4), 
                             8: (2, 4), 
                             9: (3, 3),
                             10: (3, 4),
                             11: (3, 4), 
                             12: (3, 4), 
                             13: (3, 5), 
                             14: (3, 5), 
                             23: (4, 6)}
        
        subplot_rows_cols = {4: (2, 2),
                             6: (2, 3), 
                             7: (4, 2), 
                             8: (4, 2), 
                             9: (3, 3),
                             10: (4, 3),
                             11: (4, 3), 
                             12: (4, 3), 
                             13: (5, 3), 
                             14: (5, 3), 
                             23: (6, 4)}
        
        no_subplots = len(self.bands)
        nrows, ncols = subplot_rows_cols[no_subplots]
        if no_subplots <= 6:
            figsize = (16, 7.5)
            figsize = (8.2, 5.8)
        else:
            figsize = (8.2, 11.6)

        fig, axs = plt.subplots(nrows, ncols, figsize = figsize)
        axs = axs.ravel() # flatten the 2D array of axes into a 1D array so we can iterate through them

        def standard_form_tex(x, pos):
                if x == 0:
                    return "0"
                exponent = int(np.floor(np.log10(abs(x))))
                coeff = x / (10 ** exponent)
                return rf"${coeff:.1f} \times 10^{{{exponent}}}$"
        formatter = FuncFormatter(standard_form_tex)

        for i, ax in enumerate(axs):
            if i >= no_subplots: # if we have more subplots than bands, break out of the loop and hide the axes of the remaining subplots#
                remaining_axes = axs[i:]
                for ax in remaining_axes: # iterate through the remaiing axes and hide them from the plot
                    ax.axis('off')
                break
            
            ax.yaxis.set_major_formatter(formatter)  
            ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds 
            ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3))
            ax.tick_params(axis='both', labelsize=9.5)

            b = self.bands[i]
            b_colour = self.b_colour_dict[b]
            b_marker = self.b_marker_dict[b]
            b_df = self.b_df_dict[b]
            b_em_cent_wl = b_df['em_cent_wl'].iloc[0]
            b_plot_polyfit = self.plot_results.loc[b]
            b_coverage_score = self.prepping_data.at[b, 'b_coverage_score']
            straggler_df = self.prepping_data.at[b, 'straggler_df']
            b_non_straggler_df = self.prepping_data.at[b, 'non_straggler_df']
            b_interp_df = self.interp_df[self.interp_df['band'] == b].copy()

            ax.errorbar(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = b_df['wm_MJD'], z = self.ant_z), b_df['wm_L_rf'], yerr = b_df['wm_L_rf_err'], fmt = b_marker, markeredgecolor = 'k', markeredgewidth = '1.0', linestyle = 'None', 
                                label = 'data', c = b_colour, zorder = 3)

            ax.scatter(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = straggler_df['wm_MJD'], z = self.ant_z), straggler_df['wm_L_rf'], c = 'k', marker = 'o', s = 70, zorder = 4)
            ax.scatter(self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = straggler_df['wm_MJD'], z = self.ant_z), straggler_df['wm_L_rf'], c = b_colour, marker = 'x', s = 20, zorder = 5)
            ax.errorbar(b_interp_df['d_since_peak'], b_interp_df['L_rf'], yerr = b_interp_df['L_rf_err'], c = 'k', markeredgecolor = 'k', markeredgewidth = '1.0', 
                            linestyle = 'None', alpha = 0.35,  capsize = 5, capthick = 5, label = f'interp')

            if b_non_straggler_df.empty == False: # plot the polynomial fit if we had enough non-straggler datapoints to fit it
                plot_poly_phase = self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = b_plot_polyfit['poly_plot_MJD'], z = self.ant_z)
                ax.plot(plot_poly_phase, b_plot_polyfit['poly_plot_L_rf'], c = 'k')#, c = b_colour)#, 
                        #label = f"S = {b_coverage_score:.1f}, O = {(len(b_plot_polyfit['poly_coeffs'])-1)} \n "+r"$\chi_{\nu}^{2}$ "+f" = {b_plot_polyfit['red_chi']:.1f}  \n +/- {b_plot_polyfit['red_chi_1sig']:.1f}")
                title = fr"{b_em_cent_wl:.0f} $\mathbf{{\AA}}$ ({b})"+f" \nS = {b_coverage_score:.1f}, O = {(len(b_plot_polyfit['poly_coeffs'])-1)}"
                ax.set_xlim((np.min(plot_poly_phase) - 40), (np.max(plot_poly_phase) + 40))
            else:
                title = fr"{b_em_cent_wl:.0f} $\mathbf{{\AA}}$ ({b})"
                ax.set_xlim((b_interp_df['d_since_peak'].min() - 20), (b_interp_df['d_since_peak'].max() + 20))
            #ax.legend(fontsize = 4.5)
            #ax.set_xlim((b_interp_df['d_since_peak'].min() - 30), (b_interp_df['d_since_peak'].max() + 30))
            
            #ax.set_ylim(0.0, (b_interp_df['L_rf'].max()*1.1))
            ax.grid(True)
            if self.ant_name == 'ASASSN-18jd':
                subplot_titlefontsize = 8
                fig.subplots_adjust(top=0.875,
                                    bottom=0.08,
                                    left=0.16,
                                    right=0.948,
                                    hspace=0.728,
                                    wspace= 0.85)

            elif self.ant_name == 'ASASSN-17jz':
                subplot_titlefontsize = 10
                fig.subplots_adjust(top=0.875,
                                    bottom=0.093,
                                    left=0.16,
                                    right=0.968,
                                    hspace=0.573,
                                    wspace=0.49)



            else: 
                
                if no_subplots <= 6:
                    subplot_titlefontsize = 11
                    fig.subplots_adjust(top=0.78,
                                        bottom=0.093,
                                        left=0.18,
                                        right=0.968,
                                        hspace=0.5,
                                        wspace=0.55)
                    
                else: 
                    subplot_titlefontsize = 10.5
                    fig.subplots_adjust(top=0.875,
                                        bottom=0.08,
                                        left=0.16,
                                        right=0.98,
                                        hspace=0.5,
                                        wspace=0.6)                


            ax.set_title(title, fontweight = 'bold', fontsize = subplot_titlefontsize)
        
        if no_subplots <= 6:
            suptitle = f"Polynomial fits to the bands of {self.ant_name}'s\nlight curve"
            ylabel = f'Spectral luminosity density \n'+r'(rest-frame) [erg s$\, \mathbf{^{-1} \, \AA^{-1}}$]'

        else:
            suptitle = f"Polynomial fits to the bands of {self.ant_name}'s\nlight curve"
            ylabel = r'Spectral luminosity density (rest-frame) [erg s$\, \mathbf{^{-1} \, \AA^{-1}}$]'


        axisfontsize = 14
        titlefontsize = 18
        fig.supxlabel('Phase (rest-frame) / days', fontweight = 'bold', fontsize = axisfontsize)
        #fig.supylabel(r'Luminosity spectral density'+"\n"+r' (rest-frame wavelength) \ erg s$\mathbf{^{-1} \AA^{-1}}$', fontweight = 'bold', fontsize = axisfontsize)
        fig.supylabel(ylabel, fontweight = 'bold', fontsize = axisfontsize)
        fig.suptitle(suptitle, fontweight = 'bold', fontsize = titlefontsize)


        savepath = f"C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS/plots/polyfits/{self.ant_name}_polyfit_subplot"
        plt.savefig(savepath, dpi = 300)
        #plt.show()


    @staticmethod
    def convert_MJD_to_restframe_DSP(peak_MJD, MJD, z):
        return (MJD - peak_MJD) / (1 + z)


    
    def calc_days_since_peak(self):
        peak_MJD_cutoff = self.lim_df['wm_MJD'].min() + ((self.lim_df['wm_MJD'].max() - self.lim_df['wm_MJD'].min()) * 0.60) # the peak MJD is not allowed to be past this point, which is 60% of the way across the light curve in MJD
        
        # ref band data
        ref_band_poly_data = self.plot_results.loc[self.ref_band]
        ref_band_poly_MJD = ref_band_poly_data['poly_plot_MJD']
        ref_band_poly_L_rf = ref_band_poly_data['poly_plot_L_rf']

        # mask over the region we don't want it to find the peak (the latter 40% of the light curve)
        mask = ref_band_poly_MJD < peak_MJD_cutoff
        allowed_ref_band_poly_MJD = ref_band_poly_MJD[mask]
        allowed_ref_band_poly_L_rf = ref_band_poly_L_rf[mask]

        # get the index of the peak within the allowed region
        ref_band_max_idx = np.argmax( allowed_ref_band_poly_L_rf )
        self.ref_band_peak_MJD = allowed_ref_band_poly_MJD[ref_band_max_idx]
        self.interp_df['peak_MJD'] = [self.ref_band_peak_MJD]*len(self.interp_df)
        self.interp_df['d_since_peak'] = self.convert_MJD_to_restframe_DSP(peak_MJD = self.ref_band_peak_MJD, MJD = self.interp_df['MJD'], z = self.ant_z)#(self.interp_df['MJD'] - self.interp_df['peak_MJD']) / (1 + self.ant_z) # days since peak in the rest frame
        



    def save_interpolated_df(self):
        if self.save_interp_df == True:
            savepath = f"C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS/data/interpolated_lcs/{self.ant_name}_interp_lc.csv"
            self.interp_df.to_csv(savepath, index = False)



    def run_fitting_pipeline(self):
        self.get_scalefactors()
        self.initialise_plot()
        self.MJD_limit_df()
        self.identify_stragglers_and_score_band()
        self.choose_interp_MJD()
        self.polynomial_fit_and_interp()
        self.calc_days_since_peak()
        if self.plot_polyfit == True:
            self.plot_polyfit_funciton()
            self.plot_polyfit_subplot()
            plt.show()
        self.save_interpolated_df()

        
        



##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# LOAD IN THE INTERPOLATED LIGHT CURVE DATAFRAMES





def load_interp_ANT_data(running_on_server):
    """
    loads in the interpolated ANT data files

    INPUTS:
    -----------
    sunning_on_server: (bool) If True, the function will look for files according to the path structure on the server.


    OUTPUTS:
    ----------
    dataframes: a list of the interpolated ANT data in dataframes
    names: a list of the ANT names
    ANT_bands: a list of lists, each inner list is a list of all of the bands which are present in the light curve

    """
    if running_on_server:
        base_path = ""

    else:
        base_path = "C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS/"
    directory = base_path + "data/interpolated_lcs" 

    dataframes = []
    names = []
    ANT_bands = []

    for file in os.listdir(directory): # file is a string of the file name such as 'file_name.dat'
        if file.endswith('.csv') == False: # ignore the README file
            continue

        ANT_name = file[:-14] # the files are named: ANT_name_interp_lc.csv
        # load in the files
        file_path = os.path.join(directory, file)
        file_df = pd.read_csv(file_path, delimiter = ',') # the lightcurve data in a dataframe
        bands = file_df['band'].unique() # the bands in which this transient has data for

        dataframes.append(file_df)
        names.append(ANT_name)            
        ANT_bands.append(bands)

    return dataframes, names, ANT_bands






##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
##################################################################################################################################################################
# BLACLBODY MODEL FOR REST FRAME LUMINOSITY




def blackbody(lam_cm, R_cm, T_K):
    """
    Planck's blackbody formula modified to give luminosity per unit wavelength in units ergs/s/Angstrom

    INPUTS
    --------------
    lam: the wavelength in cm

    R_cm: Blackbody radius in cm - a parameter to fit for

    T_K: Blackbody temperature in Kelvin - a parameter to fit for

    RETURNS
    --------------
    L: blackbody luminosity per unit wavelength for the wavelength input. Units: ergs/s/Angstrom
    """

    c_cgs = const.c.cgs.value
    h_cgs = const.h.cgs.value
    k_cgs = const.k_B.cgs.value

    C = 8 * (np.pi**2) * h_cgs * (c_cgs**2) * 1e-8 # the constant coefficient of the equation 
    denom = np.exp((h_cgs * c_cgs) / (lam_cm * k_cgs * T_K)) - 1

    L = C * ((R_cm**2) / (lam_cm**5)) * (1 / (denom)) # ergs/s/Angstrom

    return L











#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
# DOUBLE BLACKBODY SED



def double_blackbody(lam, R1, T1, R2, T2):
    """
    A function which returns the sum of two blackbody functions.

    INPUTS
    --------------
    lam: the wavelength in cm

    R1: Blackbody radius in cm - a parameter to fit for

    T1: Blackbody temperature in Kelvin - a parameter to fit for

    R2: Blackbody radius in cm - a parameter to fit for

    T2: Blackbody temperature in Kelvin - a parameter to fit for

    RETURNS
    --------------
    BB1 + BB2: the sum of two blackbody functions. Units: ergs/s/Angstrom
    """
    BB1 = blackbody(lam, R1, T1)
    BB2 = blackbody(lam, R2, T2)

    return BB1 + BB2








def vectorised_blackbody(lam_cm, R_cm, T_K):
    """
    Planck's blackbody formula modified to give luminosity per unit wavelength in units ergs/s/Angstrom

    INPUTS
    --------------
    lam: (N_wl, ) the wavelength in cm

    R_cm: (N_r, ) Blackbody radius in cm - a parameter to fit for

    T_K: (N_t, ) Blackbody temperature in Kelvin - a parameter to fit for

    RETURNS
    --------------
    L: (N_wl, N_r, N_t) blackbody luminosity per unit wavelength for the wavelength input. Units: ergs/s/Angstrom
    """

    c_cgs = const.c.cgs.value
    h_cgs = const.h.cgs.value
    k_cgs = const.k_B.cgs.value

    lam_cm = lam_cm[:, np.newaxis, np.newaxis] # shape (N_wl, 1, 1)
    R_cm, T_K = np.meshgrid(R_cm, T_K) # shape (N_r, N_t) - this is the same as R_cm[:, np.newaxis] * T_K[np.newaxis, :] but more efficient

    C = 8 * (np.pi**2) * h_cgs * (c_cgs**2) * 1e-8 # the constant coefficient of the equation 
    exponent = (h_cgs * c_cgs) / (lam_cm * k_cgs * T_K)
    denom = np.expm1(exponent) # more efficient than using np.exp() -1

    L = C * ((R_cm**2) / (lam_cm**5)) / (denom) # ergs/s/Angstrom

    return L







def vectorised_double_blackbody(lam, R1, T1, R2, T2):
    """
    A function which returns the sum of two blackbody functions.

    INPUTS
    --------------
    lam: the wavelength in cm

    R1: Blackbody radius in cm - a parameter to fit for

    T1: Blackbody temperature in Kelvin - a parameter to fit for

    R2: Blackbody radius in cm - a parameter to fit for

    T2: Blackbody temperature in Kelvin - a parameter to fit for

    RETURNS
    --------------
    BB1 + BB2: the sum of two blackbody functions. Units: ergs/s/Angstrom
    """
    BB1 = vectorised_blackbody(lam, R1, T1) # shape (N_wl, N_r1, N_t1)
    BB2 = vectorised_blackbody(lam, R2, T2) # shape (N_wl, N_r2, N_t2)

    BB1 = BB1[:, :, :, np.newaxis, np.newaxis] # shape (N_wl, N_r1, N_t1, 1, 1)
    BB2 = BB2[:, np.newaxis, np.newaxis, :, :] # shape (N_wl, 1, 1, N_r2, N_t2)


    return BB1 + BB2 # shape (N_wl, N_r1, N_t1, N_r2, N_t2)


#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
# POWER LAW SED





def power_law_SED(lam, A, gamma):
    """
    A function which models a power law SED like rest frame luminosity density = A*(wavelength)**gamma

    INPUTS
    --------------
    lam: (float) wavelength. Units of the wavelength should reflect the units of the luminosity density you're trying to model. If it's ergs/s/Angstrom, then input
    lam in Angstrom, if its ergs/s/cm, then input lam in cm.

    A: (float) Amplitude factor of the power law

    gamma: (float) the power of the power law


    OUTPUTS
    --------------
    L_rf: (float) the value of the rest-frame luminosity (density) given by the power law. (I say luminosity(density) because I often just refer to this as rest frame luminosity, 
            but since it's per unit wavelength, its actually a luminoisty density). Units determined by the luminosity you're trying to model. This model doesn't 
            have much physical meaning, so physical units are not explicitly defined for this model, instead they reflect the luminosity density that we're modelling

    """
    L_rf = A*(lam**gamma)

    return L_rf



#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
#=================================================================================================================================================================
# BLACK BODY FITTING ACROSS THE WHOLE (INTERPOLATED) LIGHT CURVE






class fit_SED_across_lightcurve:
    def __init__(self, interp_df, running_on_server, SED_type, brute_gridsize, DBB_brute_gridsize, error_sampling_size, ant_name, brute_delchi = 2.3, 
                individual_BB_plot = 'whole_lc', no_indiv_SED_plots = 12, show_plots = True, save_indiv_BB_plot = True, save_param_vs_time_plot = True,
                 plot_chi_contour = False, no_chi_contours = 3, save_SED_fit_file = True,
                BB_R_min = 1e13, BB_R_max = 1e19, BB_T_min = 1e3, BB_T_max = 5e5,
                DBB_T1_min = 1e2, DBB_T1_max = 1e4, DBB_T2_min = 1e4, DBB_T2_max = 5e5, DBB_R_min = 1e13, DBB_R_max = 1e19, 
                PL_A_min = 1e42, PL_A_max = 1e51, PL_gamma_min = -5.0, PL_gamma_max = 0.0):
        """
        Fits an SED model to each epoch in the provided ANT light curve. 

        INPUTS
        ---------------
        interp_df: (DataFrame) the ANT's dataframe containing a light curve which has been interpolated using a polynomial fit to each band. 
        Each ANT had a chosen reference band. At the MJD values present in the reference band's real data (and straggler MJDs), the polyfit for all other bands
        were evaluated (under some conditions). Prior to being interpolated, the ANT data should (ideally) be binned into small bins like 1 day, 
        meaning that we will only have 0 or 1 datapoint per band per MJD value (this is only really relevant for the reference band, though, since the interpolation function ensures either 0 or 1
        value per band per MJD value for the interpolated data, since the polynomials are single-valued for any given MJD value). 
        columns: MJD, L_rf, L_rf_err, band, em_cent_wl

        running_on_server: (bool) if True, the paths where we access and store the files will for the server paths. 

        SED_type: (str) options: 'single_BB', 'double_BB', 'power_law'. If 'single_BB', the blackbody fit will be a single blackbody fit. If 'double_BB', the blackbody fit will be a double blackbody fit. 
        If 'power_law', the SED fit will be a power law fit like A*(wavelength)**gamma. 

        brute_gridsize: (int) the number of trial parameter values that will be tried in the brute force method. The number of trial parameter values form a grid of parameters and
        each parameter combination will be tried in the SED fit.

        DBB_brute_gridsize: (int) the number of trial params to use for DBB brute force gridding. the gridsize would be DBB_brute_gridsize^4. This is only used if you want to sample parameter values within 
        the region of parameter space satisfying chi <= best_chi + brute_delchi, where best_chi is the min chi squared value found when using the curve_fit method. This is because the 
        DBB method is very computationally expensive to run a brute force fit for. 

        error_sampling_size: (int) the number of parameter combinations you want to sample from the brute force region of param space for which chi <= min_chi + brute_delchi (where brute_delchi usually =2.3)

        ant_name: (str) the ANT's name

        brute_delchi: (float). When calculating the errors on the model parameters when fitting with the brute force method, you can get 'one-at a time' 1 sigma errors on your parameters 
        by searching the 'ellipse' in parameter space which produces (min_red_chi +/- 1), so brute_delchi=1 here. For a 2 parameter model with 1 sigma errors taken 'jointly' as a joint confidence region, 
        then choose brute_delchi = 2.3. 
        
        the number of sigma that the brute force method will use to calculate the error on the SED fit parameters. 

        individual_BB_plot: (str) a setting for plotting individual epoch SED fits in a grid. opitons: 'UVOT', 'whole_lc' or 'None'. If 'UVOT', the SED fits taken at MJDs 
        which have UVOT data will be shown. If 'whole_lc', the SED fits taken at MJDs across the light curve will be shown. If 'None', no individual SED fits will be shown. 
        The plot will display a grid of SED fits.

        no_indiv_SED_plots: (int) how many individual SEDs you want plotted, if individual_BB_plot != 'None' (if you want the individual SED plot). Options are: 24, 20, 12
        
        show_plots: (bool) if True, the code will plt.show() the plots. You can still save them separately if desired

        save_indiv_BB_plot: (bool) if True, the plot of the individual SED fits will be saved.

        plot_chi_contour: (bool). If True and brute == True, the code will plot some chi squared contour plots in the parameter space. This is helpful to sanity check errors. But only works for PL fits. 

        no_chi_contours: (int). Number of individual plots of chi squared contours for a particular fit to a randomly selected epochs. This has only been implemented in the brute force power law fitting so far
        
        save_SED_fit_file: (bool). If True, saves a file containing the evolution of SED model parameters with phase. 
        
        BB_R_min, BB_R_max, BB_T_min, BB_T_max: (each are floats). The parameter space limits for the single BB SED fits

        DBB_T1_min, DBB_T1_max, DBB_T2_min, DBB_T2_ma, DBB_R_min, DBB_R_max: (each are floats). The parameter space limits for the double BB SED fits

        PL_A_min, PL_A_max, PL_gamma_min, PL_gamma_max: (each are floats). The parameter space limits for the power law SED fitting
        

        """
        self.interp_df = interp_df
        if running_on_server:
            self.base_path = "" # we don't need a base path for the server we use the relative path
        else:
            self.base_path = "C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS/"
        
        self.SED_type = SED_type
        self.curvefit = True # leave as True
        self.brute = True # leave as True
        self.brute_gridsize = brute_gridsize
        self.DBB_brute_gridsize = DBB_brute_gridsize
        self.error_sampling_size = error_sampling_size
        self.ant_name = ant_name
        self.brute_delchi = brute_delchi
        
        self.individual_BB_plot = individual_BB_plot
        self.save_param_vs_time_plot = save_param_vs_time_plot
        self.no_indiv_SED_plots = no_indiv_SED_plots
        self.show_plots = show_plots
        self.save_indiv_BB_plot = save_indiv_BB_plot
        self.no_chi_contours = no_chi_contours
        self.save_SED_fit_file = save_SED_fit_file
        self.plot_chi_contour = plot_chi_contour

        self.guided_UVOT_SED_fits = False # this is automatically set to true if you call self.run_UVOT_guided_SED_fitting_process() for the ANTs which have UVOT data on the rise/peak (which is what allows us to guide the nearby non-UVOT SED fits)


        # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # if we scale down the radius values to explore - this requires scaling down the rest frame luminosity by (R_scalefactor)**2 because L ~ R^2 
        self.R_scalefactor = 1e-16
        self.L_scalefactor = (self.R_scalefactor)**2
        self.interp_df['L_rf_scaled'] = self.interp_df['L_rf'] * self.L_scalefactor
        self.interp_df['L_rf_err_scaled'] = self.interp_df['L_rf_err'] * self.L_scalefactor
        interp_df['em_cent_wl_cm'] = interp_df['em_cent_wl'] * 1e-8 # the blackbody function takes wavelength in centimeters. 1A = 1e-10 m.     1A = 1e-8 cm

        # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # define limits on our SED model parameters and the results dataframe (whole columns are dependent on the SED type)
        self.mjd_values = self.interp_df['MJD'].unique()

        if self.SED_type == 'single_BB':
            #                 0          1             2            3          4            5            6               7              8                  9               10            11                  12                  13                 14                  15                      16                 17                   18                19          20
            self.columns = ['MJD', 'd_since_peak', 'no_bands', 'cf_T_K', 'cf_T_err_K', 'cf_R_cm', 'cf_R_err_cm', 'cf_covariance', 'cf_red_chi', 'cf_chi_sigma_dist', 'red_chi_1sig', 'brute_T_K', 'brute_T_err_lower_K', 'brute_T_err_upper_K', 'brute_R_cm', 'brute_R_err_lower_cm', 'brute_R_err_upper_cm', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'bands', 'em_cent_wls']
    
            #                            0              1          2          3              4                       5                6              7              8              9            
            self.sampled_columns = ['d_since_peak', 'no_bands', 'bands', 'em_cent_wls', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'sampled_T_K', 'sampled_R_cm', 'sampled_chi'] # don't include MJD in the columns since we index with it
            
            self.BB_R_min = BB_R_min
            self.BB_R_max = BB_R_max
            self.BB_T_min = BB_T_min
            self.BB_T_max = BB_T_max

            self.BB_R_min_sc = BB_R_min * self.R_scalefactor # scaling down the bounds for the radius parameter space
            self.BB_R_max_sc = BB_R_max * self.R_scalefactor


        elif self.SED_type == 'double_BB':  
            ##                 0             1           2            3          4              5            6            7            8            9            10              11               12                 13           14        15          16               17          18                          19                 20                    21                    22                    23               24                    25                     26                27                    28                         29                 30                   31              32              33                 34                 35                 36                 37                 38                 39
            #self.columns = ['MJD', 'd_since_peak', 'no_bands', 'cf_T1_K', 'cf_T1_err_K', 'cf_R1_cm', 'cf_R1_err_cm', 'cf_T2_K', 'cf_T2_err_K', 'cf_R2_cm', 'cf_R2_err_cm', 'cf_red_chi', 'cf_chi_sigma_dist', 'red_chi_1sig', 'cf_chi', 'bands', 'em_cent_wls', 'brute_T1_K', 'brute_T1_err_lower_K', 'brute_T1_err_upper_K', 'brute_R1_cm', 'brute_R1_err_lower_cm', 'brute_R1_err_upper_cm', 'brute_T2_K', 'brute_T2_err_lower_K', 'brute_T2_err_upper_K', 'brute_R2_cm', 'brute_R2_err_lower_cm', 'brute_R2_err_upper_cm', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'cf_T1_err_lower', 'cf_T1_err_upper', 'cf_R1_err_lower', 'cf_R1_err_upper', 'cf_T2_err_lower', 'cf_T2_err_upper', 'cf_R2_err_lower', 'cf_R2_err_upper']
            
            #                 0             1           2            3          4              5            6            7            8            9            10              11               12                 13           14        15          16                      
            self.columns = ['MJD', 'd_since_peak', 'no_bands', 'cf_T1_K', 'cf_T1_err_K', 'cf_R1_cm', 'cf_R1_err_cm', 'cf_T2_K', 'cf_T2_err_K', 'cf_R2_cm', 'cf_R2_err_cm', 'cf_red_chi', 'cf_chi_sigma_dist', 'red_chi_1sig', 'cf_chi', 'bands', 'em_cent_wls']
            

            #                            0               1         2            3              4                     5                6              7              8               9                 10             11           
            self.sampled_columns = ['d_since_peak', 'no_bands', 'bands', 'em_cent_wls', 'cf_red_chi', 'cf_chi_sigma_dist', 'cf_chi', 'sampled_T1_K', 'sampled_R1_cm', 'sampled_T2_K', 'sampled_R2_cm', 'sampled_chi'] # don't include MJD in the columns since we index with it
            self.DBB_T1_min = DBB_T1_min
            self.DBB_T1_max = DBB_T1_max
            self.DBB_T2_min = DBB_T2_min
            self.DBB_T2_max = DBB_T2_max
            self.DBB_R_min = DBB_R_min
            self.DBB_R_max = DBB_R_max

            self.DBB_R_min_sc = self.DBB_R_min * self.R_scalefactor # scaling down the bounds for the radius parameter space (we input this into curve_fit as the bound rather than the unscaled one)
            self.DBB_R_max_sc = self.DBB_R_max * self.R_scalefactor


        elif self.SED_type == 'power_law':
            #                  0          1              2        3         4           5             6             7                8                  9             10                11               12                 13              14                    15                 16
            self.columns = ['MJD', 'd_since_peak', 'no_bands', 'cf_A', 'cf_A_err', 'cf_gamma', 'cf_gamma_err', 'cf_red_chi', 'cf_chi_sigma_dist', 'red_chi_1sig', 'brute_A', 'brute_A_err_lower', 'brute_A_err_upper', 'brute_gamma', 'brute_gamma_err', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'bands', 'em_cent_wls']
            
            #                            0              1          2           3              4                     5                  6           7             8                9              
            self.sampled_columns = ['d_since_peak', 'no_bands', 'bands', 'em_cent_wls', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'sampled_A', 'sampled_gamma', 'sampled_chi'] # don't include MJD in the columns since we index with it
            
            self.PL_A_max = PL_A_max
            self.PL_A_min = PL_A_min
            self.PL_gamma_max = PL_gamma_max
            self.PL_gamma_min = PL_gamma_min

            self.A_scalefactor = self.L_scalefactor # scaling down the bounds for the amplitude parameter space (we input this into curve_fit as the bound rather than the unscaled one)
            self.PL_sc_A_max = self.PL_A_max * self.A_scalefactor
            self.PL_sc_A_min = self.PL_A_min * self.A_scalefactor

            if self.plot_chi_contour == True:
                self.contour_MJDs = np.random.choice(self.mjd_values, self.no_chi_contours)

        self.BB_fit_results = pd.DataFrame(columns = self.columns, index = self.mjd_values)

        sample_index = pd.MultiIndex.from_product([self.mjd_values, range(error_sampling_size)], names = ['MJD', 'sample']) # use a multiindex so you refer to a particular row using .loc[(MJD_value, sample_number)], and refer to all samples for a particular MJD using .loc[MJD_value], allows for easy grouping
        self.BB_fit_samples = pd.DataFrame(columns = self.sampled_columns, index = sample_index)
        self.BB_fit_samples.loc[:, :] = np.nan # set all cells to nan to be later overwritten. We do this because when curve_fits fail for the DBB, we won't reach the brute forcing and sampling so the rows associated to the MJD with the failed curve_fit would be empty, so we want these to be filled with NaN values. 








    
    def BB_curvefit(self, MJD, MJD_df, R_sc_min, R_sc_max, T_min, T_max):
        """
        INPUTS
        ---------------
        R_sc_min: the min value of SCALED BB radius to try

        R_sc_max: the max value of SCALED BB radius to try

        T_min: the min value of BB temperature to try

        T_max: the max value of BB temperature to try
        """
        try:
            popt, pcov = opt.curve_fit(blackbody, xdata = MJD_df['em_cent_wl_cm'], ydata = MJD_df['L_rf_scaled'], sigma = MJD_df['L_rf_err_scaled'], absolute_sigma = True, 
                                    bounds = (np.array([R_sc_min, T_min]), np.array([R_sc_max, T_max])))
            sc_cf_R, cf_T = popt
            sc_cf_R_err = np.sqrt(pcov[0, 0])
            cf_T_err = np.sqrt(pcov[1, 1])
            cf_R = sc_cf_R / self.R_scalefactor
            cf_R_err = sc_cf_R_err / self.R_scalefactor
            cf_correlation = pcov[1,0] / (cf_T_err * sc_cf_R_err) # using the scaled R error here since curve_fit is not told about the fact that R has been scaled down

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # calculate the reduced chi squared of the curve_fit result
            BB_sc_L_chi = [blackbody(wl_cm, sc_cf_R, cf_T) for wl_cm in MJD_df['em_cent_wl_cm']] # evaluating the BB model from curve_fit at the emitted central wavelengths present in our data to use for chi squared calculation
            cf_red_chi, red_chi_1sig = chisq(y_m = BB_sc_L_chi, y = MJD_df['L_rf_scaled'], yerr = MJD_df['L_rf_err_scaled'], M = 2, reduced_chi = True)
            cf_chi_sigma_dist = (cf_red_chi - 1)/red_chi_1sig

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # add the result to the results row which will be appended to the results dataframe
            self.BB_fit_results.loc[MJD, self.columns[3:11]] = [cf_T, cf_T_err, cf_R, cf_R_err, cf_correlation, cf_red_chi, cf_chi_sigma_dist, red_chi_1sig]  


        except RuntimeError:
            print(f'{Fore.RED} WARNING - Curve fit failed for MJD = {MJD} {Style.RESET_ALL}')
            self.no_failed_curvefits += 1 # counting the number of failed curve fits
            self.BB_fit_results.loc[MJD, self.columns[3:11]] = np.nan

        





    def power_law_curvefit(self, MJD, MJD_df, A_sc_min, A_sc_max, gamma_min, gamma_max):
        """
        INPUTS
        -----------------       
        A_sc_min: the minimum value of SCALED A to test

        A_sc_max: the maximum value of SCALED A to test

        gamma_min: the minimum value of gamma to test

        gamma_max: the maximum value of gamma to test
        
        """
        try:
            A_scalefactor = self.L_scalefactor # L = A(wavelength)^gamma . If we scale L down by 5, it would scale A down by 5
            popt, pcov = opt.curve_fit(power_law_SED, xdata = MJD_df['em_cent_wl'], ydata = MJD_df['L_rf_scaled'], sigma = MJD_df['L_rf_err_scaled'], absolute_sigma = True, 
                                       bounds = (np.array([A_sc_min, gamma_min]), np.array([A_sc_max, gamma_max])))
            cf_A_sc = popt[0]
            cf_A = cf_A_sc/A_scalefactor
            cf_gamma = popt[1]
            cf_A_err_sc = np.sqrt(pcov[0, 0])
            cf_A_err = cf_A_err_sc/A_scalefactor
            cf_gamma_err = np.sqrt(pcov[1, 1])
            cf_correlation = pcov[1, 0] / (cf_A_err_sc * cf_gamma_err) # I feel like we should use A's scaled error here, since curve_fit is not told about the fact that A has been scaled down at all.  

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # calculate the reduced chi squared of the curve_fit result
            PL_sc_L_chi = [power_law_SED(wl_A, cf_A_sc, cf_gamma) for wl_A in MJD_df['em_cent_wl']] # evaluating the power law SED model from curve_fit at the emitted central wavelengths present in our data to use for chi squared calculation
            cf_red_chi, red_chi_1sig = chisq(y_m = PL_sc_L_chi, y = MJD_df['L_rf_scaled'], yerr = MJD_df['L_rf_err_scaled'], M = 2, reduced_chi = True)
            cf_chi_sigma_dist = (cf_red_chi - 1)/red_chi_1sig

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # add the result to the results row which will be appended to the results dataframe
            self.BB_fit_results.loc[MJD, self.columns[3:10]] = [cf_A, cf_A_err, cf_gamma, cf_gamma_err, cf_red_chi, cf_chi_sigma_dist, red_chi_1sig]


        except RuntimeError:
            print(f'{Fore.RED} WARNING - Curve fit failed for MJD = {MJD} {Style.RESET_ALL}')
            self.no_failed_curvefits += 1 # counting the number of failed curve fits
            self.BB_fit_results.loc[MJD, self.columns[3:10]] = np.nan




    
    def power_law_brute(self, MJD, MJD_df, A_min, A_max, gamma_min, gamma_max, UVOT_guided_params = None):
        """
        fits a power law SED to the data for a given MJD. For this brute force gridding, since gamma only really needs to explore values between -5 to 0, 
        I decide to balance computational time and accuracy by increasing the number of A values that we try, and decreasing the number of gamma values
        so that it takes just as long as if we had a square parameter grid but I think we need better resolution in A so we're prioritising it a bit.


        INPUTS
        -----------------
        A_min: the minimum value of A to test

        A_max: the maximum value of A to test

        gamma_min: the minimum value of gamma to test

        gamma_max: the maximum value of gamma to test

        UVOT_guided_params: (list) if you are using a UVOT guided fitting process, this is the list of UVOT-constrained parameter space to take the model params from. 
                            Input these guided parameters in the order: A_min, A_max, gamma_min, gamma_max 
                            You must explore the entire parameter space still to ensure that you fully capture the delta_chi = 2.3 region in parameter space to ensure that
                            you know the largest and smallest parameter values which fall within this region to get the correct model parameter uncertainties. We use
                            the UVOT guided parameters to restrict the region of parameter space that we allow the final model parameters to be chosen from. 
        """
        # HERE I AM EXPLORING (grid_scalefactor)^2 TIMES AS MANY VALUES OF A AS OPPOSED TO GAMMA SO THIS IS A RECTANGULAR PARAMETER GRID NOW, BECAUSE I THINK THE A IS STRUGGING TO BE CONSTRAINED MORE THAN GAMMA
        grid_scalefactor = 2
        A_values = np.logspace(np.log10(A_min), np.log10(A_max), int(np.round(self.brute_gridsize*grid_scalefactor, -1)))
        sc_A_values = A_values*self.A_scalefactor
        gamma_values = np.linspace(gamma_min, gamma_max, int(np.round(self.brute_gridsize/grid_scalefactor)))

        wavelengths = MJD_df['em_cent_wl'].to_numpy() # the emitted central wavelengths of the bands present at this MJD value
        L_rfs = MJD_df['L_rf_scaled'].to_numpy() # the scaled rest frame luminosities of the bands present at this MJD value
        L_rf_errs = MJD_df['L_rf_err_scaled'].to_numpy() # the scaled rest frame luminosity errors of the bands present at this MJD value

        PL_L_sc = power_law_SED(wavelengths[:, np.newaxis, np.newaxis], sc_A_values[np.newaxis, :, np.newaxis], gamma_values[np.newaxis, np.newaxis, :]) # the calculated value of scaled rest frame luminosity using this value of T and scaled R
        
        # calculate the chi squared of the fit
        chi = np.sum((L_rfs[:, np.newaxis, np.newaxis] - PL_L_sc)**2 / L_rf_errs[:, np.newaxis, np.newaxis]**2, axis = 0) # the chi squared values for each combination of R and T
        
        if UVOT_guided_params is None:
            min_chi = np.min(chi) # the minimum chi squared value
            row, col = np.where(chi == min_chi) # the row and column indices of the minimum chi squared value

        elif UVOT_guided_params is not None:
            UVOT_A_min, UVOT_A_max, UVOT_gamma_min, UVOT_gamma_max = UVOT_guided_params

            # create masks to go over the chi grid
            A_mask = (A_values >= UVOT_A_min) & (A_values <= UVOT_A_max)
            gamma_mask = (gamma_values >= UVOT_gamma_min) & (gamma_values <= UVOT_gamma_max)

            # apply the masks to the chi grid, A values and gamma values
            UVOT_masked_chi = chi[np.ix_(A_mask, gamma_mask)]
            UVOT_masked_A_values = A_values[A_mask]
            UVOT_masked_gamma_values = gamma_values[gamma_mask]

            # find the min chi in the UVOT masked chi grid
            min_chi = np.min(UVOT_masked_chi)
            row, col = np.where(UVOT_masked_chi == min_chi)
        
        

        if (len(row) == 1) & (len(col) == 1): 
            r = row[0]
            c = col[0]
            N_M = len(MJD_df['band']) - 2

            if UVOT_guided_params is None:
                brute_gamma = gamma_values[c] # the parameters which give the minimum chi squared
                brute_A = A_values[r] 
            else:
                brute_gamma = UVOT_masked_gamma_values[c]
                brute_A = UVOT_masked_A_values[r]
            


            if N_M > 0: # this is for when we try to 'fit' a BB to 2 datapoints, since we have 2 parameters, we can't calculate a reduced chi squared value......
                brute_red_chi = min_chi / N_M
                red_chi_1sig = np.sqrt(2/N_M)
                brute_chi_sigma_dist = (brute_red_chi - 1) / red_chi_1sig
            else:
                brute_red_chi = np.nan
                red_chi_1sig = np.nan
                brute_chi_sigma_dist = np.nan



            # getting the errors on the model parameters
            threshold = min_chi + self.brute_delchi
            mask = (chi <= threshold)

            A_grid, gamma_grid = np.meshgrid(A_values, gamma_values, indexing = 'ij')
            masked_chi = chi[mask]
            masked_A = A_grid[mask]
            masked_gamma = gamma_grid[mask]

            gamma_err_upper = np.max(masked_gamma) - brute_gamma
            gamma_err_lower = brute_gamma - np.min(masked_gamma)
            brute_gamma_err = (gamma_err_lower + gamma_err_upper)/2 # take the mean (this assumes that gamma's lower and upper error are quite close in value, if they aren't we should decrease the grid spacing)

            A_err_upper = np.max(masked_A) - brute_A # getting assymetric errors since our trialed parameter grids were logarithmically spaced, so you wouldn't expect a symmetric error about the model paremeter
            A_err_lower = brute_A - np.min(masked_A)


            # sample param values from the uncertainty region
            if UVOT_guided_params is not None:
                UVOT_guidance_mask = ((masked_A >= UVOT_A_min) & (masked_A <= UVOT_A_max) & (masked_gamma >= UVOT_gamma_min) & (masked_gamma <= UVOT_gamma_max))
                masked_chi = masked_chi[UVOT_guidance_mask]
                masked_A = masked_A[UVOT_guidance_mask]
                masked_gamma = masked_gamma[UVOT_guidance_mask]

            weights = 1/masked_chi
            weights /= np.sum(weights)

            sampled_indicies = np.random.choice(len(weights), size = self.error_sampling_size, p = weights, replace = True)

            sampled_A = masked_A[sampled_indicies]
            sampled_gamma = masked_gamma[sampled_indicies]
            sampled_chi = masked_chi[sampled_indicies]



            
            # -------------------------------------------------------------------------------------------------------------------------------------------------
            # plotting a contour plot of chi squareds for randomly chosen when desired
            if self.plot_chi_contour:
                if MJD in self.contour_MJDs:
                    fig, ax = plt.subplots(figsize = (16, 7.2))
                    A_grid, gamma_grid = np.meshgrid(A_values, gamma_values)
                    chi_cutoff = 2.3
                    masked_chi = np.ma.masked_where((chi > (min_chi + chi_cutoff)), chi)
                    sc = ax.pcolormesh(A_grid, gamma_grid, masked_chi.T, cmap = 'jet', zorder = 2)
                    high_chi_mask = np.where((chi > (min_chi + chi_cutoff)), 100, np.nan)
                    ax.pcolormesh(A_grid, gamma_grid, high_chi_mask.T, color = 'k', zorder = 1)

                    fig.colorbar(sc, ax = ax, label = r'$\mathbf{\chi^2}$')
                    ax.errorbar(brute_A, brute_gamma, yerr = brute_gamma_err, xerr = ([A_err_lower], [A_err_upper]), markersize = 15, fmt = '*', mec = 'k', mew = '0.5', color = 'white', zorder = 3)
                    ax.set_xlabel('A', fontweight = 'bold')
                    ax.set_ylabel(f'$\mathbf{{\gamma}}$', fontweight = 'bold')
                    ax.set_xlim(((brute_A/50), (brute_A*50)))
                    ax.set_ylim(((brute_gamma - brute_gamma_err*2), (brute_gamma + brute_gamma_err*2)))
                    ax.set_xscale('log')
                    ax.set_title(f'{self.ant_name},    MJD = {MJD:.1f}, \n'+ fr"$ \mathbf{{ A = {brute_A:.1e}^{{+{A_err_upper:.1e}}}_{{-{A_err_lower:.1e}}} }}$    "+ fr'$\mathbf{{  \gamma = {brute_gamma:.1f} \pm {brute_gamma_err:.1f}  }}$' + r'    $\mathbf{\chi}$ sig dist'+ f' = {brute_chi_sigma_dist:.2e}', fontweight = 'bold') 
                    plt.show() #                                            fr"$ \mathbf{{ A = {brute_A:.1e}^{{+{A_err_upper:.1e}}}_{{-{A_err_lower:.1e}}} }}$"

  
        else:
            print()
            print(f"{Fore.RED} WARNING - MULTIPLE R AND T PARAMETER PAIRS GIVE THIS MIN CHI VALUE. MJD = {MJD_df['MJD'].iloc[0]} \n Ts = {[A_values[r] for r in row]}, Rs = {[gamma_values[c] for c in col]}")
            print(f"Chi values = {chi[row, col]} {Style.RESET_ALL}")
            print()

        
        #self.BB_fit_results.at[MJD, 'brute_A'] = brute_A
        #self.BB_fit_results.at[MJD, 'brute_A_err'] = brute_A_err
        self.BB_fit_results.loc[MJD, self.columns[10:18]] = [brute_A, A_err_lower, A_err_upper, brute_gamma, brute_gamma_err, brute_red_chi, brute_chi_sigma_dist, min_chi] 

        # save the sampled parameters to the dataframe
        #                            0              1          2           3              4                     5                  6           7             8                9              
        #self.sampled_columns = ['d_since_peak', 'no_bands', 'bands', 'em_cent_wls', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'sampled_A', 'sampled_gamma', 'sampled_chi'] # don't include MJD in the columns since we index with it
            
        MJD_d_since_peak = MJD_df['d_since_peak'].iloc[0]
        MJD_bands = list(MJD_df['band'].unique())
        MJD_no_bands = len( MJD_bands ) # the number of bands (and therefore datapoints) we have available at this MJD for the BB fit
        MJD_em_cent_wls = list(MJD_df['em_cent_wl'].unique())

        for i in range(self.error_sampling_size):
            sample_row_dict = {'d_since_peak': MJD_d_since_peak, 
                               'no_bands': MJD_no_bands, 
                               'bands': MJD_bands, 
                               'em_cent_wls': MJD_em_cent_wls, 
                               'brute_red_chi': brute_red_chi, 
                               'brute_chi_sigma_dist': brute_chi_sigma_dist, 
                               'brute_chi': min_chi, 
                               'sampled_A': sampled_A[i], 
                               'sampled_gamma': sampled_gamma[i], 
                               'sampled_chi': sampled_chi[i]}
            
            for key, value in sample_row_dict.items():
                self.BB_fit_samples.at[(MJD, i), key] = value




    def BB_brute(self, MJD, MJD_df, R_sc_min, R_sc_max, T_min, T_max, UVOT_guided_params = None):
        """
        INPUTS
        ---------------
        R_sc_min: the min value of SCALED BB radius to try

        R_sc_max: the max value of SCALED BB radius to try

        T_min: the min value of BB temperature to try

        T_max: the max value of BB temperature to try

        UVOT_guided_params: (list) if you are using a UVOT guided fitting process, this is the list of UVOT-constrained parameter space to take the model params from. 
                            Input these guided parameters in the order: R_sc_min, R_sc_max, T_min, T_max. 
                            You must explore the entire parameter space still to ensure that you fully capture the delta_chi = 2.3 region in parameter space to ensure that
                            you know the largest and smallest parameter values which fall within this region to get the correct model parameter uncertainties. We use
                            the UVOT guided parameters to restrict the region of parameter space that we allow the final model parameters to be chosen from. 
        """
        # creating the values of R and T that we will try
        # the number of R and T values to trial in the grid. The combinations of R and T form a 2D grid, so the number of R and T values that we try give the side lengths of the grid
        sc_R_values = np.logspace(np.log10(R_sc_min), np.log10(R_sc_max), self.brute_gridsize)
        T_values = np.logspace(np.log10(T_min), np.log10(T_max), self.brute_gridsize)
        #R_values = sc_R_values / self.R_scalefactor # use this to return the grid of parameter values tried

        wavelengths = MJD_df['em_cent_wl_cm'].to_numpy() # the emitted central wavelengths of the bands present at this MJD value
        L_rfs = MJD_df['L_rf_scaled'].to_numpy() # the scaled rest frame luminosities of the bands present at this MJD value
        L_rf_errs = MJD_df['L_rf_err_scaled'].to_numpy() # the scaled rest frame luminosity errors of the bands present at this MJD value

        # create a 3D array of the blackbody luminosities for each combination of R and T. This is done by broadcasting the 1D arrays of wavelengths, R values and T values
        # the 3D array will have dimensions (len(wavelengths), len(R_values), len(T_values)) and will contain the blackbody luminosities for each combination of R and T for each wavelength value
        BB_L_sc = blackbody(wavelengths[:, np.newaxis, np.newaxis], sc_R_values[np.newaxis, :, np.newaxis], T_values[np.newaxis, np.newaxis, :]) # the calculated value of scaled rest frame luminosity using this value of T and scaled R

        # calculate the chi squared of the fit
        chi = np.sum((L_rfs[:, np.newaxis, np.newaxis] - BB_L_sc)**2 / L_rf_errs[:, np.newaxis, np.newaxis]**2, axis = 0) # the chi squared values for each combination of R and T
        
        # FIND MIN CHI 
        # if we are doing a UVOT guided approach, then restrict the chi grid to the regions of parameter space that the UVOT fits allow to take the model parameters from, 
        # then calculate the model parameter uncertainties using the entire chi grid
        if UVOT_guided_params is None: # if you're not doing UVOT guided fitting
            min_chi = np.min(chi) # the minimum chi squared value
            row, col = np.where(chi == min_chi) # the row and column indices of the minimum chi squared value

        elif UVOT_guided_params is not None: # if you DO want UVOT-guided fitting
            UVOT_R_sc_min, UVOT_R_sc_max, UVOT_T_min, UVOT_T_max = UVOT_guided_params

            # create masks to go over the chi grid
            sc_R_mask = (sc_R_values >= UVOT_R_sc_min) & (sc_R_values <= UVOT_R_sc_max)
            T_mask = (T_values >= UVOT_T_min) & (T_values <= UVOT_T_max)

            # masked chi, sc_R_values and T_values
            UVOT_masked_chi = chi[np.ix_(sc_R_mask, T_mask)]
            UVOT_masked_sc_R_values = sc_R_values[sc_R_mask]
            UVOT_masked_T_values = T_values[T_mask]

            # find the min chi within the allowable region of parameter space
            min_chi = np.min(UVOT_masked_chi)
            row, col = np.where(UVOT_masked_chi == min_chi)


        

        if (len(row) == 1) & (len(col) == 1): 
            r = row[0]
            c = col[0]
            N_M = len(MJD_df['band']) - 2

            if UVOT_guided_params is None:
                brute_T = T_values[c] # the parameters which give the minimum chi squared
                brute_R = sc_R_values[r] / self.R_scalefactor
            else:
                brute_T = UVOT_masked_T_values[c]
                brute_R = UVOT_masked_sc_R_values[r] / self.R_scalefactor
            

            if N_M > 0: # this is for when we try to 'fit' a BB to 2 datapoints, since we have 2 parameters, we can't calculate a reduced chi squared value......
                brute_red_chi = min_chi / N_M
                red_chi_1sig = np.sqrt(2/N_M)
                brute_chi_sigma_dist = (brute_red_chi - 1) / red_chi_1sig
            else:
                brute_red_chi = np.nan
                red_chi_1sig = np.nan
                brute_chi_sigma_dist = np.nan

        else:
            print()
            print(f"{Fore.RED} WARNING - MULTIPLE R AND T PARAMETER PAIRS GIVE THIS MIN CHI VALUE. MJD = {MJD_df['MJD'].iloc[0]} \n Ts = {[T_values[c] for c in col]}, Rs = {[sc_R_values[r]/self.R_scalefactor for r in row]}")
            print(f"Chi values = {chi[row, col]} {Style.RESET_ALL}")
            print()



        # calculate uncertainties on model params using the brute force method
        threshold = min_chi + self.brute_delchi
        mask = chi <= threshold

        R_sc_grid, T_grid = np.meshgrid(sc_R_values, T_values, indexing = 'ij')
        masked_chi = chi[mask]
        masked_R_sc = R_sc_grid[mask]
        masked_T = T_grid[mask]

        brute_R_err_upper = (np.max(masked_R_sc) / self.R_scalefactor) - brute_R
        brute_R_err_lower = brute_R - (np.min(masked_R_sc) / self.R_scalefactor)
        brute_T_err_upper = np.max(masked_T) - brute_T
        brute_T_err_lower = brute_T - np.min(masked_T)

        if UVOT_guided_params is not None: # if we want UVOT-guided fitting, we must only sample values from within the UVOT-guided bounds, so this prevents us from sampling from the parts of the error bars which go beyond the UVOT guided regions. 
            UVOT_guidance_mask = ((masked_T <= UVOT_T_max) & (masked_T >= UVOT_T_min) & (masked_R_sc <= UVOT_R_sc_max) & (masked_R_sc >= UVOT_R_sc_min))
            masked_chi = masked_chi[UVOT_guidance_mask]
            masked_R_sc = masked_R_sc[UVOT_guidance_mask]
            masked_T = masked_T[UVOT_guidance_mask]

        # sample values from the uncertainty region
        weights = 1/masked_chi
        weights /= np.sum(weights)

        sampled_indicies = np.random.choice(len(weights), size = self.error_sampling_size, p = weights, replace = True) # sample parameter combinations from the chi grid, where the probability is proportional to 1/chi

        sampled_R = masked_R_sc[sampled_indicies] / self.R_scalefactor
        sampled_T = masked_T[sampled_indicies]
        sampled_chi = masked_chi[sampled_indicies]


        # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # add the result to the results row which will be appended to the results dataframe
        self.BB_fit_results.loc[MJD, self.columns[10:20]] = [red_chi_1sig,    brute_T,     brute_T_err_lower,     brute_T_err_upper,     brute_R,     brute_R_err_lower,      brute_R_err_upper,     brute_red_chi,    brute_chi_sigma_dist, min_chi]
        #                                                   'red_chi_1sig', 'brute_T_K', 'brute_T_err_lower_K', 'brute_T_err_upper_K', 'brute_R_cm', 'brute_R_err_lower_cm', 'brute_R_err_upper_cm', 'brute_red_chi', 'brute_chi_sigma_dist']


        # add the sampled params to the sampled param df
        #                            0              1          2          3              4                       5                6              7              8              9            
        #self.sampled_columns = ['d_since_peak', 'no_bands', 'bands', 'em_cent_wls', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'sampled_T_K', 'sampled_R_cm', 'sampled_chi']
        MJD_d_since_peak = MJD_df['d_since_peak'].iloc[0]
        MJD_bands = list(MJD_df['band'].unique())
        MJD_no_bands = len( MJD_bands ) # the number of bands (and therefore datapoints) we have available at this MJD for the BB fit
        MJD_em_cent_wls = list(MJD_df['em_cent_wl'].unique())

        for i in range(self.error_sampling_size):
            sample_row_dict = {'d_since_peak': MJD_d_since_peak, 
                               'no_bands': MJD_no_bands, 
                               'bands': MJD_bands, 
                               'em_cent_wls': MJD_em_cent_wls, 
                               'brute_red_chi': brute_red_chi, 
                               'brute_chi_sigma_dist': brute_chi_sigma_dist, 
                               'brute_chi': min_chi, 
                               'sampled_T_K': sampled_T[i], 
                               'sampled_R_cm': sampled_R[i], 
                               'sampled_chi': sampled_chi[i]}

            for key, value in sample_row_dict.items():
                self.BB_fit_samples.at[(MJD, i), key] = value
            








    def double_BB_curvefit(self, MJD, MJD_df, R1_sc_min, R1_sc_max, T1_min, T1_max, R2_sc_min, R2_sc_max, T2_min, T2_max, return_params = False):
        try:
            popt, pcov = opt.curve_fit(double_blackbody, xdata = MJD_df['em_cent_wl_cm'], ydata = MJD_df['L_rf_scaled'], sigma = MJD_df['L_rf_err_scaled'], absolute_sigma = True, 
                                    bounds = (np.array([R1_sc_min, T1_min, R2_sc_min, T2_min]), np.array([R1_sc_max, T1_max, R2_sc_max, T2_max])))
                                    #                  (R1_min,   T1_min,   R2_min,  T2_min)           (R1_max,   T1_max,  R2_max,  T2_max)
            
            sc_cf_R1, cf_T1, sc_cf_R2, cf_T2 = popt
            sc_cf_R1_err = np.sqrt(pcov[0, 0])
            cf_T1_err = np.sqrt(pcov[1, 1])
            sc_cf_R2_err = np.sqrt(pcov[2, 2])
            cf_T2_err = np.sqrt(pcov[3, 3])
            cf_R1 = sc_cf_R1 / self.R_scalefactor
            cf_R1_err = sc_cf_R1_err / self.R_scalefactor
            cf_R2 = sc_cf_R2 / self.R_scalefactor
            cf_R2_err = sc_cf_R2_err / self.R_scalefactor
            cf_cov = pcov[1,0]  # BUT THIS IS PROBABLY THE COVARIANCE BETWEEN JUST THE T1 AND R1 PARAMETERS OR SOMETHING, NOT THE COVARIANCE BETWEEN ALL 4 PARAMETERS. 

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # calculate the reduced chi squared of the curve_fit result
            BB_sc_L_chi = [double_blackbody(wl_cm, sc_cf_R1, cf_T1, sc_cf_R2, cf_T2) for wl_cm in MJD_df['em_cent_wl_cm']] # evaluating the BB model from curve_fit at the emitted central wavelengths present in our data to use for chi squared calculation
            cf_chi, cf_red_chi, red_chi_1sig = chisq(y_m = BB_sc_L_chi, y = MJD_df['L_rf_scaled'], yerr = MJD_df['L_rf_err_scaled'], M = 4, reduced_chi = False, chi_AND_redchi = True)
            cf_chi_sigma_dist = (cf_red_chi - 1)/red_chi_1sig

            # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            # add the result to the results row which will be appended to the results dataframe
            #                 0             1           2            3          4              5            6            7            8            9            10              11               12                 13           14        15          16               17          18                          19                 20                    21                    22                    23               24                    25                     26                27                    28                         29                 30                   31 
            #self.columns = ['MJD', 'd_since_peak', 'no_bands', 'cf_T1_K', 'cf_T1_err_K', 'cf_R1_cm', 'cf_R1_err_cm', 'cf_T2_K', 'cf_T2_err_K', 'cf_R2_cm', 'cf_R2_err_cm', 'cf_red_chi', 'cf_chi_sigma_dist', 'red_chi_1sig', 'cf_chi', 'bands', 'em_cent_wls', 'brute_T1_K', 'brute_T1_err_lower_K', 'brute_T1_err_upper_K', 'brute_R1_cm', 'brute_R1_err_lower_cm', 'brute_R1_err_upper_cm', 'brute_T2_K', 'brute_T2_err_lower_K', 'brute_T2_err_upper_K', 'brute_R2_cm', 'brute_R2_err_lower_cm', 'brute_R2_err_upper_cm', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi']
            self.BB_fit_results.loc[MJD, self.columns[3:15]] = [cf_T1, cf_T1_err, cf_R1, cf_R1_err, cf_T2, cf_T2_err, cf_R2, cf_R2_err, cf_red_chi, cf_chi_sigma_dist, red_chi_1sig, cf_chi]

            if return_params:
                return cf_T1, cf_T1_err, cf_R1, cf_R1_err, cf_T2, cf_T2_err, cf_R2, cf_R2_err, cf_red_chi, cf_chi_sigma_dist, red_chi_1sig, cf_chi


        except RuntimeError:
            print(f'{Fore.RED} WARNING - Curve fit failed for MJD = {MJD} {Style.RESET_ALL}')
            self.no_failed_curvefits += 1 # counting the number of failed curve fits
            self.BB_fit_results.loc[MJD, self.columns[3:15]] = np.nan

            if return_params:
                return False, False, False, False, False, False, False, False, False, False, False, False












    def double_BB_brute(self, MJD, MJD_df, R1_sc_min, R1_sc_max, T1_min, T1_max, R2_sc_min, R2_sc_max, T2_min, T2_max, cf_chi, cf_chi_sigma_dist, cf_red_chi, cf_T1, cf_R1, cf_T2, cf_R2):
        """
        This function is built to do a coarse DBB followup on a curve_fit result. It is not built to be a full brute force DBB fit, but rather to be a followup on the curve fit result to get better uncertainties on the model parameters.
        
        INPUTS
        ---------------
        R1_sc_min, R2_sc_min: the min value of SCALED BB radius to try

        R1_sc_max, R2_sc_max: the max value of SCALED BB radius to try

        T1_min, T2_min: the min value of BB temperature to try

        T1_max, T2_min: the max value of BB temperature to try

        cf_T1, cf_R1, cf_T2, cf_R2: the values of T1, R1, T2, R2 given by curve fit. We use these to calculate the uncertainties about these parameters in the brute grid. This is to allow for assymetric uncertainties on the parameters. 
                                    We do not take the model parameter values from the brute grid because if the curvefit uncertainty happens to be very large, then the brute grid would have very large spacing between trialled parameter values. 
                                    This would be too coarse of a grid to take optimal paremters from (although I guess you're exploring a grid within +/- 2 sigma of the curve_fit params, so according to curve fit most fits within this region should be reaosnable). 

        UVOT_guided_params: (list) if you are using a UVOT guided fitting process, this is the list of UVOT-constrained parameter space to take the model params from. 
                    Input these guided parameters in the order: R1_sc_min, R1_sc_max, T1_min, T1_max, R2_sc_min, R2_sc_max, T2_min, T2_max. 
                    You must explore the entire parameter space still to ensure that you fully capture the delta_chi = 2.3 region in parameter space to ensure that
                    you know the largest and smallest parameter values which fall within this region to get the correct model parameter uncertainties. We use
                    the UVOT guided parameters to restrict the region of parameter space that we allow the final model parameters to be chosen from. 
        """
        MJD_d_since_peak = MJD_df['d_since_peak'].iloc[0]
        MJD_bands = list(MJD_df['band'].unique())
        MJD_no_bands = len( MJD_bands ) # the number of bands (and therefore datapoints) we have available at this MJD for the BB fit
        MJD_em_cent_wls = list(MJD_df['em_cent_wl'].unique())

        # creating the values of R and T that we will try
        # the number of R and T values to trial in the grid. The combinations of R and T form a 2D grid, so the number of R and T values that we try give the side lengths of the grid
        sc_R1_values = np.logspace(np.log10(R1_sc_min), np.log10(R1_sc_max), self.DBB_brute_gridsize)
        T1_values = np.logspace(np.log10(T1_min), np.log10(T1_max), self.DBB_brute_gridsize)

        sc_R2_values = np.logspace(np.log10(R2_sc_min), np.log10(R2_sc_max), self.DBB_brute_gridsize)
        T2_values = np.logspace(np.log10(T2_min), np.log10(T2_max), self.DBB_brute_gridsize)

        wavelengths = MJD_df['em_cent_wl_cm'].to_numpy() # the emitted central wavelengths of the bands present at this MJD value
        L_rfs = MJD_df['L_rf_scaled'].to_numpy() # the scaled rest frame luminosities of the bands present at this MJD value
        L_rfs = L_rfs[:, np.newaxis, np.newaxis, np.newaxis, np.newaxis]
        L_rf_errs = MJD_df['L_rf_err_scaled'].to_numpy() # the scaled rest frame luminosity errors of the bands present at this MJD value
        L_rf_errs = L_rf_errs[:, np.newaxis, np.newaxis, np.newaxis, np.newaxis]

        # create a 5D array of the blackbody luminosities for each combination of R and T. This is done by broadcasting the 1D arrays of wavelengths, R values and T values
        # the 5D array will have dimensions (len(wavelengths), len(R_values), len(T_values)) and will contain the blackbody luminosities for each combination of R and T for each wavelength value
        DBB_L_sc = vectorised_double_blackbody(wavelengths, R1 = sc_R1_values, T1 = T1_values, R2 = sc_R2_values, T2 = T2_values) # the calculated value of scaled rest frame luminosity using each combination of T1, sc_R1, T2, sc_R2 for each wavelength. shape = (len(wavelengths), len(sc_R1_values), len(T1_values), len(sc_R2_values), len(T2_values))
        
        # calculate the chi squared grid
        chi = np.sum((L_rfs - DBB_L_sc)**2 / L_rf_errs**2, axis = 0) # the chi squared grid, shape = (len(sc_R1_values), len(T1_values), len(sc_R2_values), len(T2_values))

        R1_sc_grid, T1_grid, R2_sc_grid, T2_grid = np.meshgrid(sc_R1_values, T1_values, sc_R2_values, T2_values, indexing='ij') # I just renamed these

        unmasked_chi = chi # save for the error print message
        mask = chi <= (cf_chi + self.brute_delchi)
        chi = chi[mask]
        chi_flat = chi.flatten()
        if len(chi_flat) == 0:
            print()
            print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 2.3 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
            print()
            mask = unmasked_chi <= (cf_chi + 5.0)
            chi = unmasked_chi[mask]
            chi_flat = chi.flatten()
            # if we don't have any values within the delchi = 2.3, just save the actual curve_fit params and go with that
            sampled_row_dict = {'d_since_peak': MJD_d_since_peak, 
                                'no_bands': MJD_no_bands, 
                                'bands': MJD_bands, 
                                'em_cent_wls': MJD_em_cent_wls, 
                                'cf_red_chi': cf_red_chi, #brute_red_chi, 
                                'cf_chi_sigma_dist': cf_chi_sigma_dist, #brute_chi_sigma_dist, 
                                'cf_chi': cf_chi, #min_chi, 
                                'sampled_T1_K': cf_T1, 
                                'sampled_R1_cm': cf_R1, 
                                'sampled_T2_K': cf_T2, 
                                'sampled_R2_cm': cf_R2, 
                                'sampled_chi': cf_chi}

            new_index = pd.MultiIndex.from_tuples([(MJD, self.error_sampling_size)], names = ['MJD', 'sample'])
            new_row = pd.DataFrame(index = new_index, columns = list(sampled_row_dict.keys()))
            new_row.loc[(MJD, self.error_sampling_size), sampled_row_dict.keys()] = pd.Series(sampled_row_dict) # if we don't have any values within the delchi = 2.3, just save the actual curve_fit params and go with that
            self.BB_fit_samples = pd.concat([self.BB_fit_samples, new_row], axis = 0)
            self.BB_fit_samples = self.BB_fit_samples.sort_index() # sort the index so that the MJD and sample columns are in order
            
            #self.BB_fit_samples.loc[(MJD, self.error_sampling_size)] = pd.Series(sampled_row_dict) # if we don't have any values within the delchi = 2.3, just save the actual curve_fit params and go with that
            #self.BB_fit_samples.loc[(MJD, self.error_sampling_size), sampled_row_dict.keys()] = pd.Series(sampled_row_dict)

            if len(chi_flat) == 0:
                print()
                print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 5 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
                print()
                mask = unmasked_chi <= (cf_chi + 10.0)
                chi = unmasked_chi[mask]
                chi_flat = chi.flatten()

                if len(chi_flat) == 0:
                    print()
                    print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 10.0 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
                    print()
                    mask = unmasked_chi <= (cf_chi + 20.0)
                    chi = unmasked_chi[mask]
                    chi_flat = chi.flatten()

                    if len(chi_flat) == 0:
                        print()
                        print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 20.0 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
                        print()
                        mask = unmasked_chi <= (cf_chi + 50.0)
                        chi = unmasked_chi[mask]
                        chi_flat = chi.flatten()

                        if len(chi_flat) == 0:
                            print()
                            print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 50.0 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
                            print()
                            mask = unmasked_chi <= (cf_chi + 100.0)
                            chi = unmasked_chi[mask]
                            chi_flat = chi.flatten()

                            if len(chi_flat) == 0:
                                print()
                                print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 100.0 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
                                print()
                                mask = unmasked_chi <= (cf_chi + 200.0)
                                chi = unmasked_chi[mask]
                                chi_flat = chi.flatten()

                                if len(chi_flat) == 0:
                                    print()
                                    print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 200.0 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
                                    print()
                                    mask = unmasked_chi <= (cf_chi + 500.0)
                                    chi = unmasked_chi[mask]
                                    chi_flat = chi.flatten()


        R1_sc_grid = R1_sc_grid[mask]
        T1_grid = T1_grid[mask]
        R2_sc_grid = R2_sc_grid[mask]
        T2_grid = T2_grid[mask]


        
        if len(chi_flat) == 0:
            print()
            print(f'{Fore.RED} WARNING - No chi values within the delta_chi = 500.0 region for MJD = {MJD}. Min delchi = {np.min(unmasked_chi) - (cf_chi)} {Style.RESET_ALL}')
            print()
        R1_sc_flat = R1_sc_grid.flatten()
        T1_flat = T1_grid.flatten()
        R2_sc_flat = R2_sc_grid.flatten()
        T2_flat = T2_grid.flatten()
        
        weights = 1/chi_flat
        weights /= np.sum(weights)

        sampled_indicies = np.random.choice(len(weights), size = self.error_sampling_size, p = weights, replace = True) # sample parameter combinations from the chi grid, where the probability is proportional to 1/chi
        
        sampled_R1 = R1_sc_flat[sampled_indicies] / self.R_scalefactor
        sampled_T1 = T1_flat[sampled_indicies]
        sampled_R2 = R2_sc_flat[sampled_indicies] / self.R_scalefactor
        sampled_T2 = T2_flat[sampled_indicies]
        sampled_chi = chi_flat[sampled_indicies]




        # add the sampled parameters to the sampled dataframe
        #                            0               1         2            3              4                     5                6              7              8               9                 10              11            
        #self.sampled_columns = ['d_since_peak', 'no_bands', 'bands', 'em_cent_wls', 'brute_red_chi', 'brute_chi_sigma_dist', 'brute_chi', 'sampled_T1_K', 'sampled_R1_cm', 'sampled_T2_K', 'sampled_R2_cm', 'sampled_chi] 

        for i in range(self.error_sampling_size):
            sampled_row_dict = {'d_since_peak': MJD_d_since_peak, 
                                'no_bands': MJD_no_bands, 
                                'bands': MJD_bands, 
                                'em_cent_wls': MJD_em_cent_wls, 
                                'cf_red_chi': cf_red_chi, #brute_red_chi, 
                                'cf_chi_sigma_dist': cf_chi_sigma_dist, #brute_chi_sigma_dist, 
                                'cf_chi': cf_chi, #min_chi, 
                                'sampled_T1_K': sampled_T1[i], 
                                'sampled_R1_cm': sampled_R1[i], 
                                'sampled_T2_K': sampled_T2[i], 
                                'sampled_R2_cm': sampled_R2[i], 
                                'sampled_chi': sampled_chi[i]}


            #for key, value in sampled_row_dict.items():
            #    self.BB_fit_samples.at[(MJD, i), key] = value
            self.BB_fit_samples.loc[(MJD, i), sampled_row_dict.keys()] = list(sampled_row_dict.values()) # add the sampled params to the dataframe
            #self.BB_fit_samples.loc[(MJD, i)] = pd.Series(sampled_row_dict.values()) # add the sampled params to the dataframe
            #self.BB_fit_samples.loc[(MJD, i), list(sampled_row_dict.keys())] = list(sampled_row_dict.values()) # add the sampled params to the dataframe







    def double_BB_curvefit_then_brute(self, MJD, MJD_df, R1_sc_min, R1_sc_max, T1_min, T1_max, R2_sc_min, R2_sc_max, T2_min, T2_max):
        """
        This functio does DBB fitting using curve_fit, then does a coarse grid search around the curve_fit optimal parameter values to obtain more accurate 
        (ans potentially assymetric) uncertainties. It also saves a dataframe alongside the SED fit resulst with sampled SED parameters from within the 
        uncertainties calculated by the coarse gridding. 

        INPUTS
        -------------------
        The exact same inputs as you'd give to double_BB_curvefit
        """
        
        # run the curve_fit, then we will use the results to set the bounds of the brute force fit (provided that these bounds don't go beyond the UVOT guided ones)

        # when doing the UVOT guided fitting with this function, we don't need UVOT_guided_params because curve_fits bounds are just set to the UVOT guided params and it 
        # gives out your param value bounded within your given regions, as well as its uncertainty (although a symmetric uncertainty)
        cf_T1, cf_T1_err, cf_R1, cf_R1_err, cf_T2, cf_T2_err, cf_R2, cf_R2_err, cf_red_chi, cf_chi_sigma_dist, red_chi_1sig, cf_chi = self.double_BB_curvefit(MJD = MJD, MJD_df = MJD_df, R1_sc_min = R1_sc_min, R1_sc_max = R1_sc_max, T1_min = T1_min, T1_max = T1_max, 
                                                                                                                                                                R2_sc_min = R2_sc_min, R2_sc_max = R2_sc_max, T2_min = T2_min, T2_max = T2_max, return_params = True)
        
        if cf_T1 is not False: # if the curve_fit was successful
            # set the limits for the brute force coarse grid


            # we will do a brute DBB coarse grid within +/-2 sigma of the curve fit params, exploreing ALL of this space (coarsely) so that we get accurate uncertainties, since the uncertainties on the UVOT-guided 
            # model params are allowed to exceed the UVOT-guided parameter space, as long as the model parameter itself does not exceed the UVOT guided region.
            # So, we do not want the calculation of the uncertainties to be limited by the curve_fit limits, we just want the actual model parameters to be within these limits
            # Therefore, we just limit the region over which we can take our sampled parameter values (from within the delchi = 2.3 region) to ensure that we do not sample values
            # outside of the curve_fit limits. 

            def param_lims(param, param_err, param_lim_lower, param_lim_upper, scalefactor = 1):
                param_min = (param - 1*param_err) * scalefactor
                param_max = (param + 1*param_err) * scalefactor

                if param_min < param_lim_lower:
                    param_min = param_lim_lower

                if param_max > param_lim_upper:
                    param_max = param_lim_upper

                if param_min <0:
                    param_min = 1

                return param_min, param_max

            brute_R1_sc_min, brute_R1_sc_max = param_lims(param = cf_R1, param_err = cf_R1_err, param_lim_lower = R1_sc_min, param_lim_upper = R1_sc_max, scalefactor = self.R_scalefactor)
            brute_T1_min, brute_T1_max = param_lims(param = cf_T1, param_err = cf_T1_err, param_lim_lower = T1_min, param_lim_upper = T1_max)
            brute_R2_sc_min, brute_R2_sc_max = param_lims(param = cf_R2, param_err = cf_R2_err, param_lim_lower = R2_sc_min, param_lim_upper = R2_sc_max, scalefactor = self.R_scalefactor)
            brute_T2_min, brute_T2_max = param_lims(param = cf_T2, param_err = cf_T2_err, param_lim_lower = T2_min, param_lim_upper = T2_max)

            self.double_BB_brute(MJD = MJD, MJD_df = MJD_df, R1_sc_min = brute_R1_sc_min, R1_sc_max = brute_R1_sc_max, T1_min = brute_T1_min, T1_max = brute_T1_max,
                                    R2_sc_min = brute_R2_sc_min, R2_sc_max = brute_R2_sc_max, T2_min = brute_T2_min, T2_max = brute_T2_max, 
                                    cf_chi = cf_chi, cf_chi_sigma_dist = cf_chi_sigma_dist, cf_red_chi = cf_red_chi, 
                                    cf_T1 = cf_T1, cf_R1 = cf_R1, cf_T2 = cf_T2, cf_R2 = cf_R2) 











    def run_BB_fit(self):
        # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # iterate through each value of MJD within the dataframe and see if we have enough bands to take a BB fit to it 
        single_BB = self.SED_type == 'single_BB'
        double_BB = self.SED_type == 'double_BB'
        power_law = self.SED_type == 'power_law'


        if self.curvefit: # count the number of failed curve_fits
            self.no_failed_curvefits = 0

        for MJD in tqdm(self.mjd_values, desc = f'Progress {self.SED_type} SED fitting each MJD value', total = len(self.mjd_values), leave = False):
            MJD_df = self.interp_df[self.interp_df['MJD'] == MJD].copy() # THERE COULD BE FLOATING POINT ERRORS HERE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            MJD_d_since_peak = MJD_df['d_since_peak'].iloc[0]
            MJD_no_bands = len( MJD_df['band'].unique() ) # the number of bands (and therefore datapoints) we have available at this MJD for the BB fit
            self.BB_fit_results.loc[MJD, :] = np.nan # set all values to nan for now, then overwrite them if we have data for thsi column, so that if (e.g.) brute = False, then the brute columns would contain nan values
            self.BB_fit_results.loc[MJD, self.columns[0:3]] = [MJD, MJD_d_since_peak, MJD_no_bands] # the first column in the dataframe is MJD, so set the first value in the row as the MJD
            self.BB_fit_results.at[MJD, 'bands'] = list(MJD_df['band'].unique())
            self.BB_fit_results.at[MJD, 'em_cent_wls'] = list(MJD_df['em_cent_wl'].unique())

            if MJD_no_bands <= 1: # don't try fitting a BB spectrum to a single datapoint, so the BB results in this row will all be nan
                continue
            
            #for a single BB fit
            if single_BB:
                if self.curvefit:
                    self.BB_curvefit(MJD, MJD_df, R_sc_min = self.BB_R_min_sc, R_sc_max = self.BB_R_max_sc, T_min = self.BB_T_min, T_max = self.BB_T_max)

                if self.brute:
                    self.BB_brute(MJD, MJD_df, R_sc_min = self.BB_R_min_sc, R_sc_max = self.BB_R_max_sc, T_min = self.BB_T_min, T_max = self.BB_T_max)

            # for a double BB fit
            elif double_BB:
                if MJD_no_bands < 4: # don't try fitting a DBB spectrum to <c4 datapoints, so the BB results in this row will all be nan
                    continue

                if self.curvefit:
                    self.double_BB_curvefit(MJD, MJD_df, 
                                            R1_sc_min = self.DBB_R_min_sc, R1_sc_max = self.DBB_R_max_sc, T1_min = self.DBB_T1_min, T1_max = self.DBB_T1_max, 
                                            R2_sc_min = self.DBB_R_min_sc, R2_sc_max = self.DBB_R_max_sc, T2_min = self.DBB_T2_min, T2_max = self.DBB_T2_max)

            elif power_law:
                if self.curvefit:
                    self.power_law_curvefit(MJD, MJD_df, A_sc_min = self.PL_sc_A_min, A_sc_max = self.PL_sc_A_max, gamma_min = self.PL_gamma_min, gamma_max = self.PL_gamma_max)

                if self.brute:
                    self.power_law_brute(MJD, MJD_df, A_min = self.PL_A_min, A_max = self.PL_A_max, gamma_min = self.PL_gamma_min, gamma_max = self.PL_gamma_max)


        # print a message to indicate that the fitting was successful
        if self.curvefit:
            print(f'{Fore.GREEN}SED fitting complete for {self.ant_name})  (# curve_fits failed = {self.no_failed_curvefits}) ============================================================================================= {Style.RESET_ALL}')
            print()

        else: 
            print(f'{Fore.GREEN}SED fitting complete for {self.ant_name})   ============================================================================================= {Style.RESET_ALL}')
            print()

        return self.BB_fit_results
    



    



    def run_SED_fitting_process(self, band_colour_dict, band_marker_dict):
        """
        * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        A FUNCTION WHICH YOU MIGHT DIRECTLY CALL WHEN INITIALISING THE CLASS
        * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 

        This SED fitting process fits the chosen SED to each MJD's data, independently of the SED fits nearby. 

        INPUTS:
        -------------
        band_colour_dict: (dict)  a dictionary where the keys are the band names and the values are the colours to use when plotting them

        band_marker_dict: (dict) a dictionary where the keys are the band names and the values are the markers to use when plotting them

        OUTPUTS:
        -------------

        SED_fit_results: (pd.DataFrame) A dataframe containing the SED fit results at each epoch in the light curve provided. 
        
        """
        self.guided_UVOT_SED_fits = False 
        SED_fit_results = self.run_BB_fit() # iterate through the MJDs and fit our chosen SED to them
        self.get_individual_BB_fit_MJDs() # if we want to plot the individual SEDs, get the MJDs at which we will plot their SEDs
        
        # plot the individual SEDs:
        if self.SED_type == 'single_BB': # only plots if the individual_fit_MJDs is not None, so this should be find even if you dont want the individual BB fits plot
            self.plot_individual_BB_fits(band_colour_dict, band_marker_dict)

        elif self.SED_type == 'double_BB':
            self.plot_individual_double_BB_fits(band_colour_dict, band_marker_dict)

        elif self.SED_type == 'power_law':
            self.plot_individual_power_law_SED_fits(band_colour_dict, band_marker_dict)

        # plot the SED params vs time to make sure its behaving well
        self.plot_SED_params_vs_time(band_colour_dict=band_colour_dict)


        self.save_SED_fit_results(guided = self.guided_UVOT_SED_fits) # save the dataframe of the SED fitting results

        return SED_fit_results





    ###################################################################################################################################################################################
    ###################################################################################################################################################################################

    # STILL FITTING STUFF, BUT HERE WE'RE WRITING CODE TO USE NEARBY UVOT MJD SED FITS TO GUIDE THE FITS OF NEARBY MJDS WITHOUT UVOT ##################################################

    ###################################################################################################################################################################################
    ###################################################################################################################################################################################

    
    


    def get_UVOT_MJDs_and_SED_fit_them(self, sigma_dist_for_good_fit):
        """
        This function takes the MJDs from interp_df which have UVOT data (if any) and fits the SED model to them. 
        We don't return anything from this function since we're just updating BB_fit_results with the results of the UVOT MJD SED fits, but any MJDs without
        UVOT data are yet to be fit. Only necessary for the ANTs with UVOT data at the start so ZTF19aailpwl, ZTF20acvfraq, ZTF22aadesap

        INPUTS
        -------------
        sigma_dist_for_good_fit: (float) the maximum reduced chi squared sigma distance for which we will consider the fit 'good', so all fits with chi_sig_dist <= sigma_dist_for_good_fit
        is considered a good fit.  

        """
        
        UV_wavelength_threshold = 3000 # angstrom
        bin_by_MJD = self.interp_df.groupby('MJD', observed = True).apply(lambda g: pd.Series({'UVOT?': (g['em_cent_wl']< UV_wavelength_threshold).any() })).reset_index()

        self.all_UVOT_MJDs = bin_by_MJD[bin_by_MJD['UVOT?'] == True]['MJD'].to_numpy() # an array of the MJDs at which we have UVOT data
        self.optical_MJDs = bin_by_MJD[bin_by_MJD['UVOT?'] == False]['MJD'].to_numpy() # used in the next function where we SED fit the non-UVOT MJDs

        if (self.SED_type == 'double_BB') and (self.curvefit):
            self.no_failed_curvefits = 0

        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # adding new columns to the results dataframe to show the upper and lower parameter space limits that the fit was allowed to explore
        if self.SED_type == 'single_BB':
            #self.curvefit = False # set this to false to prevent any curve-fit related code starting up, since we don't specify a fitting method here as we always choose brute force over curve fit
            self.BB_fit_results = self.BB_fit_results.reindex(columns = list(self.BB_fit_results.columns) + ['R_param_lower_lim', 'R_param_upper_lim', 'T_param_lower_lim', 'T_param_upper_lim'])


        elif self.SED_type == 'double_BB':
            #self.curvefit = True # set this to True to allow any curve-fit related code starting up, since we don't specify a fitting method here as we always choose brute force over curve fit
            self.BB_fit_results = self.BB_fit_results.reindex(columns = list(self.BB_fit_results.columns) + ['R1_param_lower_lim', 'R1_param_upper_lim', 'T1_param_lower_lim', 'T1_param_upper_lim', 'R2_param_lower_lim', 'R2_param_upper_lim', 'T2_param_lower_lim', 'T2_param_upper_lim'])


        elif self.SED_type == 'power_law':
            #self.curvefit = False # set this to false to prevent any curve-fit related code starting up, since we don't specify a fitting method here as we always choose brute force over curve fit
            self.BB_fit_results = self.BB_fit_results.reindex(columns = list(self.BB_fit_results.columns) + ['A_param_lower_lim', 'A_param_upper_lim', 'gamma_param_lower_lim', 'gamma_param_upper_lim'])



        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # SED fitting the UVOT MJDs
        for UV_MJD in tqdm(self.all_UVOT_MJDs, desc = 'Progress SED fitting each UVOT MJD value', total = len(self.all_UVOT_MJDs), leave = False):
            MJD_df = self.interp_df[self.interp_df['MJD'] == UV_MJD].copy() # THERE COULD BE FLOATING POINT ERRORS HERE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            MJD_d_since_peak = MJD_df['d_since_peak'].iloc[0]
            MJD_no_bands = len( MJD_df['band'].unique() ) # the number of bands (and therefore datapoints) we have available at this MJD for the BB fit
            self.BB_fit_results.loc[UV_MJD, :] = np.nan # set all values to nan for now, then overwrite them if we have data for thsi column, so that if (e.g.) brute = False, then the brute columns would contain nan values
            self.BB_fit_results.loc[UV_MJD, self.columns[0:3]] = [UV_MJD, MJD_d_since_peak, MJD_no_bands] # the first column in the dataframe is MJD, so set the first value in the row as the MJD
            self.BB_fit_results.at[UV_MJD, 'bands'] = list(MJD_df['band'].unique())
            self.BB_fit_results.at[UV_MJD, 'em_cent_wls'] = list(MJD_df['em_cent_wl'].unique())

            if MJD_no_bands <=1:
                continue

            #for a single BB fit
            if self.SED_type == 'single_BB':
                #if self.curvefit:
                #    self.BB_curvefit(UV_MJD, MJD_df, R_sc_min = self.BB_R_min_sc, R_sc_max = self.BB_R_max_sc, T_min = self.BB_T_min, T_max = self.BB_T_max)
                #if self.brute:
                self.BB_fit_results.loc[UV_MJD, ['R_param_lower_lim', 'R_param_upper_lim', 'T_param_lower_lim', 'T_param_upper_lim']] = [self.BB_R_min, self.BB_R_max, self.BB_T_min, self.BB_T_max]
                self.BB_brute(UV_MJD, MJD_df, R_sc_min = self.BB_R_min_sc, R_sc_max = self.BB_R_max_sc, T_min = self.BB_T_min, T_max = self.BB_T_max)
                note = 'brute'

            # for a double BB fit
            elif self.SED_type == 'double_BB': # WE CURRENTLY DON'T HAVE A FUNCTION TO BRUTE FORCE A DOUBLE BLACKBODY SO MUST USE CURVE FIT
                if MJD_no_bands <4: # don't fit a DBB to <4 data points since M=4
                    continue

                self.BB_fit_results.loc[UV_MJD, ['R1_param_lower_lim', 'R1_param_upper_lim', 'T1_param_lower_lim', 'T1_param_upper_lim', 'R2_param_lower_lim', 'R2_param_upper_lim', 'T2_param_lower_lim', 'T2_param_upper_lim']] = [self.DBB_R_min, self.DBB_R_max, self.DBB_T1_min, self.DBB_T1_max, self.DBB_R_min, self.DBB_R_max, self.DBB_T2_min, self.DBB_T2_max]
                self.double_BB_curvefit_then_brute(UV_MJD, MJD_df, R1_sc_min = self.DBB_R_min_sc, R1_sc_max = self.DBB_R_max_sc, T1_min = self.DBB_T1_min, T1_max = self.DBB_T1_max, R2_sc_min = self.DBB_R_min_sc, R2_sc_max = self.DBB_R_max_sc, T2_min = self.DBB_T2_min, T2_max = self.DBB_T2_max)
                #self.double_BB_curvefit(UV_MJD, MJD_df, R1_sc_min = self.DBB_R_min_sc, R1_sc_max = self.DBB_R_max_sc, T1_min = self.DBB_T1_min, T1_max = self.DBB_T1_max, R2_sc_min = self.DBB_R_min_sc, R2_sc_max = self.DBB_R_max_sc, T2_min = self.DBB_T2_min, T2_max = self.DBB_T2_max)
                note = 'cf'

            # for a power law fit
            elif self.SED_type == 'power_law':
                #if self.curvefit:
                #    self.power_law_curvefit(UV_MJD, MJD_df, A_sc_min = self.PL_sc_A_min, A_sc_max = self.PL_sc_A_max, gamma_min = self.PL_gamma_min, gamma_max = self.PL_gamma_max)
                #if self.brute:
                self.BB_fit_results.loc[UV_MJD, ['A_param_lower_lim', 'A_param_upper_lim', 'gamma_param_lower_lim', 'gamma_param_upper_lim']] = [self.PL_A_min, self.PL_A_max, self.PL_gamma_min, self.PL_gamma_max]
                self.power_law_brute(UV_MJD, MJD_df, A_min = self.PL_A_min, A_max = self.PL_A_max, gamma_min = self.PL_gamma_min, gamma_max = self.PL_gamma_max)
                note = 'brute'

        # print a message to indicate that the fitting was successful
        if self.SED_type == 'double_BB': # since double BB is the only SED fit using curvefit anyways
            print(f'{Fore.GREEN}UVOT SED fitting complete for {self.ant_name})  (# curve_fits failed = {self.no_failed_curvefits}) ============================================================================================= {Style.RESET_ALL}')
            print()

        else:
            print(f'{Fore.GREEN}UVOT SED fitting complete for {self.ant_name}   ============================================================================================= {Style.RESET_ALL}')
            print()

        note = 'cf' if self.SED_type == 'double_BB' else 'brute' # bug fix for PS1-10adi's SBB for some reason
        UVOT_SEDs_with_good_SED_fits = self.BB_fit_results[self.BB_fit_results['MJD'].isin(self.all_UVOT_MJDs)].copy() # filter SED_fit_results for the UVOT fit results
        UVOT_SEDs_with_good_SED_fits = UVOT_SEDs_with_good_SED_fits[UVOT_SEDs_with_good_SED_fits[f'{note}_chi_sigma_dist'] <= sigma_dist_for_good_fit].copy() # find the SED results where the fit was good

        if UVOT_SEDs_with_good_SED_fits.empty: # if none of the UVOT MJDs had good SED fits, don't use their results to guide the non-UVOT fits
            self.UVOT_MJDs_with_good_SED_fits = None

        else: 
            self.UVOT_MJDs_with_good_SED_fits = UVOT_SEDs_with_good_SED_fits['MJD'].to_numpy() # an array of MJD values with UVOT data which had a good SED fit so can be used for parameter constraint

            








    @staticmethod
    def param_limit_calculation(UVOT_M, UVOT_M_err_lower, UVOT_M_err_upper, MJD_diff, err_scalefactor, normal_lower_lim, normal_upper_lim):
        """
        UVOT_M: (float) the closest UVOT MJD SED's model parameter value (just one of them, this function works on one parameter at a time, NOT like the 'one parameter at a time
        statistical error calculation', you just need to use this function once per model parameter for the SED)

        UVOT_M_err_lower: (float) the closest UVOT MJD SED's model parameter's lower error

        UVOT_M_err_upper: (float) the closest UVOT MJD SED's model parameter's upper error

        MJD_diff: (float) MJD_diff = |UVOT_MJD - MJD| where MJD is the MJD at which we're trying to fit and UVOT_MJD is the MJD of the closest MJD with UVOT data. This
        is the UVOT MJD SED which we'll be using to restrict the parameter space which is explored for MJD's fit

        err_scalefactor: (float) used like this: MJD_A_lower_lim = UVOT_A + err_scalefactor * |UVOT_MJD - MJD| * UVOT_A_err_lower and so on for all model parameters 
        where A is a model parameter. Since we want to use the SED fits of the nearby UVOT MJDs to constrain the parameter space to explore by the non-UVOT MJD SED 
        fits, we should allow the non-UVOT SEd to explore a larger area of parameter space around the UVOT SED parameters if the non-UVOT MJD is further away from the 
        UVOT one.

        normal_lower_lim: (float) the lower limit which we normally use to explore the parameter space of this model parameter, when we are fitting independently of the nearby MJDs.
        
        normal_upper_lim: (float) the upper limit which we normally use to explore the parameter space of this model parameter, when we are fitting independently of the nearby MJDs.
        """

        param_lower_lim = UVOT_M - (err_scalefactor * MJD_diff + 1) * UVOT_M_err_lower # here, we make sure we explore at least 1 sigma of parameter space, so even if MJD_diff = 0, we still have searchable param space, that's what the +1 in the bracket does
        param_upper_lim = UVOT_M + (err_scalefactor * MJD_diff + 1) * UVOT_M_err_upper

        # if the calculated limit goes beyond the limit which we usually use for fitting (this would happen if the UVOT param error was very large or |UVOT_MJD - MJD| is very large)
        # the second condition here would only occur if the UVOT SED fit was really bad and gave the model parameter a very very high value
        if (param_lower_lim <= normal_lower_lim) or (param_lower_lim >= normal_upper_lim): 
            param_lower_lim = normal_lower_lim

        
        # if the calculated limit goes beyond the limit which we usually use for fitting (this would happen if the UVOT param error was very large or |UVOT_MJD - MJD| is very large)
        # the second condition here would only occur if the UVOT SED fit was really bad and gave the model parameter a very very low value
        if (param_upper_lim >= normal_upper_lim) or (param_upper_lim <= normal_lower_lim): 
            param_upper_lim = normal_upper_lim


        if param_upper_lim <= param_lower_lim:
            param_lower_lim = normal_lower_lim
            param_upper_lim = normal_upper_lim

        return param_lower_lim, param_upper_lim





    def optical_SED_fits_guided_by_UVOT(self): 
        """
        This function follows from get_UVOT_data_and_SED_fit(). It uses the parameters obtained from the SED fits of nearby UVOT data to constrain the parameter space for fitting 
        the nearby no-UVOT MJD SEDs. 

        """
        

        for opt_MJD in tqdm(self.optical_MJDs, desc = f'Progress {self.SED_type} SED fitting each optical MJD value', total = len(self.optical_MJDs), leave = False):
            MJD_df = self.interp_df[self.interp_df['MJD'] == opt_MJD].copy() # THERE COULD BE FLOATING POINT ERRORS HERE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            MJD_d_since_peak = MJD_df['d_since_peak'].iloc[0]
            MJD_no_bands = len( MJD_df['band'].unique() ) # the number of bands (and therefore datapoints) we have available at this MJD for the BB fit
            self.BB_fit_results.loc[opt_MJD, :] = np.nan # set all values to nan for now, then overwrite them if we have data for thsi column, so that if (e.g.) brute = False, then the brute columns would contain nan values
            self.BB_fit_results.loc[opt_MJD, self.columns[0:3]] = [opt_MJD, MJD_d_since_peak, MJD_no_bands] # the first column in the dataframe is MJD, so set the first value in the row as the MJD
            self.BB_fit_results.at[opt_MJD, 'bands'] = list(MJD_df['band'].unique())
            self.BB_fit_results.at[opt_MJD, 'em_cent_wls'] = list(MJD_df['em_cent_wl'].unique())

            # find the closest UVOT datapoint
            MJD_diff = abs(opt_MJD - self.UVOT_MJDs_with_good_SED_fits)
            closest_MJD_diff_idx = np.argmin(MJD_diff)
            closest_MJD_diff = MJD_diff[closest_MJD_diff_idx]
            closest_UVOT_MJD = self.UVOT_MJDs_with_good_SED_fits[closest_MJD_diff_idx] # a flaw of this method is that if out closest UVOT SED fit was a bad fit and has large errors, we may have been betetr off using the 2nd closest UVOT MJD or something like that
            
            # dont bother fitting if we've only got one datapoint for the SED
            if MJD_no_bands <=1:
                continue

            #for a single BB fit ----------------------------------------------------------------------------------------------------------------------------
            if self.SED_type == 'single_BB':
                # get the model parameters from the closest-by UVOT SED fit to help constrain the fit here
                UVOT_T = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_T_K']
                UVOT_T_lower_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_T_err_lower_K']
                UVOT_T_upper_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_T_err_upper_K']
                UVOT_R = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_R_cm']
                UVOT_R_lower_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_R_err_lower_cm']
                UVOT_R_upper_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_R_err_upper_cm']

                # calculate the region of parameter space to explore MJD's SED fit. Below we calculate UNSCALED R limits. 
                MJD_R_min, MJD_R_max = self.param_limit_calculation(UVOT_M = UVOT_R, UVOT_M_err_lower = UVOT_R_lower_err, UVOT_M_err_upper = UVOT_R_upper_err, 
                                                                                MJD_diff = closest_MJD_diff, err_scalefactor = self.UVOT_guided_err_scalefactor, 
                                                                                normal_lower_lim = self.BB_R_min, normal_upper_lim = self.BB_R_max)
                MJD_R_sc_min = MJD_R_min * self.R_scalefactor # scale the R limits down
                MJD_R_sc_max = MJD_R_max * self.R_scalefactor

                MJD_T_min, MJD_T_max = self.param_limit_calculation(UVOT_M = UVOT_T, UVOT_M_err_lower = UVOT_T_lower_err, UVOT_M_err_upper = UVOT_T_upper_err, MJD_diff = closest_MJD_diff, 
                                                                    err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim = self.BB_T_min, normal_upper_lim = self.BB_T_max)
                
                # running the BB Brute SED fitting ---
                self.BB_fit_results.loc[opt_MJD, ['R_param_lower_lim', 'R_param_upper_lim', 'T_param_lower_lim', 'T_param_upper_lim']] = [MJD_R_min, MJD_R_max, MJD_T_min, MJD_T_max] # documenting the parameter space which we searched
                self.BB_brute(opt_MJD, MJD_df, R_sc_min = self.BB_R_min_sc, R_sc_max = self.BB_R_max_sc, T_min = self.BB_T_min, T_max = self.BB_T_max, 
                                UVOT_guided_params = [MJD_R_sc_min, MJD_R_sc_max, MJD_T_min, MJD_T_max]) 



            # for a double BB fit ----------------------------------------------------------------------------------------------------------------------------
            elif self.SED_type == 'double_BB': # WE CURRENTLY DON'T HAVE A FUNCTION TO BRUTE FORCE A DOUBLE BLACKBODY SO MUST USE CURVE FIT
                
                if MJD_no_bands <4: # dont bother fitting to <4 datapoints since M=4
                    continue


                # get the model parameters from the closest-by UVOT SED fit to help constrain the fit here
                UVOT_T1 = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_T1_K']
                UVOT_T1_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_T1_err_K']
                UVOT_R1 = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_R1_cm']
                UVOT_R1_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_R1_err_cm']

                UVOT_T2 = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_T2_K']
                UVOT_T2_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_T2_err_K']
                UVOT_R2 = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_R2_cm']
                UVOT_R2_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'cf_R2_err_cm']

                MJD_T1_min, MJD_T1_max = self.param_limit_calculation(UVOT_M = UVOT_T1, UVOT_M_err_lower = UVOT_T1_err, UVOT_M_err_upper = UVOT_T1_err, MJD_diff = closest_MJD_diff, 
                                                                        err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim=self.DBB_T1_min, normal_upper_lim = self.DBB_T1_max)
                
                MJD_T2_min, MJD_T2_max = self.param_limit_calculation(UVOT_M = UVOT_T2, UVOT_M_err_lower = UVOT_T2_err, UVOT_M_err_upper = UVOT_T2_err, MJD_diff = closest_MJD_diff, 
                                                                        err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim = self.DBB_T2_min, normal_upper_lim = self.DBB_T2_max)
                
                MJD_R1_min, MJD_R1_max = self.param_limit_calculation(UVOT_M = UVOT_R1, UVOT_M_err_lower = UVOT_R1_err, UVOT_M_err_upper = UVOT_R1_err, MJD_diff = closest_MJD_diff, 
                                                                        err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim=self.DBB_R_min, normal_upper_lim = self.DBB_R_max)
                
                MJD_R2_min, MJD_R2_max = self.param_limit_calculation(UVOT_M = UVOT_R2, UVOT_M_err_lower = UVOT_R2_err, UVOT_M_err_upper = UVOT_R2_err, MJD_diff = closest_MJD_diff, 
                                                                        err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim=self.DBB_R_min, normal_upper_lim = self.DBB_R_max)
                MJD_R1_sc_min = MJD_R1_min * self.R_scalefactor
                MJD_R1_sc_max = MJD_R1_max * self.R_scalefactor
                MJD_R2_sc_min = MJD_R2_min * self.R_scalefactor
                MJD_R2_sc_max = MJD_R2_max * self.R_scalefactor

                # running the DBB curve fit SED fitting ---
                self.BB_fit_results.loc[opt_MJD, ['R1_param_lower_lim', 'R1_param_upper_lim', 'T1_param_lower_lim', 'T1_param_upper_lim', 'R2_param_lower_lim', 'R2_param_upper_lim', 'T2_param_lower_lim', 'T2_param_upper_lim']] = [MJD_R1_min, MJD_R1_max, MJD_T1_min, MJD_T1_max, MJD_R2_min, MJD_R2_max, MJD_T2_min, MJD_T2_max] # documenting the parameter space which we searched
                #self.double_BB_curvefit(opt_MJD, MJD_df,
                #                        R1_sc_min = MJD_R1_sc_min, R1_sc_max = MJD_R1_sc_max, T1_min = MJD_T1_min, T1_max = MJD_T1_max, 
                #                        R2_sc_min = MJD_R2_sc_min, R2_sc_max = MJD_R2_sc_max, T2_min = MJD_T2_min, T2_max = MJD_T2_max)
                
                self.double_BB_curvefit_then_brute(opt_MJD, MJD_df,
                                        R1_sc_min = MJD_R1_sc_min, R1_sc_max = MJD_R1_sc_max, T1_min = MJD_T1_min, T1_max = MJD_T1_max, 
                                        R2_sc_min = MJD_R2_sc_min, R2_sc_max = MJD_R2_sc_max, T2_min = MJD_T2_min, T2_max = MJD_T2_max)



            # for a power law fit ----------------------------------------------------------------------------------------------------------------------------
            elif self.SED_type == 'power_law':
                # get the model parameters from the closest-by UVOT SED fit to help constrain the fit here
                UVOT_A = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_A']
                UVOT_A_lower_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_A_err_lower']
                UVOT_A_upper_err = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_A_err_upper']
                UVOT_gamma = self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_gamma']
                UVOT_gamma_err= self.BB_fit_results.loc[closest_UVOT_MJD, 'brute_gamma_err']

                # calculate the region of parameter space to explore MJD's SED fit
                MJD_A_min, MJD_A_max = self.param_limit_calculation(UVOT_M = UVOT_A, UVOT_M_err_lower = UVOT_A_lower_err, UVOT_M_err_upper = UVOT_A_upper_err, 
                                                                                MJD_diff = closest_MJD_diff, err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim = self.PL_A_min, normal_upper_lim = self.PL_A_max)

                MJD_gamma_min, MJD_gamma_max = self.param_limit_calculation(UVOT_M = UVOT_gamma, UVOT_M_err_lower = UVOT_gamma_err, UVOT_M_err_upper = UVOT_gamma_err, MJD_diff = closest_MJD_diff, 
                                                                            err_scalefactor = self.UVOT_guided_err_scalefactor, normal_lower_lim = self.PL_gamma_min, normal_upper_lim = self.PL_gamma_max)
                
                # running the PL brute SED fitting ---
                self.BB_fit_results.loc[opt_MJD, ['A_param_lower_lim', 'A_param_upper_lim', 'gamma_param_lower_lim', 'gamma_param_upper_lim']] = [MJD_A_min, MJD_A_max, MJD_gamma_min, MJD_gamma_max] # documenting the parameter space which we searched
                self.power_law_brute(opt_MJD, MJD_df, A_min = self.PL_A_min, A_max = self.PL_A_max, gamma_min = self.PL_gamma_min, gamma_max = self.PL_gamma_max, 
                                        UVOT_guided_params = [MJD_A_min, MJD_A_max, MJD_gamma_min, MJD_gamma_max])



        # print a message to indicate that the fitting was successful
        if self.curvefit:
            print(f'{Fore.GREEN}Optical SED fitting complete for {self.ant_name}  (# curve_fits failed = {self.no_failed_curvefits}) ============================================================================================= {Style.RESET_ALL}')
            print()

        else:
            print(f'{Fore.GREEN}Optical SED fitting complete for {self.ant_name}   ============================================================================================= {Style.RESET_ALL}')
            print()

        return self.BB_fit_results




    
    def run_UVOT_guided_SED_fitting_process(self, err_scalefactor, sigma_dist_for_good_fit, band_colour_dict, band_marker_dict):
        """
        * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
        A FUNCTION WHICH YOU WOULD DIRECTLY CALL WHEN INITIALISING THE CLASS
        * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 

        This SED fitting process uses a guided fitting method. This means that if we have UVOT data on the rise/peak of the light curve, we SED fit these
        first, then use these results to constrain the parameter space over which we test for nearby MJD SED fits which do not have UVOT data. This only applies for
        lightcurves with UVOT data, which are:  'ZTF19aailpwl', 'ZTF20acvfraq', 'ZTF22aadesap', 'ASASSN-17jz', 'ASASSN-18jd'
        If the ANT you're trying to SED fit does not have UVOT data on the rise/peak, it will use a non-guided SED fitting process, in which
        each MJD's SED fit is done independently of the ones around it. 

        INPUTS
        ---------------
        err_scalefactor: (float) used like this: MJD_A_lower_lim = UV_A + err_scalefactor * |UV_MJD - MJD| * UV_A_err_lower and so on for all model parameters 
        where A is a model parameter. Since we want to use the SED fits of the nearby UVOT MJDs to constrain the parameter space to explore by the non-UVOT MJD SED 
        fits, we should allow the non-UVOT SED to explore a larger area of parameter space around the UVOT SED parameters if the non-UVOT MJD is further away from the 
        UVOT one.

        sigma_dist_for_good_fit: (float) the maximum reduced chi squared sigma distance for which we will consider the fit 'good', so all fits with chi_sig_dist <= sigma_dist_for_good_fit
        is considered a good fit. I use 3 in my dissertation. 

        band_colour_dict: (dict) where the keys are the band names and the values are the colours to use when plotting them (can be found in plotting_preferences)

        band_marker_dict: (dict) where the keys are the band names and the values are the markers to use when plotting them (can be found in plotting_preferences)

        OUTPUTS
        --------------
        SED_fit_results: (DataFrame) containing the SED fit results at each MJD. 

        """
        self.UVOT_guided_err_scalefactor = err_scalefactor
        if self.ant_name in ['ZTF19aailpwl', 'ZTF20acvfraq', 'ZTF22aadesap', 'ASASSN-17jz', 'ASASSN-18jd']: # these are the ANTs with UVOT on the rise/peak so can use it to constrain non-UVOT SED fit parameter space
            self.guided_UVOT_SED_fits = True # I will use this to add details to the subplots of individual SEDs like adding in our calculated explorable parameter space 

            if self.SED_type == 'single_BB': # setting these straight so we don't get any unexpected code trying to run
                self.curvefit = False
            elif self.SED_type == 'double_BB':
                self.curvefit = True
            elif self.SED_type == 'power_law':
                self.curvefit = False

            # fit SEDs to the MJDs with UVOT data, if any of these fits are considered good, we can use them to constrain the param space of the non-UVOT fits. 
            self.get_UVOT_MJDs_and_SED_fit_them(sigma_dist_for_good_fit = sigma_dist_for_good_fit)

            
            if self.UVOT_MJDs_with_good_SED_fits is not None: # if we have UVOT MJDs which had 'good fitting' SED fits, we will use them to constrain the non-UVOT fits
                SED_fit_results = self.optical_SED_fits_guided_by_UVOT()
                self.get_individual_BB_fit_MJDs() # if we want to plot the individual SEDs, get the MJDs at which we will plot their SEDs
            else:
                # MAYBE I SHOULD SET THE self.guided_UVOT_SED_fits = FALSE???????????????????????
                print()
                print(f'{Fore.RED}WARNING - THERE WERE NO UVOT MJD SED FITS WITH SIG DIST <= {sigma_dist_for_good_fit}. \nTHERE WILL BE NO UVOT GUIDED SED FITTING - ALL SED FITS WILL BE DONE INDEPENDENTLY OF ONE ANOTHER{Style.RESET_ALL}')
                print()
                print('Running the regular (non-guided) fitting process on the entire light curve')
                SED_fit_results = self.run_BB_fit() # iterate through the MJDs and fit our chosen SED to them
                self.get_individual_BB_fit_MJDs() # if we want to plot the individual SEDs, get the MJDs at which we will plot their SEDs



        else: 
            SED_fit_results = self.run_BB_fit() # iterate through the MJDs and fit our chosen SED to them
            self.get_individual_BB_fit_MJDs() # if we want to plot the individual SEDs, get the MJDs at which we will plot their SEDs
            


        # plot the individual SEDs:
        if self.SED_type == 'single_BB': # only plots if the individual_fit_MJDs is not None, so this should be find even if you dont want the individual BB fits plot
            self.plot_individual_BB_fits(band_colour_dict, band_marker_dict)

        elif self.SED_type == 'double_BB':
            self.plot_individual_double_BB_fits(band_colour_dict, band_marker_dict)

        elif self.SED_type == 'power_law':
            self.plot_individual_power_law_SED_fits(band_colour_dict, band_marker_dict)


        # plot the SED params vs time to make sure its behaving well
        self.plot_SED_params_vs_time(band_colour_dict=band_colour_dict)


        self.save_SED_fit_results(guided = self.guided_UVOT_SED_fits) # save the dataframe of SED fitting results

        return SED_fit_results








    ###################################################################################################################################################################################
    ###################################################################################################################################################################################

    # PLOTTING INDIVIDUAL SED FITS ####################################################################################################################################################

    ###################################################################################################################################################################################
    ###################################################################################################################################################################################








    def get_individual_BB_fit_MJDs(self):
        """
        This function will find the MJD values at which we will plot the individual BB fits. We will plot the BB fits at these MJD values in a grid of (no_MJD) number of plots, 
        with the BB fit and the chi squared parameter space grid

        if you choose self.individual_BB_plot == 'UVOT', and, for example self.no_indiv_plots == 12 and there are < 12 MJDS with UVOT data, the code will plot some non-UVOT SEDs too

        """
        if (self.SED_type == 'single_BB') or (self.SED_type == 'power_law'): # dont plot an MJD which had no SED fit taken to it because N<M
            min_bands = 2

        elif self.SED_type == 'double_BB':
            min_bands = 4
        
        BB_MJDs = self.BB_fit_results[self.BB_fit_results['no_bands'] >= min_bands].index # the MJD values at which we have more than 1 band present, so we can fit a BB to the data
        if self.individual_BB_plot == 'UVOT':
            UVOT_df = self.interp_df[self.interp_df['band'].isin(['UVOT_U', 'UVOT_B', 'UVOT_V', 'UVOT_UVM2', 'UVOT_UVW1', 'UVOT_UVW2'])].copy()
            UVOT_MJDs = UVOT_df['MJD'].unique()
            if (len(UVOT_MJDs) == 0.0): # if we have no UVOT data, just get MJDs from the whole light curve
                self.indiv_plot_MJDs = BB_MJDs[::int(len(BB_MJDs)/self.no_indiv_SED_plots)] # plot every 12th MJD value
                self.indiv_plot_MJDs = self.indiv_plot_MJDs[:self.no_indiv_SED_plots] # only plot the first 12 values, in case the line above finds 13
                return
            
            step = max(1, int(len(UVOT_MJDs)/self.no_indiv_SED_plots)) # make sure we don't get a step of 0
            self.indiv_plot_MJDs = UVOT_MJDs[::step] # plot every 12th MJD value
            self.indiv_plot_MJDs = self.indiv_plot_MJDs[:self.no_indiv_SED_plots] # only plot the first 12 values, in case the line above finds 13
            len_UVOT_mjd_choice = len(self.indiv_plot_MJDs)

            if len_UVOT_mjd_choice < self.no_indiv_SED_plots: # if we want to plot the UVOT data but there are less than 12 instances of UVOT data, add some regular MJDs to the plot too
                no_missing = self.no_indiv_SED_plots - len_UVOT_mjd_choice
                add_MJDs = BB_MJDs[::int(len(BB_MJDs)/no_missing)]
                add_MJDs = add_MJDs[:no_missing]
                self.indiv_plot_MJDs = np.concatenate((self.indiv_plot_MJDs, add_MJDs))


        elif self.individual_BB_plot == 'whole_lc':
            step = step = max(1, int(len(BB_MJDs) / self.no_indiv_SED_plots)) # make sure we don't get a step of 0
            self.indiv_plot_MJDs = BB_MJDs[::step] # plot every 12th MJD value
            self.indiv_plot_MJDs = self.indiv_plot_MJDs[:self.no_indiv_SED_plots] # only plot the first 12 values, in case the line above finds 13
            

        else:
            self.indiv_plot_MJDs = None





    @staticmethod
    def get_indiv_SED_plot_rows_cols(no_SEDs):
        """
        (Gets called within plot_individual_BB_fits() and plot_individual_double_BB_fits() )
        This function takes in the number of individual SEDs you want to plot in a single plot and gives the number of rows and columns needed to allow for this. 
        """
        if no_SEDs == 24:
            nrows, ncols = (4, 6)

        elif no_SEDs == 20:
            nrows, ncols = (4, 5)

        elif no_SEDs == 12:
            nrows, ncols = (4, 3)

        return nrows, ncols


    @staticmethod
    def format_sci_with_uncertainty(value, upper, lower):
        """
        Formats a number in scientific notation with asymmetric uncertainties,
        factoring the exponent out of the uncertainties.

        Parameters:
        - value: float, central value
        - upper: float, +uncertainty (same units as value)
        - lower: float, -uncertainty (same units as value)

        Returns:
        - A LaTeX-formatted string like '(4.1^{+0.05}_{-0.02} × 10^{4})'
        """
        if value == 0:
            raise ValueError("Cannot determine exponent for value 0.")

        exp = int(np.floor(np.log10(abs(value))))
        base = value / 10**exp
        upper_scaled = upper / 10**exp
        lower_scaled = lower / 10**exp

        return rf"$\mathbf{{{base:.2g}^{{+{upper_scaled:.2g}}}_{{-{lower_scaled:.2g}}} \times 10^{{{exp}}}}}$"


    @staticmethod
    def format_sci_with_uncertainty_symmetric(value, error):
        """
        Formats a number in scientific notation with asymmetric uncertainties,
        factoring the exponent out of the uncertainties.

        Parameters:
        - value: float, central value
        - upper: float, +uncertainty (same units as value)
        - lower: float, -uncertainty (same units as value)

        Returns:
        - A LaTeX-formatted string like '(4.1^{+0.05}_{-0.02} × 10^{4})'
        """
        if value == 0:
            raise ValueError("Cannot determine exponent for value 0.")

        exp = int(np.floor(np.log10(abs(value))))
        base = value / 10**exp
        error_scaled = error / 10**exp
        #label = rf"$\mathbf{{{base:.2g}^{{+{upper_scaled:.2g}}}_{{-{lower_scaled:.2g}}} \times 10^{{{exp}}}}}$"
        label = rf"$\mathbf{{{base:.2g} \, \pm \, {error_scaled:.2g} \times 10^{{{exp}}}}}$"

        return label




    def plot_individual_BB_fits(self, band_colour_dict, band_marker_dict):
        """
        Make a subplot of many of the individual single BB SEDs fit at particular MJDs.
        """
        nrows, ncols = self.get_indiv_SED_plot_rows_cols(no_SEDs = self.no_indiv_SED_plots) # calculate the number of rows and columns needed given the number of individual SEDs we want to plot

        if self.indiv_plot_MJDs is not None:
            fig, axs = plt.subplots(nrows, ncols, figsize = (8.2, 11.6), sharex = True)
            legend_dict = {}

            #def sci_formatter(x, pos):
            #    return f'{x:.1e}'  
            def standard_form_tex(x, pos):
                if x == 0:
                    return "0"
                exponent = int(np.floor(np.log10(abs(x))))
                coeff = x / (10 ** exponent)
                return rf"${coeff:.1f} \times 10^{{{exponent}}}$"
            formatter = FuncFormatter(standard_form_tex)

            # Set y-sharing per row
            for row in range(nrows):
                for col in range(ncols):
                    ax = axs[row, col]
                    if col > 0:
                        ax.sharey(axs[row, 0])  # share y-axis with the first plot in that row
                        #ax.set_yticklabels([]) # remoce the tick labels 
                        ax.tick_params(labelleft=False)
                    ax.yaxis.set_major_formatter(formatter)  
                    ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds
                    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))


            axs = axs.flatten()
            #formatter = ScalarFormatter(useMathText=False)
            #formatter.set_powerlimits((0, 0))  # Always show scientific notation
            for i, MJD in enumerate(self.indiv_plot_MJDs):
                ax = axs[i]
                MJD_df = self.interp_df[self.interp_df['MJD'] == MJD].copy()
                d_since_peak = MJD_df['d_since_peak'].iloc[0]

                #ax.yaxis.set_major_formatter(formatter)  
                 
                ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
                ax.tick_params(axis='both', labelsize=9.5)



                subplot_title = f'Phase = {d_since_peak:.0f}'+ r'  $\mathbf{D_{\sigma_\chi}}$ = '+f'{self.BB_fit_results.loc[MJD, "brute_chi_sigma_dist"]:.1f}'
                #title2 = fr"$ \mathbf{{ T = {self.BB_fit_results.loc[MJD, 'brute_T_K']:.1e}^{{+{self.BB_fit_results.loc[MJD, 'brute_T_err_upper_K']:.1e}}}_{{-{self.BB_fit_results.loc[MJD, 'brute_T_err_lower_K']:.1e}}} }}$"+'\n'
                #title3 = fr"$ \mathbf{{ R = {self.BB_fit_results.loc[MJD, 'brute_R_cm']:.1e}^{{+{self.BB_fit_results.loc[MJD, 'brute_R_err_upper_cm']:.1e}}}_{{-{self.BB_fit_results.loc[MJD, 'brute_R_err_lower_cm']:.1e}}} }}$"+'\n'
                title3 = 'R = ' + self.format_sci_with_uncertainty(value = self.BB_fit_results.loc[MJD, 'brute_R_cm'], upper = self.BB_fit_results.loc[MJD, 'brute_R_err_upper_cm'], lower = self.BB_fit_results.loc[MJD, 'brute_R_err_lower_cm']) + ' cm'
                title2 = 'T = ' + self.format_sci_with_uncertainty(value = self.BB_fit_results.loc[MJD, 'brute_T_K'], upper = self.BB_fit_results.loc[MJD, 'brute_T_err_upper_K'], lower = self.BB_fit_results.loc[MJD, 'brute_T_err_lower_K']) + ' K\n'
                #if self.guided_UVOT_SED_fits: # add the UVOT guided parameter space limits info to the title
                #    title4 = f"\nT lims: ({self.BB_fit_results.at[MJD, 'T_param_lower_lim']:.1e} - {self.BB_fit_results.at[MJD, 'T_param_upper_lim']:.1e})\n"
                #    title5 = f"R lims: ({self.BB_fit_results.at[MJD, 'R_param_lower_lim']:.1e} - {self.BB_fit_results.at[MJD, 'R_param_upper_lim']:.1e})"
                #    subplot_title = subplot_title + title4 + title5

                if self.interp_df['em_cent_wl'].max() < 8000: # make sure that the wavelength range we're plotting covers all of the bands, some ANTs have a few in the low IR
                    plot_wl = np.linspace(1000, 8000, 300)*1e-8 # wavelength range to plot out BB at in cm
                else: 
                    plot_wl = np.linspace(1000, (self.interp_df['em_cent_wl'].max() + 500), 500)*1e-8 # wavelength range to plot out BB at in cm

                plot_BB_L = blackbody(plot_wl, self.BB_fit_results.loc[MJD, 'brute_R_cm'], self.BB_fit_results.loc[MJD, 'brute_T_K'])
                h_BB, = ax.plot(plot_wl*1e8, plot_BB_L, c = 'k', label = title2 + title3)
                ax.grid(True)
                
                for b in MJD_df['band'].unique():
                    b_df = MJD_df[MJD_df['band'] == b].copy()
                    b_colour = band_colour_dict[b]
                    b_marker = band_marker_dict[b]
                    h = ax.errorbar(b_df['em_cent_wl'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = b_marker, c = b_colour, label = b)
                    legend_dict[b] = h[0]
                
                leg = ax.legend(handles = [h_BB], labels = [title2 + title3], prop = {'weight': 'bold', 'size': '7'})#, loc='lower left', bbox_to_anchor=(0.05, 0.05))
                leg.get_frame().set_alpha(0.6)
                ax.set_title(subplot_title, fontsize = 9.5, fontweight = 'bold')
            

            titlefontsize = 18
            suptitle = f"Single-blackbody SED fits at different epochs of \n{self.ant_name}'s lightcurve"
            fig.supxlabel(r'Emitted wavelength [$\mathbf{\AA}$]', fontweight = 'bold', fontsize = (titlefontsize - 4))
            fig.supylabel(r'Spectral luminosity density (rest-frame) [erg s$\mathbf{^{-1} \, \AA^{-1}}$]', fontweight = 'bold', fontsize = (titlefontsize - 4))
            fig.suptitle(suptitle, fontweight = 'bold', fontsize = titlefontsize)
            fig.legend(legend_dict.values(), legend_dict.keys(), loc = 'upper right', fontsize = 8.5, bbox_to_anchor = (1.005, 0.95))
            fig.subplots_adjust(top=0.875,
                                bottom=0.07,
                                left=0.18,
                                right=0.83,
                                hspace=0.3,
                                wspace=0.24)
            
            if self.save_indiv_BB_plot == True:
                if self.guided_UVOT_SED_fits:
                    savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_subplot_GUIDED_SBB_fits_{self.no_indiv_SED_plots}_({self.individual_BB_plot}).png"

                else:
                    savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_subplot_SBB_fits_{self.no_indiv_SED_plots}_({self.individual_BB_plot}).png"
                plt.savefig(savepath, dpi = 300) 
            
            if self.show_plots:
                plt.show()
            else:
                plt.close()
                





    def plot_individual_double_BB_fits(self, band_colour_dict, band_marker_dict): 
        """
        Make a subplot of many of the individual double BB SEDs fit at particular MJDs.
        """
        nrows, ncols = self.get_indiv_SED_plot_rows_cols(self.no_indiv_SED_plots) # calculate the number of rows and columns needed given the number of individual SEDs we want to plot

        if self.indiv_plot_MJDs is not None:
            fig, axs = plt.subplots(nrows, ncols, figsize = (8.2, 11.6), sharex = True)

            def standard_form_tex(x, pos):
                if x == 0:
                    return "0"
                exponent = int(np.floor(np.log10(abs(x))))
                coeff = x / (10 ** exponent)
                return rf"${coeff:.1f} \times 10^{{{exponent}}}$"
            formatter = FuncFormatter(standard_form_tex)

            # Set y-sharing per row
            for row in range(nrows):
                for col in range(ncols):
                    ax = axs[row, col]
                    if col > 0:
                        ax.sharey(axs[row, 0])  # share y-axis with the first plot in that row
                        #ax.set_yticklabels([]) # remoce the tick labels 
                        ax.tick_params(labelleft=False)
                    ax.yaxis.set_major_formatter(formatter)  
                    ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds
                    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))


            axs = axs.flatten()
            legend_dict = {}
            for i, MJD in enumerate(self.indiv_plot_MJDs):
                ax = axs[i]
                MJD_df = self.interp_df[self.interp_df['MJD'] == MJD].copy()
                d_since_peak = MJD_df['d_since_peak'].iloc[0]


                ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
                ax.tick_params(axis='both', labelsize=9.5)
                #ax.yaxis.set_major_formatter(formatter)  
                #ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds 

                # sort out the titles to present all of the model parameters
                subplot_title = f'Phase = {d_since_peak:.0f}'+ r'  $\mathbf{D_{\sigma_\chi}}$ = '+f'{self.BB_fit_results.loc[MJD, "cf_chi_sigma_dist"]:.1f}'
                title2 = r'T1 = '+f"{self.BB_fit_results.loc[MJD, 'cf_T1_K']:.1e} +/- {self.BB_fit_results.loc[MJD, 'cf_T1_err_K']:.1e} K"
                #title2 = 'T1 = ' + self.format_sci_with_uncertainty_symmetric(value = self.BB_fit_results.loc[MJD, 'cf_T1_K'], error = self.BB_fit_results.loc[MJD, 'cf_T1_err_K']) + ' K'
                title3 = r'R1 = '+f"{self.BB_fit_results.loc[MJD, 'cf_R1_cm']:.1e} +/- {self.BB_fit_results.loc[MJD, 'cf_R1_err_cm']:.1e} cm"
                #title3 = 'R1 = ' + self.format_sci_with_uncertainty_symmetric(value = self.BB_fit_results.loc[MJD, 'cf_R1_cm'], error = self.BB_fit_results.loc[MJD, 'cf_R1_err_cm']) + ' cm'
                title4 = r'T2 = '+f"{self.BB_fit_results.loc[MJD, 'cf_T2_K']:.1e} +/- {self.BB_fit_results.loc[MJD, 'cf_T2_err_K']:.1e} K"
                #title4 = 'T2 = ' + self.format_sci_with_uncertainty_symmetric(value = self.BB_fit_results.loc[MJD, 'cf_T2_K'], error = self.BB_fit_results.loc[MJD, 'cf_T2_err_K']) + ' K'
                title5 = r'R1 = '+f"{self.BB_fit_results.loc[MJD, 'cf_R2_cm']:.1e} +/- {self.BB_fit_results.loc[MJD, 'cf_R2_err_cm']:.1e} cm"
                #title5 = 'R2 = ' + self.format_sci_with_uncertainty_symmetric(value = self.BB_fit_results.loc[MJD, 'cf_R2_cm'], error = self.BB_fit_results.loc[MJD, 'cf_R2_err_cm']) + ' cm'

                #if self.guided_UVOT_SED_fits: # add the UVOT guided parameter space limits info to the title
                #    title6 = f"\nT1 lims: ({self.BB_fit_results.at[MJD, 'T1_param_lower_lim']:.1e} - {self.BB_fit_results.at[MJD, 'T1_param_upper_lim']:.1e})\n"
                #    title7 = f"R1 lims: ({self.BB_fit_results.at[MJD, 'R1_param_lower_lim']:.1e} - {self.BB_fit_results.at[MJD, 'R1_param_upper_lim']:.1e})\n"
                #    title8 = f"T2 lims: ({self.BB_fit_results.at[MJD, 'T2_param_lower_lim']:.1e} - {self.BB_fit_results.at[MJD, 'T2_param_upper_lim']:.1e})\n"
                #    title9 = f"R2 lims: ({self.BB_fit_results.at[MJD, 'R2_param_lower_lim']:.1e} - {self.BB_fit_results.at[MJD, 'R2_param_upper_lim']:.1e})"
                #    subplot_title = subplot_title + title6 + title7 + title8 + title9
                
                
                if self.interp_df['em_cent_wl'].max() < 8000: # make sure that the wavelength range we're plotting covers all of the bands, some ANTs have a few in the low IR
                    plot_wl = np.linspace(1000, 8000, 300)*1e-8 # wavelength range to plot out BB at in cm
                else: 
                    plot_wl = np.linspace(1000, (self.interp_df['em_cent_wl'].max() + 500), 500)*1e-8 # wavelength range to plot out BB at in cm

                plot_BB_L = double_blackbody(lam = plot_wl, R1 = self.BB_fit_results.loc[MJD, 'cf_R1_cm'], T1 = self.BB_fit_results.loc[MJD, 'cf_T1_K'], R2 = self.BB_fit_results.loc[MJD, 'cf_R2_cm'], T2 = self.BB_fit_results.loc[MJD, 'cf_T2_K'])
                plot_BB1_L = blackbody(lam_cm = plot_wl, R_cm = self.BB_fit_results.loc[MJD, 'cf_R1_cm'], T_K = self.BB_fit_results.loc[MJD, 'cf_T1_K'])
                plot_BB2_L = blackbody(lam_cm = plot_wl, R_cm = self.BB_fit_results.loc[MJD, 'cf_R2_cm'], T_K = self.BB_fit_results.loc[MJD, 'cf_T2_K'])
                plot_wl_A = plot_wl*1e8 # the wavelengths for the plot in Angstrom
                ax.plot(plot_wl_A, plot_BB_L, c = 'k')
                h1, = ax.plot(plot_wl_A, plot_BB1_L, c = 'red', linestyle = '--', alpha = 0.5) # 'h1, =' upakcs the 2D array given by ax.plot(), although there is only one element in this since we're only plotting one line
                h2, = ax.plot(plot_wl_A, plot_BB2_L, c = 'blue', linestyle = '--', alpha = 0.5)
                ax.grid(True)
                
                for b in MJD_df['band'].unique():
                    b_df = MJD_df[MJD_df['band'] == b].copy()
                    b_colour = band_colour_dict[b]
                    b_marker = band_marker_dict[b]
                    h = ax.errorbar(b_df['em_cent_wl'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = b_marker, c = b_colour, label = b)
                    legend_dict[b] = h[0]

                ax.set_title(subplot_title, fontsize = 9.5, fontweight = 'bold')
                leg = ax.legend(handles = [h1, h2], labels = [title2 + '\n'+ title3, title4 + '\n'+ title5], fontsize = 5.5, prop = {'weight': 'bold', 'size': 5.5})
                leg.get_frame().set_alpha(0.6)

            
            titlefontsize = 18 
            suptitle = f"Double-blackbody SED fits at different epochs of \n{self.ant_name}'s lightcurve"
            fig.supxlabel(r'Emitted wavelength [$\mathbf{\AA}$]', fontweight = 'bold', fontsize = (titlefontsize - 4))
            fig.supylabel(r'Spectral luminosity density (rest-frame) [erg s$\mathbf{^{-1} \, \AA^{-1}}$]', fontweight = 'bold', fontsize = (titlefontsize - 4))
            fig.suptitle(suptitle, fontweight = 'bold', fontsize = titlefontsize)
            fig.legend(legend_dict.values(), legend_dict.keys(), loc = 'upper right', fontsize = 8.5, bbox_to_anchor = (1.005, 0.95))
            fig.subplots_adjust(top=0.875,
                                bottom=0.07,
                                left=0.18,
                                right=0.83,
                                hspace=0.3,
                                wspace=0.24)
            


            if self.save_indiv_BB_plot == True:
                if self.guided_UVOT_SED_fits:
                    savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_subplot_GUIDED_DBB_fits_{self.no_indiv_SED_plots}_({self.individual_BB_plot}).png"
                else:
                    savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_subplot_DBB_fits_{self.no_indiv_SED_plots}_({self.individual_BB_plot}).png"
                plt.savefig(savepath, dpi = 300) 

            if self.show_plots:
                plt.show()
            else:
                plt.close()





    def plot_individual_power_law_SED_fits(self, band_colour_dict, band_marker_dict):
        """
        Make a subplot of many of the individual power law SEDs fit at particular MJDs.
        """
        nrows, ncols = self.get_indiv_SED_plot_rows_cols(no_SEDs = self.no_indiv_SED_plots) # calculate the number of rows and columns needed given the number of individual SEDs we want to plot

        if self.indiv_plot_MJDs is not None:
            fig, axs = plt.subplots(nrows, ncols, figsize = (8.2, 11.6), sharex = True)
            


            def standard_form_tex(x, pos):
                if x == 0:
                    return "0"
                exponent = int(np.floor(np.log10(abs(x))))
                coeff = x / (10 ** exponent)
                return rf"${coeff:.1f} \times 10^{{{exponent}}}$"
            formatter = FuncFormatter(standard_form_tex)

            # Set y-sharing per row
            for row in range(nrows):
                for col in range(ncols):
                    ax = axs[row, col]
                    if col > 0:
                        ax.sharey(axs[row, 0])  # share y-axis with the first plot in that row
                        #ax.set_yticklabels([]) # remoce the tick labels 
                        ax.tick_params(labelleft=False)
                    ax.yaxis.set_major_formatter(formatter)  
                    ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds
                    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))


            axs = axs.flatten()
            legend_dict = {}
            for i, MJD in enumerate(self.indiv_plot_MJDs):
                ax = axs[i]
                MJD_df = self.interp_df[self.interp_df['MJD'] == MJD].copy()
                d_since_peak = MJD_df['d_since_peak'].iloc[0]

                #ax.yaxis.set_major_formatter(formatter)  
                #ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds 
                ax.tick_params(axis='both', labelsize=9.5)
                ax.xaxis.set_major_locator(MaxNLocator(nbins=4))

                subplot_title = f'Phase = {d_since_peak:.0f}'+ r'  $\mathbf{D_{\sigma_\chi}}$ = '+f'{self.BB_fit_results.loc[MJD, "brute_chi_sigma_dist"]:.1f}'
                #title2 = fr"$ \mathbf{{ A = {self.BB_fit_results.loc[MJD, 'brute_A']:.1e}^{{+{self.BB_fit_results.loc[MJD, 'brute_A_err_upper']:.1e}}}_{{-{self.BB_fit_results.loc[MJD, 'brute_A_err_lower']:.1e}}} }}$"+'\n'
                title2 = 'A = ' + self.format_sci_with_uncertainty(value = self.BB_fit_results.loc[MJD, 'brute_A'], upper = self.BB_fit_results.loc[MJD, 'brute_A_err_upper'], lower = self.BB_fit_results.loc[MJD, 'brute_A_err_lower']) + '\n'
                title3 = r'$\mathbf{\gamma = }$'+f"{self.BB_fit_results.loc[MJD, 'brute_gamma']:.1e}" + r"$\mathbf{\pm}$"+ f" {self.BB_fit_results.loc[MJD, 'brute_gamma_err']:.1e}"
                #title3 = r'$\mathbf{\gamma = }$ ' + self.format_sci_with_uncertainty_symmetric(value = self.BB_fit_results.loc[MJD, 'brute_gamma'], error = self.BB_fit_results.loc[MJD, 'brute_gamma_err'])

                if self.interp_df['em_cent_wl'].max() < 8000: # make sure that the wavelength range we're plotting covers all of the bands, some ANTs have a few in the low IR
                    plot_wl = np.linspace(1000, 8000, 300)*1e-8 # wavelength range to plot out BB at in cm
                else: 
                    plot_wl = np.linspace(1000, (self.interp_df['em_cent_wl'].max() + 500), 500)*1e-8 # wavelength range to plot out BB at in cm
                plot_wl_A = plot_wl*1e8
                
                plot_PL_L = power_law_SED(plot_wl_A, self.BB_fit_results.loc[MJD, 'brute_A'], self.BB_fit_results.loc[MJD, 'brute_gamma'])
                h_BB, = ax.plot(plot_wl_A, plot_PL_L, c = 'k', label = title2 + title3)
                ax.grid(True)
                
                for b in MJD_df['band'].unique():
                    b_df = MJD_df[MJD_df['band'] == b].copy()
                    b_colour = band_colour_dict[b]
                    b_marker = band_marker_dict[b]
                    h = ax.errorbar(b_df['em_cent_wl'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = b_marker, c = b_colour, label = b)
                    legend_dict[b] = h[0]
                
                leg = ax.legend(handles = [h_BB], labels = [title2 + title3], prop = {'weight': 'bold', 'size': '7'})
                leg.get_frame().set_alpha(0.6)
                ax.set_title(subplot_title, fontsize = 9.5, fontweight = 'bold')
            
            titlefontsize = 18
            suptitle = f"Power-law SED fits at different epochs of \n{self.ant_name}'s lightcurve"
            fig.supxlabel(r'Emitted wavelength [$\mathbf{\AA}$]', fontweight = 'bold', fontsize = (titlefontsize - 4))
            fig.supylabel(r'Spectral luminosity density (rest-frame) [erg s$\mathbf{^{-1} \, \AA^{-1}}$]', fontweight = 'bold', fontsize = (titlefontsize - 4))
            fig.suptitle(suptitle, fontweight = 'bold', fontsize = titlefontsize)
            fig.legend(legend_dict.values(), legend_dict.keys(), loc = 'upper right', fontsize = 8.5, bbox_to_anchor = (1.005, 0.95))       
            fig.subplots_adjust(top=0.875,
                                bottom=0.07,
                                left=0.18,
                                right=0.83,
                                hspace=0.3,
                                wspace=0.24)

            if self.save_indiv_BB_plot == True:
                if self.guided_UVOT_SED_fits:
                    savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_subplot_GUIDED_PL_fits_{self.no_indiv_SED_plots}_({self.individual_BB_plot}).png"
                else:
                    savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_subplot_PL_fits_{self.no_indiv_SED_plots}_({self.individual_BB_plot}).png"
                plt.savefig(savepath, dpi = 300) 

            if self.show_plots:
                plt.show()
            else:
                plt.close()






    def plot_SED_params_vs_time(self, band_colour_dict):
        """
        A function which creates a plot of the model parameters vs time
        """

        # some of the plots need y lims
        SBB_T_plot_lims = {'ZTF18aczpgwm': (None, None), 
                            'ZTF19aailpwl': (0.0, 2e4), 
                            'ZTF19aamrjar': (0.0, 2.5e4), 
                            'ZTF19aatubsj': (None, None), 
                            'ZTF20aanxcpf': (None, None), 
                            'ZTF20abgxlut': (0.0, 2.3e4), 
                            'ZTF20abodaps': (0.0, 4e4), 
                            'ZTF20abrbeie': (0.0, 2e4), 
                            'ZTF20acvfraq': (None, None), 
                            'ZTF21abxowzx': (0.0, 2.5e4), 
                            'ZTF22aadesap': (0.0, 2e4),
                            'PS1-10adi': (None, None), 
                            'ASASSN-17jz': (None, None), 
                            'ASASSN-18jd': (None, None)}

        SBB_R_plot_lims = {'ZTF18aczpgwm': (None, None), 
                            'ZTF19aailpwl': (None, None), 
                            'ZTF19aamrjar': (None, None), 
                            'ZTF19aatubsj': (None, None), 
                            'ZTF20aanxcpf': (None, None), 
                            'ZTF20abgxlut': (0.0, 8e15), 
                            'ZTF20abodaps': (0.0, 1.2e16), 
                            'ZTF20abrbeie': (None, None), 
                            'ZTF20acvfraq': (None, None), 
                            'ZTF21abxowzx': (None, None), 
                            'ZTF22aadesap': (0.0, 5e15), 
                            'PS1-10adi': (None, None), 
                            'ASASSN-17jz': (None, None), 
                            'ASASSN-18jd': (None, None)}


        DBB_T1_plot_lims = {'ZTF18aczpgwm': (None, None), 
                            'ZTF19aailpwl': (0, 1.5e4), 
                            'ZTF19aamrjar': (None, None), 
                            'ZTF19aatubsj': (None, None), 
                            'ZTF20aanxcpf': (None, None), 
                            'ZTF20abgxlut': (None, None), 
                            'ZTF20abodaps': (None, None), 
                            'ZTF20abrbeie': (None, None), 
                            'ZTF20acvfraq': (0, 1.5e4), 
                            'ZTF21abxowzx': (None, None), 
                            'ZTF22aadesap': (1500, 7500), 
                            'PS1-10adi': (None, None), 
                            'ASASSN-17jz': (0, 1e4), 
                            'ASASSN-18jd': (None, None)}
        
        DBB_R1_plot_lims = {'ZTF18aczpgwm': (None, None), 
                            'ZTF19aailpwl': (0, 5.3e16), 
                            'ZTF19aamrjar': (None, None), 
                            'ZTF19aatubsj': (None, None), 
                            'ZTF20aanxcpf': (None, None), 
                            'ZTF20abgxlut': (None, None), 
                            'ZTF20abodaps': (None, None), 
                            'ZTF20abrbeie': (None, None), 
                            'ZTF20acvfraq': (-1.9e17, 8e17), 
                            'ZTF21abxowzx': (None, None), 
                            'ZTF22aadesap': (1e5, 1.2e17), 
                            'PS1-10adi': (None, None), 
                            'ASASSN-17jz': (0, 3.5e16), 
                            'ASASSN-18jd': (None, None)}
        
        DBB_T2_plot_lims = {'ZTF18aczpgwm': (None, None), 
                            'ZTF19aailpwl': (1e4, 4.3e4), 
                            'ZTF19aamrjar': (None, None), 
                            'ZTF19aatubsj': (None, None), 
                            'ZTF20aanxcpf': (None, None), 
                            'ZTF20abgxlut': (None, None), 
                            'ZTF20abodaps': (None, None), 
                            'ZTF20abrbeie': (None, None), 
                            'ZTF20acvfraq': (-4e5, 8e5), 
                            'ZTF21abxowzx': (None, None), 
                            'ZTF22aadesap': (9000, 30000), 
                            'PS1-10adi': (None, None), 
                            'ASASSN-17jz': (0, 8e4), 
                            'ASASSN-18jd': (None, None)}
        
        DBB_R2_plot_lims = {'ZTF18aczpgwm': (None, None), 
                            'ZTF19aailpwl': (0, 6e15), 
                            'ZTF19aamrjar': (None, None), 
                            'ZTF19aatubsj': (None, None), 
                            'ZTF20aanxcpf': (None, None), 
                            'ZTF20abgxlut': (None, None), 
                            'ZTF20abodaps': (None, None), 
                            'ZTF20abrbeie': (None, None), 
                            'ZTF20acvfraq': (-1.3e16, 1.4e16), 
                            'ZTF21abxowzx': (None, None), 
                            'ZTF22aadesap': (1e14, 1.4e15), 
                            'PS1-10adi': (None, None), 
                            'ASASSN-17jz': (0, 8e15), 
                            'ASASSN-18jd': (None, None)}

        PL = self.SED_type == 'power_law'
        SBB = self.SED_type == 'single_BB'
        DBB = self.SED_type == 'double_BB'

        def standard_form_tex(x, pos):
            if x == 0:
                return "0"
            exponent = int(np.floor(np.log10(abs(x))))
            coeff = x / (10 ** exponent)
            return rf"${coeff:.1f} \times 10^{{{exponent}}}$"
        formatter = FuncFormatter(standard_form_tex)


        legfontsize = 10.5
        tickfontsize = 13


        if SBB:
            fig, axs = plt.subplots(3, 1, sharex=True, figsize = (6.5, 13)) # (8.2, 11.6)
            ax1, ax2, ax4 = axs

            # getting the colour scale for plotting the params vs MJD coloured by chi sigma distance
            colour_cutoff = 3.0
            chi_cutoff = 0.1
            #norm = Normalize(vmin = 0.0, vmax = colour_cutoff)

            BB_2dp = self.BB_fit_results[self.BB_fit_results['no_bands'] == 2].copy() # since this woudl mean N = M, so we aren't fitting, but solving
            BB_2dp_good_fit = BB_2dp[BB_2dp['brute_chi'] <= chi_cutoff].copy()
            BB_N_greater_M = self.BB_fit_results[self.BB_fit_results['no_bands'] > 2].copy()



            # top left = light curve
            for b in self.interp_df['band'].unique():
                b_df = self.interp_df[self.interp_df['band'] == b].copy()
                b_em_cent_wl = b_df['em_cent_wl'].iloc[0]
                b_colour = band_colour_dict[b]
                ax1.errorbar(b_df['d_since_peak'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = 'o', c = b_colour, 
                            linestyle = 'None', markeredgecolor = 'k', markeredgewidth = '0.5', label = fr"{b_em_cent_wl:.0f} $\AA$")
            
            if self.ant_name == 'ZTF20abodaps':
                ax1.set_yscale('log')

            


            # separating the BB fit results into high and low chi sigma distance so we can plot the ones wiht low chi sigma distance in a colour map, and the high sigma distance in one colour
            BB_low_chi_dist = BB_N_greater_M[abs(BB_N_greater_M['brute_chi_sigma_dist']) <= colour_cutoff].copy() # taking the absolute values since we allow the sigma distance to be nagetive now, but a value of -0.5 is just as good as 0.5 (I think)
            BB_high_chi_dist = BB_N_greater_M[abs(BB_N_greater_M['brute_chi_sigma_dist']) > colour_cutoff].copy()
            BB_low_chi_dist['abs_brute_chi_sig_dist'] = abs(BB_low_chi_dist['brute_chi_sigma_dist'])


            # ax2 middle: blackbody radius vs MJD
            ax2.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['brute_R_cm'], yerr = [BB_N_greater_M['brute_R_err_lower_cm'], BB_N_greater_M['brute_R_err_upper_cm']], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0$', fmt = 'o', mec = 'k', mew = '0.5', zorder = 3)
            

            # first plot all fits (good and bad) in grey
            ax2.errorbar(BB_2dp['d_since_peak'], BB_2dp['brute_R_cm'], yerr = [BB_2dp['brute_R_err_lower_cm'], BB_2dp['brute_R_err_upper_cm']], linestyle = 'None', c = '#696868', 
                        fmt = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)
            
            # the plot the good fits over the top in white
            ax2.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['brute_R_cm'], yerr = [BB_2dp_good_fit['brute_R_err_lower_cm'], BB_2dp_good_fit['brute_R_err_upper_cm']], linestyle = 'None', c = 'white', 
                        fmt = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)
            

            
            #ax2.errorbar(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['brute_R_cm'], yerr = [BB_low_chi_dist['brute_R_err_lower_cm'], BB_low_chi_dist['brute_R_err_upper_cm']],  c = BB_low_chi_dist['abs_brute_chi_sig_dist'].to_numpy(), 
            #            label = 'Brute force gridding results', fmt = 'o', zorder = 3, mec = 'k', mew = '0.5')
            
            sc = ax2.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['brute_R_cm'], cmap = 'viridis', c = BB_low_chi_dist['abs_brute_chi_sig_dist'].to_numpy(), 
                            label = r'N > M and $D_{\sigma_\chi} \leq 3.0$', marker = 'o', edgecolors = 'k', linewidths = 0.5, zorder = 4)
            

            ####################################################################################################################################################
            ####################################################################################################################################################
            ####################################################################################################################################################
            ####################################################################################################################################################
             #

            divider2 = make_axes_locatable(ax2)
            cax2 = divider2.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax2) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')

            #cbar_label = r'Goodness-of-fit metric, $D_{\sigma_\chi}$'
            #cbar = plt.colorbar(sc, ax = ax2)
            #cbar.set_label(label = cbar_label)

            ax2.set_ylim(SBB_R_plot_lims[self.ant_name])
            



            # ax4 bottom: blackbody temperature vs MJD
            ax4.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['brute_T_K'], yerr = [BB_N_greater_M['brute_T_err_lower_K'], BB_N_greater_M['brute_T_err_upper_K']], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0$', marker = 'o', zorder = 3)
            

            # first plot all fits (good and bad) in grey
            ax4.errorbar(BB_2dp['d_since_peak'], BB_2dp['brute_T_K'], yerr = [BB_2dp['brute_T_err_lower_K'], BB_2dp['brute_T_err_upper_K']], linestyle = 'None', c = '#696868', 
                        marker = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)
            
            # the plot the good fits over the top in white
            ax4.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['brute_T_K'], yerr = [BB_2dp_good_fit['brute_T_err_lower_K'], BB_2dp_good_fit['brute_T_err_upper_K']], linestyle = 'None', c = 'white', 
                        marker = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)
            

            
            sc = ax4.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['brute_T_K'], cmap = 'viridis', c = BB_low_chi_dist['abs_brute_chi_sig_dist'].to_numpy(), 
                        label = r'N > M and $D_{\sigma_\chi} \leq 3.0$', marker = 'o', edgecolors = 'k', linewidths = 0.5, zorder = 4)
            

            divider4 = make_axes_locatable(ax4)
            cax4 = divider4.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax4) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')


            ax4.set_ylim(SBB_T_plot_lims[self.ant_name])

            for ax in [ax1, ax2, ax4]:
                ax.grid(True)
                ax.yaxis.set_major_formatter(formatter)  
                ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds 
                ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
                ax.tick_params(axis='both', labelsize= tickfontsize)
                if self.ant_name == 'ZTF20abodaps':
                    if ax == ax1:
                        continue
                ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

                

                #ax.set_xlim(MJDs_for_fit[ANT_name])

            titlefontsize = 17
            axisfontsize = 14
            subaxis_fontsize = 13.5

            if self.ant_name == 'ASASSN-18jd': # it has too many bands lol
                legend_ncols = 2
            else:
                legend_ncols = 1

            
            ax1.legend(ncols = legend_ncols, fontsize = legfontsize, loc = 'upper right')
            ax2.legend(fontsize = legfontsize)
            ax4.legend(fontsize = legfontsize)

            ax1.set_ylabel('Spectral luminosity density \n(rest-frame) '+r' [erg s$\mathbf{^{-1}}$$\mathbf{\AA^{-1}}$]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax2.set_ylabel('Blackbody radius [cm]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax4.set_ylabel('Blackbody temperature [K]', fontweight = 'bold', fontsize = subaxis_fontsize)
            fig.align_ylabels()
            fig.suptitle(f"Single-Blackbody fit results across \n{self.ant_name}'s light curve", fontweight = 'bold', fontsize = titlefontsize)
            fig.supxlabel('Phase (rest-frame) [days]', fontweight = 'bold', fontsize = axisfontsize)
            fig.subplots_adjust(top=0.91,
                                bottom=0.058,
                                left=0.24,
                                right=0.9,
                                hspace=0.15,
                                wspace=0.19)
            
            savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_SBB_param_vs_DSP.png"




        if PL:
            fig, axs = plt.subplots(3, 1, sharex=True, figsize = (6.5, 13))
            ax1, ax2, ax4 = axs

            # getting the colour scale for plotting the params vs MJD coloured by chi sigma distance
            colour_cutoff = 3.0
            chi_cutoff = 0.1

            BB_2dp = self.BB_fit_results[self.BB_fit_results['no_bands'] == 2].copy() # since this woudl mean N = M, so we aren't fitting, but solving
            BB_2dp_good_fit = BB_2dp[BB_2dp['brute_chi'] <= chi_cutoff].copy()
            BB_N_greater_M = self.BB_fit_results[self.BB_fit_results['no_bands'] > 2].copy()

            # top left = light curve
            for b in self.interp_df['band'].unique():
                b_df = self.interp_df[self.interp_df['band'] == b].copy()
                b_em_cent_wl = b_df['em_cent_wl'].iloc[0]
                b_colour = band_colour_dict[b]
                ax1.errorbar(b_df['d_since_peak'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = 'o', c = b_colour, 
                            linestyle = 'None', markeredgecolor = 'k', markeredgewidth = '0.5', label = fr"{b_em_cent_wl:.0f} $\AA$")
            #ax1.legend()
            ax1.yaxis.set_major_formatter(formatter)  
            ax1.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds 
            if self.ant_name == 'ZTF20abodaps':
                ax1.set_yscale('log')
            

            
            # separating the BB fit results into high and low chi sigma distance so we can plot the ones wiht low chi sigma distance in a colour map, and the high sigma distance in one colour
            BB_low_chi_dist = BB_N_greater_M[abs(BB_N_greater_M['brute_chi_sigma_dist']) <= colour_cutoff].copy() # taking the absolute values since we allow the sigma distance to be nagetive now, but a value of -0.5 is just as good as 0.5 (I think)
            BB_high_chi_dist = BB_N_greater_M[abs(BB_N_greater_M['brute_chi_sigma_dist']) > colour_cutoff].copy()
            BB_low_chi_dist['abs_brute_chi_sig_dist'] = abs(BB_low_chi_dist['brute_chi_sigma_dist'])


            # ax2 top right: A vs DSP
            ax2.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['brute_A'], yerr = [BB_N_greater_M['brute_A_err_lower'], BB_N_greater_M['brute_A_err_upper']], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0 $', fmt = 'o', mec = 'k', mew = '0.5', capsize = 5, zorder = 3)
            

            sc = ax2.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['brute_A'], cmap = 'viridis', c = BB_low_chi_dist['abs_brute_chi_sig_dist'].to_numpy(), 
                            label = r'N > M and $D_{\sigma_\chi} \leq 3.0 $', marker = 'o', zorder = 4, edgecolors = 'k', linewidths = 0.5)   

            # first plot all fits (good and bad) in grey
            ax2.errorbar(BB_2dp['d_since_peak'], BB_2dp['brute_A'], yerr = [BB_2dp['brute_A_err_lower'], BB_2dp['brute_A_err_upper']], linestyle = 'None', c = '#696868', 
                        fmt = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)       

            # the plot the good fits over the top in white
            ax2.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['brute_A'], yerr = [BB_2dp_good_fit['brute_A_err_lower'], BB_2dp_good_fit['brute_A_err_upper']], linestyle = 'None', c = 'white', 
                        fmt = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)   

  
            #if self.guided_UVOT_SED_fits:
            #    ax2.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['brute_A'], yerr = [abs(BB_N_greater_M['brute_A'] - BB_N_greater_M['A_param_lower_lim']), abs(BB_N_greater_M['A_param_upper_lim'] - BB_N_greater_M['brute_A'])], linestyle = 'None', c = 'red', 
            #                fmt = 'None', alpha = 0.3, label = 'Param space search lims')
            #    ax2.set_ylim(((BB_N_greater_M['brute_A'].min())*0.7, (BB_N_greater_M['brute_A'].max())*1.3)) # since the allowed parameter space to explore can span orders of magnitude, limit the y lim to be within 30% of the most extreme A values on the plot

            #cbar_label = r'Brute goodness of BB fit ($\chi_{\nu}$ sig dist)'
            #cbar = plt.colorbar(sc, ax = ax2)
            #cbar.set_label(label = cbar_label)

            divider2 = make_axes_locatable(ax2)
            cax2 = divider2.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax2) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')

            ax2.set_yscale('log')



            # ax4 bottom right: gamma vs DSP
            ax4.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['brute_gamma'], yerr = BB_N_greater_M['brute_gamma_err'], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0 $', marker = 'o', capsize = 5, zorder = 3)
            

            sc = ax4.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['brute_gamma'], cmap = 'viridis', c = BB_low_chi_dist['abs_brute_chi_sig_dist'].to_numpy(), 
                        label = r'N > M and $D_{\sigma_\chi} \leq 3.0 $', marker = 'o', edgecolors = 'k', linewidths = 0.5, zorder = 4)

            # first plot all fits (good and bad) in grey
            ax4.errorbar(BB_2dp['d_since_peak'], BB_2dp['brute_gamma'], yerr = BB_2dp['brute_gamma_err'], linestyle = 'None', c = '#696868', 
                        marker = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)
            
            # the plot the good fits over the top in white
            ax4.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['brute_gamma'], yerr = BB_2dp_good_fit['brute_gamma_err'], linestyle = 'None', c = 'white', 
                        marker = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)

            #if self.guided_UVOT_SED_fits:
            #    ax4.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['brute_gamma'], yerr = [abs(BB_N_greater_M['brute_gamma'] - BB_N_greater_M['gamma_param_lower_lim']), abs(BB_N_greater_M['gamma_param_upper_lim'] - BB_N_greater_M['brute_gamma'])], linestyle = 'None', c = 'red', 
            #                fmt = 'None', alpha = 0.3, label = 'Param space search lims')
            #    ax4.set_ylim(((BB_N_greater_M['brute_gamma'].min())*1.3, (BB_N_greater_M['brute_gamma'].max())*0.7)) # since the allowed parameter space to explore can span orders of magnitude, limit the y lim to be within 10% of the most extreme A values on the plot

            

            
            divider4 = make_axes_locatable(ax4)
            cax4 = divider4.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax4) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')
            
            #plt.colorbar(sc, ax = ax4, label = 'Chi sigma distance')
            #cbar_label = r'Brute goodness of BB fit ($\chi_{\nu}$ sig dist)'
            #cbar = plt.colorbar(sc, ax = ax4)
            #cbar.set_label(label = cbar_label)

            for ax in [ax1, ax2, ax4]:
                ax.grid(True)
                ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
                ax.tick_params(axis='both', labelsize= tickfontsize)
                if self.ant_name == 'ZTF20abodaps':
                    if ax == ax1:
                        continue
                if ax != ax2:
                    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
                #ax.legend(fontsize = 8)
                #ax.set_xlim(MJDs_for_fit[ANT_name])

            #if self.guided_UVOT_SED_fits:
            #    title = f"UVOT GUIDED power law SED fit results across {self.ant_name}'s light curve (UVOT guided err scalefactor = {self.UVOT_guided_err_scalefactor})"
            #else:
            #    title = f"Power law SED fit results across {self.ant_name}'s light curve"


            titlefontsize = 17
            axisfontsize = 14
            subaxis_fontsize = 13.5

            if self.ant_name == 'ASASSN-18jd': # it has too many bands lol
                legend_ncols = 2
            else:
                legend_ncols = 1

            
            ax1.legend(ncols = legend_ncols, fontsize = legfontsize, loc = 'upper right')
            ax2.legend(fontsize = legfontsize)
            ax4.legend(fontsize = legfontsize)

            ax1.set_ylabel('Spectral luminosity density \n'+r'(rest-frame) [erg s$\mathbf{^{-1} \AA^{-1}}$]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax2.set_ylabel(r'Power-law amplitude (A) [erg s$\mathbf{^{-1} \AA^{-1}}$]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax4.set_ylabel(r'Power-law $\mathbf{\gamma}$ [no units]', fontweight = 'bold', fontsize = subaxis_fontsize)
            fig.suptitle(f"Power-law fit results across \n{self.ant_name}'s light curve", fontweight = 'bold', fontsize = titlefontsize)
            fig.supxlabel('Phase (rest-frame) [days]', fontweight = 'bold', fontsize = axisfontsize)
            fig.subplots_adjust(top=0.91,
                                bottom=0.058,
                                left=0.24,
                                right=0.9,
                                hspace=0.15,
                                wspace=0.19)
            
            if self.guided_UVOT_SED_fits:
                savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_GUIDED_PL_param_vs_DSP.png"
            else:
                savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_PL_param_vs_DSP.png"



        if DBB:
            legfontsize = 12
            tickfontsize = 15
            fig, axs = plt.subplots(5, 1, sharex=True, figsize = (8.2, 17.4))
            ax1, ax2, ax3, ax5, ax6 = axs

            # getting the colour scale for plotting the params vs MJD coloured by chi sigma distance
            colour_cutoff = 3.0
            chi_cutoff = 0.1

            M_params = 4
            BB_2dp = self.BB_fit_results[self.BB_fit_results['no_bands'] == M_params].copy() # since this woudl mean N = M, so we aren't fitting, but solving
            BB_2dp_good_fit = BB_2dp[BB_2dp['cf_chi'] <= chi_cutoff].copy()
            BB_N_greater_M = self.BB_fit_results[self.BB_fit_results['no_bands'] > M_params].copy()

            # top left = light curve
            for b in self.interp_df['band'].unique():
                b_df = self.interp_df[self.interp_df['band'] == b].copy()
                b_em_cent_wl = b_df['em_cent_wl'].iloc[0]
                b_colour = band_colour_dict[b]
                ax1.errorbar(b_df['d_since_peak'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = 'o', c = b_colour, 
                            linestyle = 'None', markeredgecolor = 'k', markeredgewidth = '0.5', label = fr"{b_em_cent_wl:.0f} $\AA$")
            #ax1.legend()
            

            
            # separating the BB fit results into high and low chi sigma distance so we can plot the ones wiht low chi sigma distance in a colour map, and the high sigma distance in one colour
            BB_low_chi_dist = BB_N_greater_M[abs(BB_N_greater_M['cf_chi_sigma_dist']) <= colour_cutoff].copy() # taking the absolute values since we allow the sigma distance to be nagetive now, but a value of -0.5 is just as good as 0.5 (I think)
            BB_high_chi_dist = BB_N_greater_M[abs(BB_N_greater_M['cf_chi_sigma_dist']) > colour_cutoff].copy()
            BB_low_chi_dist['abs_cf_chi_sig_dist'] = abs(BB_low_chi_dist['cf_chi_sigma_dist'])


            # ax2 top middle: T1 vs DSP
            ax2.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_T1_K'], yerr = BB_N_greater_M['cf_T1_err_K'], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0 $', fmt = 'o', mec = 'k', mew = '0.5', capsize = 5, zorder = 3)
            
            sc = ax2.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['cf_T1_K'], cmap = 'viridis', c = BB_low_chi_dist['abs_cf_chi_sig_dist'].to_numpy(), 
                            label = r'N > M and $D_{\sigma_\chi} \leq 3.0 $', marker = 'o', zorder = 4, edgecolors = 'k', linewidths = 0.5)

            # first plot all fits (good and bad) in grey
            ax2.errorbar(BB_2dp['d_since_peak'], BB_2dp['cf_T1_K'], yerr = BB_2dp['cf_T1_err_K'], linestyle = 'None', c = '#696868', 
                        fmt = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)

            # the plot the good fits over the top in white
            ax2.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['cf_T1_K'], yerr = BB_2dp_good_fit['cf_T1_err_K'], linestyle = 'None', c = 'white', 
                        fmt = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)

  
            #if self.guided_UVOT_SED_fits:
            #    ax2.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_T1_K'], yerr = [abs(BB_N_greater_M['cf_T1_K'] - BB_N_greater_M['T1_param_lower_lim']), abs(BB_N_greater_M['T1_param_upper_lim'] - BB_N_greater_M['cf_T1_K'])], linestyle = 'None', c = 'red', 
            #                fmt = 'None', alpha = 0.3, label = 'Param space search lims')
            #    ax2.set_ylim(((BB_N_greater_M['cf_T1_K'].min())*0.7, (BB_N_greater_M['cf_T1_K'].max())*1.3)) # since the allowed parameter space to explore can span orders of magnitude, limit the y lim to be within 30% of the most extreme A values on the plot

            

            ax2.set_ylim(DBB_T1_plot_lims[self.ant_name])


            divider2 = make_axes_locatable(ax2)
            cax2 = divider2.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax2) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')


            #cbar_label = r'Curve_fit goodness of BB fit ($\chi_{\nu}$ sig dist)'
            #cbar = plt.colorbar(sc, ax = ax2)
            #cbar.set_label(label = cbar_label)



            # ax3 top right: T2 vs DSP
            ax5.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_T2_K'], yerr = BB_N_greater_M['cf_T2_err_K'], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0 $', fmt = 'o', mec = 'k', mew = '0.5', capsize = 5, zorder = 3)
            
            # first plot all fits (good and bad) in grey
            ax5.errorbar(BB_2dp['d_since_peak'], BB_2dp['cf_T2_K'], yerr = BB_2dp['cf_T2_err_K'], linestyle = 'None', c = '#696868', 
                        fmt = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)
            
            # the plot the good fits over the top in white
            ax5.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['cf_T2_K'], yerr = BB_2dp_good_fit['cf_T2_err_K'], linestyle = 'None', c = 'white', 
                        fmt = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)


            sc = ax5.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['cf_T2_K'], cmap = 'viridis', c = BB_low_chi_dist['abs_cf_chi_sig_dist'].to_numpy(), 
                            label = r'N > M and $D_{\sigma_\chi} \leq 3.0 $', marker = 'o', zorder = 4, edgecolors = 'k', linewidths = 0.5)
  
            #if self.guided_UVOT_SED_fits:
            #    ax3.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_T2_K'], yerr = [abs(BB_N_greater_M['cf_T2_K'] - BB_N_greater_M['T2_param_lower_lim']), abs(BB_N_greater_M['T2_param_upper_lim'] - BB_N_greater_M['cf_T2_K'])], linestyle = 'None', c = 'red', 
            #                fmt = 'None', alpha = 0.3, label = 'Param space search lims')
            #    ax3.set_ylim(((BB_N_greater_M['cf_T2_K'].min())*0.7, (BB_N_greater_M['cf_T2_K'].max())*1.3)) # since the allowed parameter space to explore can span orders of magnitude, limit the y lim to be within 30% of the most extreme A values on the plot

            ax5.set_ylim(DBB_T2_plot_lims[self.ant_name])

            divider5 = make_axes_locatable(ax5)
            cax5 = divider5.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax5) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')

            #cbar_label = r'Curve_fit goodness of BB fit ($\chi_{\nu}$ sig dist)'
            #cbar = plt.colorbar(sc, ax = ax3)
            #cbar.set_label(label = cbar_label)




            # ax5 bottom middle: R1 vs DSP
            ax3.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_R1_cm'], yerr = BB_N_greater_M['cf_R1_err_cm'], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0 $', fmt = 'o', mec = 'k', mew = '0.5', capsize = 5, zorder = 3)

            sc = ax3.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['cf_R1_cm'], cmap = 'viridis', c = BB_low_chi_dist['abs_cf_chi_sig_dist'].to_numpy(), 
                            label = r'N > M and $D_{\sigma_\chi} \leq 3.0 $', marker = 'o', zorder = 4, edgecolors = 'k', linewidths = 0.5)
            
            # first plot all fits (good and bad) in grey
            ax3.errorbar(BB_2dp['d_since_peak'], BB_2dp['cf_R1_cm'], yerr = BB_2dp['cf_R1_err_cm'], linestyle = 'None', c = '#696868', 
                        fmt = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)
            
            # the plot the good fits over the top in white
            ax3.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['cf_R1_cm'], yerr = BB_2dp_good_fit['cf_R1_err_cm'], linestyle = 'None', c = 'white', 
                        fmt = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)
            

  
            #if self.guided_UVOT_SED_fits:
            #    ax5.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_R1_cm'], yerr = [abs(BB_N_greater_M['cf_R1_cm'] - BB_N_greater_M['R1_param_lower_lim']), abs(BB_N_greater_M['R1_param_upper_lim'] - BB_N_greater_M['cf_R1_cm'])], linestyle = 'None', c = 'red', 
            #                fmt = 'None', alpha = 0.3, label = 'Param space search lims')
            #    ax5.set_ylim(((BB_N_greater_M['cf_R1_cm'].min())*0.7, (BB_N_greater_M['cf_R1_cm'].max())*1.3)) # since the allowed parameter space to explore can span orders of magnitude, limit the y lim to be within 30% of the most extreme A values on the plot

            

            
            ax3.set_ylim(DBB_R1_plot_lims[self.ant_name])

            divider3 = make_axes_locatable(ax3)
            cax3 = divider3.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax3) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')

            #cbar_label = r'Curve_fit goodness of BB fit ($\chi_{\nu}$ sig dist)'
            #cbar = plt.colorbar(sc, ax = ax5)
            #cbar.set_label(label = cbar_label)



            # ax6 bottom right: R2 vs DSP
            ax6.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_R2_cm'], yerr = BB_N_greater_M['cf_R2_err_cm'], linestyle = 'None', c = 'k', 
                        label = r'N > M and $D_{\sigma_\chi} > 3.0 $', fmt = 'o', mec = 'k', mew = '0.5', capsize = 5, zorder = 3)
            
            sc = ax6.scatter(BB_low_chi_dist['d_since_peak'], BB_low_chi_dist['cf_R2_cm'], cmap = 'viridis', c = BB_low_chi_dist['abs_cf_chi_sig_dist'].to_numpy(), 
                            label = r'N > M and $D_{\sigma_\chi} \leq 3.0 $', marker = 'o', zorder = 4, edgecolors = 'k', linewidths = 0.5)

            # first plot all fits (good and bad) in grey
            ax6.errorbar(BB_2dp['d_since_peak'], BB_2dp['cf_R2_cm'], yerr = BB_2dp['cf_R2_err_cm'], linestyle = 'None', c = '#696868', 
                        fmt = 'o', label = r'N = M and $\chi^2 > 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 1)

            # the plot the good fits over the top in white
            ax6.errorbar(BB_2dp_good_fit['d_since_peak'], BB_2dp_good_fit['cf_R2_cm'], yerr = BB_2dp_good_fit['cf_R2_err_cm'], linestyle = 'None', c = 'white', 
                        fmt = 'o', label = r'N = M and $\chi^2 \leq 0.1$', mec = 'k', mew = '0.5', ecolor = 'k', zorder = 2)
  
            #if self.guided_UVOT_SED_fits:
            #    ax6.errorbar(BB_N_greater_M['d_since_peak'], BB_N_greater_M['cf_R2_cm'], yerr = [abs(BB_N_greater_M['cf_R2_cm'] - BB_N_greater_M['R2_param_lower_lim']), abs(BB_N_greater_M['R2_param_upper_lim'] - BB_N_greater_M['cf_R2_cm'])], linestyle = 'None', c = 'red', 
            #                fmt = 'None', alpha = 0.3, label = 'Param space search lims')
            #    ax6.set_ylim(((BB_N_greater_M['cf_R2_cm'].min())*0.7, (BB_N_greater_M['cf_R2_cm'].max())*1.3)) # since the allowed parameter space to explore can span orders of magnitude, limit the y lim to be within 30% of the most extreme A values on the plot

            

            
            ax6.set_ylim(DBB_R2_plot_lims[self.ant_name])

            divider6 = make_axes_locatable(ax6)
            cax6 = divider6.append_axes("right", size="2%", pad=0.15)  # Adjust position with `pad`
            cbar = plt.colorbar(sc, cax = cax6) 
            cbar_label = r'Goodness-of-fit, $\mathbf{D_{\sigma_\chi}}$'
            cbar.set_label(label = cbar_label, fontsize = 12, fontweight = 'bold')


            #cbar_label = r'Curve_fit goodness of BB fit ($\chi_{\nu}$ sig dist)'
            #cbar = plt.colorbar(sc, ax = ax6)
            #cbar.set_label(label = cbar_label)




            for ax in [ax1, ax2, ax3, ax5, ax6]:
                ax.grid(True)
                ax.yaxis.set_major_formatter(formatter)  
                ax.get_yaxis().get_offset_text().set_visible(False) # Hide the offset that matplotlib adds 
                ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
                ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
                ax.tick_params(axis='both', labelsize= tickfontsize)
                
                #ax.set_xlim(MJDs_for_fit[ANT_name])

            #if self.guided_UVOT_SED_fits:
            #    title = f"UVOT GUIDED curve_fit double blackbody SED fit results across {self.ant_name}'s light curve (UVOT guided err scalefactor = {self.UVOT_guided_err_scalefactor})"
            #else:
            #    title = f"Curve_fit double blackbody SED fit results across {self.ant_name}'s light curve"


            titlefontsize = 17
            axisfontsize = 14
            subaxis_fontsize = 13.5

            if self.ant_name == 'ASASSN-18jd': # it has too many bands lol
                legend_ncols = 2
            else:
                legend_ncols = 1

            
            ax1.legend(ncols = legend_ncols, fontsize = legfontsize, loc = 'upper right')
            ax2.legend(fontsize = legfontsize)
            ax3.legend(fontsize = legfontsize)
            ax5.legend(fontsize = legfontsize)
            ax6.legend(fontsize = legfontsize)


            ax1.set_ylabel('Spectral luminosity density \n'+r'(rest-frame) [erg s$\mathbf{^{-1} \AA^{-1}}$]', fontweight = 'bold', fontsize = subaxis_fontsize)
            #ax2.set_ylabel(r'$\mathbf{T_{\text{BB, }1}}$ [K]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax2.set_ylabel('BB1 Temperature [K]', fontweight = 'bold', fontsize = subaxis_fontsize)
            #ax5.set_ylabel(r'$\mathbf{T_{\text{BB, }2}}$ [K]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax5.set_ylabel('BB2 Temperature [K]', fontweight = 'bold', fontsize = subaxis_fontsize)
            #ax3.set_ylabel(r'$\mathbf{R_{\text{BB, }1}}$ [cm]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax3.set_ylabel('BB1 Radius [cm]', fontweight = 'bold', fontsize = subaxis_fontsize)
            #ax6.set_ylabel(r'$\mathbf{R_{\text{BB, }2}}$ [cm]', fontweight = 'bold', fontsize = subaxis_fontsize)
            ax6.set_ylabel('BB2 Radius [cm]', fontweight = 'bold', fontsize = subaxis_fontsize)
            fig.suptitle(f"Double-Blackbody fit results across \n{self.ant_name}'s light curve", fontweight = 'bold', fontsize = titlefontsize)
            fig.supxlabel('Phase (rest-frame) [days]', fontweight = 'bold', fontsize = axisfontsize)
            fig.subplots_adjust(top=0.93,
                                bottom=0.058,
                                left=0.24,
                                right=0.91,
                                hspace=0.15,
                                wspace=0.19)
            
            if self.guided_UVOT_SED_fits:
                savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_GUIDED_DBB_param_vs_DSP.png"
            else:
                savepath = self.base_path + f"plots/BB fits/proper_BB_fits/{self.ant_name}/{self.ant_name}_DBB_param_vs_DSP.png"



        if self.save_param_vs_time_plot:
            plt.savefig(savepath, dpi = 300)

        if self.show_plots:
                plt.show()
        else:
            plt.close()
            








    def save_SED_fit_results(self, guided):
        """
        This function saves the SED fitting results in a dataframe

        INPUTS
        -----------------------
        guided: (bool) If True, this means that the SED fitting was done using the method in which we fit the UVOT MJD SEDs first then use these to fuide the nearby non-UVOT SEDs. 
                If False, this emans each MJD SEd fit was taken independently from the last.
        """
        if self.save_SED_fit_file:
            if self.SED_type == 'single_BB':
                note = 'SBB'
            elif self.SED_type == 'double_BB':
                note = 'DBB'
            elif self.SED_type == 'power_law':
                note = 'PL'

            if guided:
                note = 'UVOT_guided_'+note

            savepath = self.base_path + f"data/SED_fits/{self.ant_name}/{self.ant_name}_{note}_SED_fit_across_lc_new.csv"
            self.BB_fit_results.to_csv(savepath, index = False)

            # ALSO SAVE THE SAMPLED SED PARAMETER DATAFRAME. CONTAINS PARAMETER VALUES SAMPLED FROM THE CHI SQUARED CONTOUR WHERE CHI<= MIN_CHI + 2.3
            savepath = self.base_path + f"data/SED_fits/{self.ant_name}/{self.ant_name}_{note}_sampled_params.csv"
            self.BB_fit_samples.to_csv(savepath, index = True)





