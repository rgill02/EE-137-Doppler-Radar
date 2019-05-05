import math
import numpy as np

def nextpow2(x):
	return math.ceil(math.log(x, 2))

def find_nearest_idx(array, value):
	array = np.asarray(array)
	idx = (np.abs(array - value)).argmin()
	return idx
