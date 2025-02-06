import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import scipy.optimize as opt
from matplotlib import cm
from matplotlib.colors import Normalize
sys.path.append("C:/Users/laure/OneDrive/Desktop/YoRiS desktop/YoRiS") # this allows us to import plotting preferences and functions
from plotting_preferences import band_colour_dict, band_ZP_dict, band_obs_centwl_dict, ANT_redshift_dict, ANT_luminosity_dist_cm_dict, MJDs_for_fit
from functions import load_interp_ANT_data, fit_BB_across_lc






# load in the interpolated data
interp_df_list, transient_names, list_of_bands = load_interp_ANT_data()



#idx = 0
for idx in range(11):

    ANT_name = transient_names[idx]
    interp_lc= interp_df_list[idx]
    ANT_bands = list_of_bands[idx]
    print()
    print(ANT_name)
    if idx == 5:
        print()
        print(f'SKIPPING {ANT_name} FOR NOW')
        print()
        continue

    BB_curvefit = True
    BB_brute = False
    BB_fit_results = fit_BB_across_lc(interp_lc, brute = BB_brute, curvefit = BB_curvefit)
    

    # what we want: 
    # L_rf vs MJD: on this plot there will be the actual (binned) data, the polyfit and the interpolated data from the polyfit
    # BB R vs MJD: on this plot we'll have curve_fit R and brute force grid R, perhaps with a colour scale to indicate the sigma distance of the reduced chi squared for the 
    #               BB fit to indicate how much we should trust the value
    # BB T vs MJD: basically the same as BB R vs MJD
    # sigma distance vs MJD?: sigma distance for the curve_fit and brute force results. I feel like this would be good to have alongside the polyfit, because if the polyfit was bad at this MJD,
    #               then the interpolated L_rf of the band might be bad, too, which might mean that the BB fit will struggle to fit to this poorly interpolated datapoint.


    #fig = plt.figure(figsize = (16, 7.3))
    #ax1, ax2, ax3, ax4 = [plt.subplot(2, 2, i) for i in np.arange(1, 5, 1)]
    fig, axs = plt.subplots(2, 2, sharex=True, figsize = (16, 7.2))
    ax1, ax2 = axs[0]
    ax3, ax4 = axs[1]

    # getting the colour scale for plotting the BB T and R vs MJD coloured by chi sigma distance
    colour_cutoff = 5.0
    norm = Normalize(vmin = 0.0, vmax = colour_cutoff)

    # separating the BB fit results into high and low chi sigma distance so we can plot the ones wiht low chi sigma distance in a colour map, and the high sigma distance in one colour
    BB_low_chi_dist = BB_fit_results[BB_fit_results['cf_chi_sigma_dist'] <= colour_cutoff]
    BB_high_chi_dist = BB_fit_results[BB_fit_results['cf_chi_sigma_dist'] > colour_cutoff]



    # top left: the L_rf vs MJD light curve
    for b in ANT_bands: # iterate through all of the bands present in the ANT's light curve
        b_df = interp_lc[interp_lc['band'] == b].copy()
        b_colour = band_colour_dict[b]
        ax1.errorbar(b_df['MJD'], b_df['L_rf'], yerr = b_df['L_rf_err'], fmt = 'o', c = b_colour, 
                    linestyle = 'None', markeredgecolor = 'k', markeredgewidth = '0.5', label = b)
        ax1.set_ylabel('Rest frame luminosity')
        


    BB_fit_results = BB_fit_results.dropna(subset = ['red_chi_1sig'])

    if BB_curvefit == True:
        #norm = Normalize(vmin = BB_fit_results['cf_chi_sigma_dist'].min(), vmax = BB_fit_results['cf_chi_sigma_dist'].max())
        # top right: blackbody radius vs MJD
        ax2.errorbar(BB_fit_results['MJD'], BB_fit_results['cf_R_cm'], yerr = BB_fit_results['cf_R_err_cm'], linestyle = 'None', c = 'k', 
                    fmt = 'o', zorder = 1, label = f'BB fit chi sig dist >{colour_cutoff}')
        sc = ax2.scatter(BB_low_chi_dist['MJD'], BB_low_chi_dist['cf_R_cm'], cmap = 'jet', c = np.ravel(BB_low_chi_dist['cf_chi_sigma_dist']), 
                    label = 'Curve fit results', marker = 'o', zorder = 2, edgecolors = 'k', linewidths = 0.5)

        cbar_label = r'Goodness of BB fit ($\chi_{\nu}$ sig dist)'
        cbar = plt.colorbar(sc, ax = ax2)
        cbar.set_label(label = cbar_label)


        # bottom left: reduced chi squared sigma distance vs MJD
        ax3.scatter(BB_fit_results['MJD'], BB_fit_results['cf_chi_sigma_dist'], marker = 'o', label = 'Curve fit results', edgecolors = 'k', linewidths = 0.5)

        # bottom right: blackbody temperature vs MJD
        ax4.errorbar(BB_fit_results['MJD'], BB_fit_results['cf_T_K'], yerr = BB_fit_results['cf_T_err_K'], linestyle = 'None', c = 'k', 
                    fmt = 'o', zorder = 1, label = f'BB fit chi sig dist >{colour_cutoff}')
        sc = ax4.scatter(BB_low_chi_dist['MJD'], BB_low_chi_dist['cf_T_K'], cmap = 'jet', c = BB_low_chi_dist['cf_chi_sigma_dist'], 
                    label = 'Curve fit results', marker = 'o', edgecolors = 'k', linewidths = 0.5, zorder = 2)
        
        #plt.colorbar(sc, ax = ax4, label = 'Chi sigma distance')
        cbar_label = r'Goodness of BB fit ($\chi_{\nu}$ sig dist)'
        cbar = plt.colorbar(sc, ax = ax4)
        cbar.set_label(label = cbar_label)


        
    if BB_brute == True:
        # top right: blackbody radius vs MJD
        ax2.scatter(BB_fit_results['MJD'], BB_fit_results['brute_R_cm'], linestyle = 'None', cmap = 'jet', c = BB_fit_results['brute_chi_sigma_dist'], 
                    label = 'brute force gridding results', fmt = 'None')
        
        # bottom left: reduced chi squared sigma distance vs MJD
        ax3.scatter(BB_fit_results['MJD'], BB_fit_results['brute_chi_sigma_dist'], marker = '^', label = 'Brute force gridding results', ecolors = 'k', linewdiths = 0.5)

        # bottom right: blackbody temperature vs MJD
        ax4.scatter(BB_fit_results['MJD'], BB_fit_results['brute_T_K'], linestyle = 'None', cmap = 'jet', c = BB_fit_results['brute_chi_sigma_dist'], 
                    label = 'Brute force gridding results', fmt = '^')

    for ax in [ax1, ax2, ax3, ax4]:
        ax.grid(True)
        ax.set_xlim(MJDs_for_fit[ANT_name])
        ax.legend(fontsize = 8)

    ax2.set_ylabel('Blackbody radius / cm')
    ax3.set_ylabel('Reduced chi squared sigma distance \n (<=1 = Good fit)')
    ax4.set_ylabel('Blackbody temperature / K')
    fig.suptitle(f"Blackbody fit results across {ANT_name}'s light curve")
    fig.supxlabel('MJD')
    fig.subplots_adjust(top=0.92,
                        bottom=0.085,
                        left=0.055,
                        right=0.97,
                        hspace=0.15,
                        wspace=0.19)
    plt.show()

