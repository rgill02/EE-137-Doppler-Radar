#Imports
import threading
import queue
import numpy as np
from My_Utils import *
from scipy.constants import c

################################################################################
class Processor:
	"""
	The processing chain for the heart rate variability application
	"""
	def __init__(self, ts_us, chunk_size, record_q, res_q, to_plot="freq"):
		"""
		PURPOSE: creates a new HRV_Processor
		ARGS:
			ts_us (float): sampling period (us)
			chunk_size (int): number of samples in one processing chunk
			record_q (Queue): queue to pull chunks from
			res_q (Queue): queue to write results to
			to_plot (str): what to plot, options: raw, freq
		RETURNS: new instance of a Processor
		NOTES:
		"""
		#Save arguments
		self.ts_us = ts_us
		self.ts = ts_us / 1e6
		self.fs = 1 / self.ts
		self.res_q = res_q
		self.record_q = record_q
		self.to_plot = to_plot

		#Initialize other variables
		nfft = 2 ** (nextpow2(chunk_size) + 2);
		self.nfft = nfft
		self.f = np.linspace(-nfft / 2.0, nfft / 2.0 - 1, num=nfft) * (self.fs / nfft)
		self.t = np.arange(start=0, stop=self.ts*chunk_size, step=self.ts)
		self.fc = 10.525e9;
		self.c = c;
		self.v = self.f * c / 2 / self.fc;
		self.v_mph = self.v / 0.44704;

		#Create high pass filter
		high_pass_cutoff_mph = 6;
		high_pass_cutoff = 2 * high_pass_cutoff_mph * 0.44704 * self.fc / c;
		self.filter = np.zeros(nfft, dtype=np.cfloat)
		self.filter[np.where(self.f <= -high_pass_cutoff)] = 1
		self.filter[np.where(self.f >= high_pass_cutoff)] = 1

		#Setup processing thread variables
		self.proc_thread = None
		self.proc_keep_going = threading.Event()
		self.proc_keep_going.clear()

		#Setup result dictionary
		self.setup_res_dict()

	############################################################################
	def setup_res_dict(self):
		self.res = {
			"cpi_num": 0,
			"eng": 0,
			"detc": False,
			"vel": 0
		}
		if self.to_plot == "freq":
			self.res["x"] = self.v_mph
			self.res["xlabel"] = "Velocity (mph)"
			self.res["ylabel"] = "Magnitude (Linear)"
			self.res["title"] = "Signal Velocities"
			self.res["xlim"] = (0, 50)
			self.res["ylim"] = (0, 13)
		else:
			self.res["x"] = self.t * 1e3
			self.res["xlabel"] = "Time (ms)"
			self.res["ylabel"] = "Voltage"
			self.res["title"] = "Raw Signal"
			self.res["xlim"] = (0, 500)
			self.res["ylim"] = (-2.5, 2.5)

	############################################################################
	def __del__(self):
		"""
		PURPOSE: performs any necessary cleanup
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		self.stop()

	############################################################################
	def start(self):
		"""
		PURPOSE: starts the processing thread
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		if self.proc_thread == None or not self.is_running():
			self.proc_thread = threading.Thread(target = self.run)
			self.proc_thread.start()

	############################################################################
	def stop(self):
		"""
		PURPOSE: stops the processing thread
		ARGS: none
		RETURNS: none
		NOTES: blocks until thread stops
		"""
		if self.proc_thread:
			self.proc_keep_going.clear()
			self.proc_thread.join()
			self.proc_thread = None

	############################################################################
	def is_running(self):
		"""
		PURPOSE: checks if the processing thread is running
		ARGS: none
		RETURNS: True if running, False if stopped
		NOTES:
		"""
		return self.proc_keep_going.is_set()

	############################################################################
	def get_status(self):
		"""
		PURPOSE: gets the status of this thread
		ARGS: none
		RETURNS: dictionary of statuses
		NOTES:
		"""
		status = {
			"running" : self.is_running()
		}
		return status

	############################################################################
	def run(self):
		"""
		PURPOSE: performs the processing
		ARGS: none
		RETURNS: none
		NOTES: calling 'start' runs this in a separate thread
		"""
		#Indicate processor is running
		self.proc_keep_going.set()
		cpi_num = 0

		try:
			#Run until told to stop
			while self.is_running():
				#Get chunk to process
				try:
					chunk = self.record_q.get(timeout=0.1)
				except queue.Empty as e:
					continue
				sig = self.remove_dc(chunk)
				eng = self.compute_energy(sig)
				detc = self.detect(eng)
				hsig = self.filter_sig(sig)
				vel = self.compute_velocity(hsig)
				if not detc:
					vel = 0
				self.res["cpi_num"] = cpi_num
				self.res["eng"] = eng
				self.res["detc"] = detc
				self.res["vel"] = vel
				if self.to_plot == "freq":
					self.res["y"] = abs(hsig)
				else:
					self.res["y"] = sig
					#self.res["ylim"] = (np.min(sig), np.max(sig))
				cpi_num += 1
				self.res_q.put(self.res)
		except Exception as e:
			print("ERROR: 'processor thread' got exception %s" % type(e))
			print(e)
			self.proc_keep_going.clear()

		#Cleanup

	############################################################################
	def remove_dc(self, sig):
		"""
		PURPOSE: removes the dc from the signal
		ARGS:
			sig (numpy array): signal to filter
		RETURNS: numpy array representing filtered signal
		NOTES:
		"""
		return sig - np.mean(sig);

	############################################################################
	def compute_energy(self, sig):
		"""
		PURPOSE: computes the energy in the signal
		ARGS:
			sig (numpy array): signal to filter
		RETURNS: (float) energy
		NOTES:
		"""
		return np.sum(np.abs(sig) ** 2)

	############################################################################
	def detect(self, eng):
		"""
		PURPOSE: checks if the signal is a detection
		ARGS:
			eng (float): energy in signal
		RETURNS: (bool) True for deteciton, False if not
		NOTES:
		"""
		thresh = 0.2070
		if eng > thresh:
			return True
		return False

	############################################################################
	def filter_sig(self, sig):
		"""
		PURPOSE: applies our filter to a signal
		ARGS:
			sig (numpy array): signal to filter
		RETURNS: numpy array representing filtered signal in frequency domain
		NOTES:
		"""
		#Convert to frequency space
		H = np.fft.fftshift(np.fft.fft(sig, n=self.nfft))
		#Apply filter
		return H * self.filter

	############################################################################
	def compute_velocity(self, sig):
		"""
		PURPOSE: computes the velocity of the signal
		ARGS:
			sig (numpy array): signal in frequency domain
		RETURNS: (float) velocity
		NOTES:
		"""
		idx = np.argmax(abs(sig))
		return abs(self.v_mph[idx])

################################################################################
if __name__ == "__main__":
	import time
	import matplotlib.pyplot as plt

	

	