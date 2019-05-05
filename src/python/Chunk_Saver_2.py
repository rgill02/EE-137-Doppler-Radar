#Imports
import threading
import queue
from scipy.io import savemat
import numpy as np

################################################################################
class Chunk_Saver:
	"""
	Saves chunks of data to a mat file
	"""
	def __init__(self, savefile, ts_us, chunk_size, record_q):
		"""
		PURPOSE: creates a new Chunk_Saver
		ARGS:
			savefile (str): full path to '.mat' file to save to
			ts_us (int): sampling period (microseconds)
			chunk_size (int): number of samples to expect in one chunk
			record_q (Queue): queue to push chunks to
		RETURNS: new instance of a Chunk Saver
		NOTES: does not save file until thread is stopped
		"""
		#Save arguments
		self.savefile = str(savefile)
		self.ts_us = int(ts_us)
		self.chunk_size = int(chunk_size)
		self.record_q = record_q
		self.file_num = 0

		#Setup thread variables
		self.thread = None
		self.keep_going = threading.Event()
		self.keep_going.clear()

		#Keeps track of if we have grabbed any data
		self.chunk_count = 0

		#Part of dictionary to be saved to mat file
		self.dict_to_save = {'ts_us': self.ts_us, 'chunk_size': self.chunk_size}

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
		PURPOSE: starts the thread
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		if self.thread == None or not self.is_running():
			self.thread = threading.Thread(target = self.run)
			self.thread.start()

	############################################################################
	def stop(self):
		"""
		PURPOSE: stops the thread
		ARGS: none
		RETURNS: none
		NOTES: blocks until thread stops
		"""
		if self.thread:
			self.keep_going.clear()
			self.thread.join()
			self.thread = None

	############################################################################
	def is_running(self):
		"""
		PURPOSE: checks if the thread is running
		ARGS: none
		RETURNS: True if running, False if stopped
		NOTES:
		"""
		return self.keep_going.is_set()

	############################################################################
	def get_status(self):
		"""
		PURPOSE: gets the status of this thread
		ARGS: none
		RETURNS: dictionary of statuses
		NOTES:
		"""
		status = {
			"running" : self.is_running(),
			"chunk_count" : self.chunk_count
		}
		return status

	############################################################################
	def run(self):
		"""
		PURPOSE: performs the polling
		ARGS: none
		RETURNS: none
		NOTES: calling 'start' runs this in a separate thread
		"""
		#Indicate processor is running
		self.keep_going.set()

		try:
			#Run until told to stop
			while self.is_running():
				try:
					chunk = self.record_q.get(timeout=0.5)
				except queue.Empty as e:
					continue
				if not self.chunk_count:
					self.data = chunk
				else:
					self.data = np.concatenate((self.data, chunk))
				self.chunk_count += 1
		except Exception as e:
			print("ERROR: 'saver thread' got exception %s" % type(e))
			print(e)
			self.keep_going.clear()

		#Drain queue
		while self.record_q.qsize():
			chunk = self.record_q.get()
			if not self.chunk_count:
				self.data = chunk
			else:
				self.data = np.concatenate((self.data, chunk))
			self.chunk_count += 1

		#Save file
		if self.chunk_count:
			self.dict_to_save['data'] = self.data
			self.file_num += 1
			savemat("%s_%d.mat" % (self.savefile, self.file_num), mdict=self.dict_to_save)

################################################################################
if __name__ == "__main__":
	import math
	import time

	ts_us = 200
	chunk_size = 2500
	savefile = "test_chunk_saver"
	record_q = queue.Queue()

	saver = Chunk_Saver(savefile, ts_us, chunk_size, record_q)

	#Create fake data
	t = np.arange(chunk_size)
	x1 = np.sin(2 * math.pi * (10 / chunk_size) * t)
	x2 = np.sin(2 * math.pi * (20 / chunk_size) * t)
	x3 = np.sin(2 * math.pi * (50 / chunk_size) * t)
	x4 = np.sin(2 * math.pi * (100 / chunk_size) * t)
	record_q.put(x1)
	record_q.put(x2)
	record_q.put(x3)
	record_q.put(x4)

	saver.start()

	try:
		while saver.is_running():
			time.sleep(0.1)
			if record_q.qsize() <= 0:
				break
	except KeyboardInterrupt as e:
		pass

	saver.stop()

	time.sleep(2)

	record_q.put(x1)
	record_q.put(x2)
	record_q.put(x3)
	record_q.put(x4)

	saver.start()

	try:
		while saver.is_running():
			time.sleep(0.1)
			if record_q.qsize() <= 0:
				break
	except KeyboardInterrupt as e:
		pass

	saver.stop()