from os.path import join

import numpy as np
from astropy.io import ascii as asc
from astropy.table import vstack
from astropy.table import Table, Column
import glob

from ..temp_metallicity_calc import metallicity_calculation


def main(fitspath, dataset, composite_file, outfile):
    """
    Purpose:
      Reads in composite table(s) containing bin information to
      determine temperature-based metallicity from composite average
      T_e and individual line ratios ([OII]/H-beta, [OIII]/H-beta)

    :param fitspath: str containing folder path
    :param dataset: str containing sub-folder (specific to stacking approach)
    :param composite_file: str containing filename of composite data
    :param outfile: str containing filename of output file
    """

    # Read in composite table
    composite_table = asc.read(composite_file)

    bin_id = composite_table['ID'].data
    bin_temp = composite_table['Temperature'].data

    # Read in tables containing line ratios, bins, etc.
    det3_table = asc.read(join(fitspath, 'get_det3_table2.tbl'))
    bin_table = asc.read(join(fitspath, dataset+'_2d_binning_datadet3.tbl'))
    # Not used for now
    # average_table = asc.read(join(fitspath, dataset+'_Average_R23_O32_Values.tbl'))

    # Populate composite temperature for individual galaxies
    adopted_temp = np.zeros(len(det3_table))
    for comp_bin, comp_temp in zip(bin_id, bin_temp):
        bin_idx = np.where(bin_table['Bin_number'].data == comp_bin)[0]
        adopted_temp[bin_idx] = comp_temp

    O2 = det3_table['O2'].data  # [OII]3726,3728 fluxes
    O3 = det3_table['O3'].data  # [OIII]4959,5007 fluxes (Assume 3.1:1 ratio)
    Hb = det3_table['Hb'].data  # H-beta fluxes

    com_O_log, metal_dict = metallicity_calculation(adopted_temp, O2/Hb, O3/Hb)

    # Update [det3_table] to include two new columns
    col_temp = Column(adopted_temp, name='Temperature')
    col_metal = Column(com_O_log, name='com_O_log')
    det3_table.add_columns([col_temp, col_metal])  # Add at the end (default)

    # Write Astropy ASCII table containing composite T_e and derived metallicity
    det3_table.write(outfile, format='ascii.fixed_width_two_line')
