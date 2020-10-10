from os.path import join, exists

from chun_codes import random_pdf, compute_onesig_pdf
from .. import line_name
from astropy.io import ascii as asc
import numpy as np

from ..column_names import filename_dict, temp_metal_names0, npz_filename_dict, \
    bin_names0
from .ratios import flux_ratios
from .temp_metallicity_calc import temp_calculation, metallicity_calculation
from .attenuation import compute_EBV


def write_npz(path, npz_files, dict_list):
    """
    Purpose:
      Write numpy files with provided dictionaries

    :param path: str - prefix for filename output
    :param npz_files: list - contains npz file names
    :param dict_list: list - contains dictionaries for each corresponding npz file

    :return: Write npz files
    """
    for file, dict_input in zip(npz_files, dict_list):
        npz_outfile = join(path, file)
        if exists(npz_outfile):
            print("Overwriting : "+npz_outfile)
        else:
            print("Writing : "+npz_outfile)
        np.savez(npz_outfile, **dict_input)


def fluxes_derived_prop(path, raw=False, binned_data=True, apply_dust=False, revised=True):
    """
    Purpose:
      Use measurements and their uncertainties to perform a randomization
      approach. The randomization is performed on individual emission lines.
      It carries that information to derived flux ratios and then
      determines electron temperature and metallicity

    :param path: str of full path
    :param raw: bool to do a simple calculation, no randomization. Default: False
    :param binned_data: bool for whether to analysis binned data. Default: True
    :param apply_dust: bool for whether to apply dust attenuation. Default: False
    :param revised: bool to indicate if revised validation table is used. Default: True
    """

    # Define files to read in for binned data
    if binned_data:
        flux_file = join(path, filename_dict['bin_fit'])
        if not raw:
            prop_file = join(path, filename_dict['bin_derived_prop'])
            if revised:
                print('Using REVISED validation table')
                verify_file = join(path, filename_dict['bin_valid_rev'])
            else:
                print('Using validation table')
                verify_file = join(path, filename_dict['bin_valid'])

    flux_tab0 = asc.read(flux_file)
    if not raw:
        prop_tab0 = asc.read(prop_file)

    if binned_data:
        if not raw:
            verify_tab = asc.read(verify_file)
            detection = verify_tab['Detection'].data

            # For now we are only considering those with reliable detection and
            # excluding those with reliable non-detections (detect = 0.5)
            detect_idx = np.where((detection == 1))[0]

            ID = verify_tab['bin_ID'].data
            ID_detect = ID[detect_idx]
            print(ID_detect)

            flux_tab = flux_tab0[detect_idx]
            prop_tab = prop_tab0[detect_idx]

    flux_cols     = [str0+'_Flux_Gaussian' for str0 in line_name]
    flux_rms_cols = [str0+'_RMS' for str0 in line_name]

    #
    # EMISSION-LINE SECTION
    #

    if raw:
        flux_dict = dict()
        for aa, flux, rms in zip(range(len(flux_cols)), flux_cols, flux_rms_cols):

            # Fill in dictionary
            flux_dict[line_name[aa]] = flux_tab0[flux].data

        flux_ratios_dict = flux_ratios(flux_dict)

        derived_prop_dict = dict()

        Te = temp_calculation(flux_ratios_dict['R'])
        derived_prop_dict[temp_metal_names0[0]] = Te
        metal_dict = metallicity_calculation(Te, flux_ratios_dict['two_beta'],
                                             flux_ratios_dict['three_beta'])
        derived_prop_dict.update(metal_dict)

        # Write Astropy table
        # Get bin IDs and composite measurements in one dicitonary and write to table
        tbl_dict = {bin_names0[0]: np.int_(flux_tab0[bin_names0[0]].data)}
        tbl_dict.update(flux_ratios_dict)
        tbl_dict.update(derived_prop_dict)

        outfile = join(path, filename_dict['bin_derived_prop'])
        if not exists(outfile):
            print("Writing : ", outfile)
        else:
            print("Overwriting : ", outfile)
        asc.write(tbl_dict, output=outfile, overwrite=True,
                  format='fixed_width_two_line')
    else:
        # Initialize dictionaries

        flux_pdf_dict = dict()
        flux_peak_dict = dict()
        flux_error_dict = dict()

        # Randomization for emission-line fluxes
        for aa, flux, rms in zip(range(len(flux_cols)), flux_cols, flux_rms_cols):
            flux_pdf = random_pdf(flux_tab[flux], flux_tab[rms], seed_i=aa,
                                  n_iter=1000)
            err, peak = compute_onesig_pdf(flux_pdf, flux_tab[flux], usepeak=True)

            # Fill in dictionary
            flux_pdf_dict[line_name[aa]] = flux_pdf
            flux_peak_dict[line_name[aa] + '_peak'] = peak
            flux_error_dict[line_name[aa] + '_error'] = err

            # Update values
            flux_tab0[line_name[aa] + '_Flux_Gaussian'][detect_idx] = peak

        # Write revised emission-line fit ASCII table
        new_flux_file = join(path, filename_dict['bin_fit_rev'])
        if exists(new_flux_file):
            print("Overwriting: "+new_flux_file)
        else:
            print("Writing: "+new_flux_file)
        asc.write(flux_tab0, new_flux_file, overwrite=True,
                  format='fixed_width_two_line')

        # Save flux npz files
        npz_files = [npz_filename_dict['flux_pdf'],
                     npz_filename_dict['flux_errors'],
                     npz_filename_dict['flux_peak']]
        dict_list = [flux_pdf_dict, flux_error_dict, flux_peak_dict]
        write_npz(path, npz_files, dict_list)

        # Obtain line ratio distributions: logR23, logO32, two_beta, three_beta, R
        # Also include Balmer decrements
        flux_ratios_dict = flux_ratios(flux_pdf_dict)

        #
        # Get EBV from Balmer decrement if apply_dust set
        #

        if apply_dust:
            EBV = compute_EBV(flux_ratios_dict['HgHb'], source='HgHb')
        else:
            EBV = None

        #
        # DERIVED PROPERTIES SECTION
        #

        # Initialize dictionaries
        derived_prop_pdf_dict = dict()
        derived_prop_error_dict = dict()
        derived_prop_peak_dict = dict()

        # Calculate temperature distribution
        Te_pdf = temp_calculation(flux_ratios_dict['R'], EBV=EBV)
        derived_prop_pdf_dict[temp_metal_names0[0]] = Te_pdf

        # Calculate metallicity distribution
        metal_dict = metallicity_calculation(Te_pdf, flux_ratios_dict['two_beta'],
                                             flux_ratios_dict['three_beta'],
                                             EBV=EBV)
        derived_prop_pdf_dict.update(metal_dict)

        # Loop for each derived properties (T_e, metallicity, etc.)
        for names0 in temp_metal_names0:
            arr0 = prop_tab[names0].data

            err_prop, peak_prop = \
                compute_onesig_pdf(derived_prop_pdf_dict[names0], arr0,
                                   usepeak=True)

            # Fill in dictionary
            derived_prop_error_dict[names0+'_error'] = err_prop
            derived_prop_peak_dict[names0+'_peak'] = peak_prop

            # Update values
            prop_tab0[names0][detect_idx] = peak_prop

        # Write revised properties ASCII table
        if not apply_dust:
            new_prop_file = join(path, filename_dict['bin_derived_prop_rev'])
        else:
            new_prop_file = join(path, filename_dict['bin_derived_prop_rev_dust'])
        if exists(new_prop_file):
            print("Overwriting: "+new_prop_file)
        else:
            print("Writing: "+new_prop_file)
        asc.write(prop_tab0, new_prop_file, overwrite=True,
                  format='fixed_width_two_line')

        # Save derived properties npz files
        npz_files = [npz_filename_dict['der_prop_pdf'],
                     npz_filename_dict['der_prop_errors'],
                     npz_filename_dict['der_prop_peak']]
        dict_list = [derived_prop_pdf_dict, derived_prop_error_dict,
                     derived_prop_peak_dict]
        write_npz(path, npz_files, dict_list)
