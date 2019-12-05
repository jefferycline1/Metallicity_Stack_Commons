from chun_codes.cardelli import cardelli
import astropy.units as u

lambda0   = [3726.18, 4101.73, 4340.46, 4363.21, 4861.32, 4958.91, 5006.84]
line_type = ['Oxy2', 'Balmer', 'Balmer', 'Single', 'Balmer', 'Single', 'Single']
line_name = ['OII_3727', 'HDELTA', 'HGAMMA', 'OIII_4363', 'HBETA', 'OIII_4958', 'OIII_5007']

fitting_lines_dict = {"lambda0":lambda0, "line_type":line_type, "line_name":line_name}

fitspath_reagen = '/Users/reagenleimbach/Desktop/Zcalbase_gal/'

fitspath_caroline = 'C:\\Users\\carol\\Google Drive\\'

# Define k values for dust attenuation
k_values = cardelli(lambda0 * u.Angstrom)
k_dict   = dict(zip(line_name,k_values))
