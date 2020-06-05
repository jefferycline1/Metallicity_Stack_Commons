from astropy.io import ascii as asc
from astropy.table import Table, Column
import numpy as np
from os.path import join, exists

from .. import k_dict, line_name_short
from ..column_names import filename_dict, dust0

# Balmer decrement Case B, zero reddening
HdHb_CaseB = 0.259  # Hd/Hb ratio
HgHb_CaseB = 0.468  # Hg/Hb ratio
HaHb_CaseB = 2.86   # Ha/Hb ratio

HB = line_name_short['HB']
HG = line_name_short['HG']
HD = line_name_short['HD']

k_HBETA  = k_dict[HB]
k_HGAMMA = k_dict[HG]


def compute_EBV(fitspath, use_revised=False):
    """
    Purpose:
      Determines E(B-V) from Hg/Hb flux ratio

    :param fitspath: str containing root path
    :param use_revised: Boolean to indicate whether to use regular or revised tables
    """

    combine_file = join(fitspath, filename_dict['bin_fit_rev']) if use_revised \
        else join(fitspath, filename_dict['bin_fit'])

    print("Reading : " + combine_file)
    combine_asc = asc.read(combine_file)

    ID = combine_asc['bin_ID'].data
    HBETA  = combine_asc[HB+'_Flux_Observed'].data
    HGAMMA = combine_asc[HG+'_Flux_Observed'].data
    HDELTA = combine_asc[HD+'_Flux_Observed'].data

    HgHb = HGAMMA / HBETA
    HdHb = HDELTA / HBETA

    EBV = -2.5 * np.log10(HgHb/HgHb_CaseB)/(k_HGAMMA - k_HBETA)

    col1 = Column(HgHb, name=dust0[1])
    col2 = Column(HdHb, name=dust0[2])
    col3 = Column(EBV,  name=dust0[0])

    out_ascii = join(fitspath, filename_dict['bin_derived_prop_rev']) if use_revised \
        else join(fitspath, filename_dict['bin_derived_prop'])

    if not exists(out_ascii):
        print("File not found : ", out_ascii)

        raise FileNotFoundError
    else:
        tab1 = asc.read(out_ascii)
        print("Adding dust attenuation information to " + out_ascii)

        tab1.add_columns([col1, col2, col3])
        asc.write(tab1, out_ascii, format='fixed_width_two_line')


def compute_A(EBV):
    """
    Purpose:
      Compute A(Lambda) for all possible emission lines

    :param EBV: float value of E(B-V)
      Has not been configured to handle a large array.  Some array handling would be needed

    :return A_dict: dict containing A(lambda) with keys identical to k_dict
    """

    k_arr  = np.array(list(k_dict.values()))

    A_arr  = k_arr * EBV
    A_dict = dict(zip(list(k_dict.keys()), A_arr))

    return A_dict


def line_ratio_atten(ratio, EBV, wave_top, wave_bottom):

    k_top    = k_dict[wave_top]
    k_bottom = k_dict[wave_bottom]

    ratio_atten = ratio * 10**(0.4*EBV*(k_top - k_bottom))

    return ratio_atten


def Hb_SFR(log_LHb, EBV):
    """
    Purpose:
      Determine dust-corrected SFR using the H-beta luminosity and a
      measurement for nebular attenuation

    Equation below is based on Eq. 2 in Ly et al. (2015), ApJ, 805, 45
      DOI: https://doi.org/10.1088/0004-637X/805/1/45

    :param log_LHb: numpy array or float containing logarithm of H-beta
           luminosity in units of erg/s
    :param EBV: numpy array or float providing E(B-V)

    :return logSFR: numpy array or float containing the SFR in
            logarithmic units of M_sun/yr
    """

    logSFR = np.log10(4.4e-42 * HaHb_CaseB) + 0.4*EBV*k_HBETA + log_LHb

    return logSFR
