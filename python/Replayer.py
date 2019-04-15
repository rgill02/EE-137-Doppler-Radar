#Imports
import threading
import queue
import math
from scipy.io import loadmat
import time

################################################################################
class Replayer:
	"""
	Replays recorded files as if they were being sampled in real time
	"""
	def __init__(self, savefile, record_q, ts_us=None, chunk_size=None):
		"""
		PURPOSE: creates a new Replayer
		ARGS:
			savefile (str): the .mat file containing the saved data
			record_q (Queue): the queue to put the chunks in
			ts_us (int): the sampling period (microseconds), if left as None it 
				uses the value in the save file
			chunk_size (int): the number of samples in one chunk, if left as 
				None it uses the value in the save file
		RETURNS: new instance of a replayer
		NOTES:
		"""
		#Save arguments and load file
		self.record_q = record_q
		self.savefile = savefile
		saved_data = loadmat(savefile)
		self.ts_us = saved_data['ts_us'][0][0]
		self.chunk_size = saved_data['chunk_size'][0][0]
		self.data = saved_data['data'][0]
		if ts_us != None:
			self.ts_us = ts_us
		if chunk_size != None:
			self.chunk_size = chunk_size

		#Setup thread variables
		self.replay_thread = None
		self.replay_keep_going = threading.Event()
		self.replay_keep_going.clear()

		#Compute variables used to chunk the data
		self.num_chunks = int(math.floor(self.data.shape[0] / self.chunk_size))
		if self.num_chunks == 0:
			raise ValueError("Chunk size is too large for the given recorded data")
		self.chunk_time = self.ts_us / 1e6 * self.chunk_size

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
		if self.replay_thread == None or not self.is_running():
			self.replay_thread = threading.Thread(target = self.run)
			self.replay_thread.start()

	############################################################################
	def stop(self):
		"""
		PURPOSE: stops the thread
		ARGS: none
		RETURNS: none
		NOTES: blocks until thread stops
		"""
		if self.replay_thread:
			self.replay_keep_going.clear()
			self.replay_thread.join()
			self.replay_thread = None

	############################################################################
	def is_running(self):
		"""
		PURPOSE: checks if the thread is running
		ARGS: none
		RETURNS: True if running, False if stopped
		NOTES:
		"""
		return self.replay_keep_going.is_set()

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
			"connected" : True,
			"receiving_data" : True
		}
		return status

	############################################################################
	def run(self):
		"""
		PURPOSE: does the actual replaying
		ARGS: none
		RETURNS: none
		NOTES: calling 'start' will run this in a separate thread
		"""
		#Indicate thread is running
		self.replay_keep_going.set()

		try:
			#Run until told to stop
			ii = 0
			prev_time = time.time() - 1
			while self.is_running():
				cur_time = time.time()
				if (cur_time - prev_time) >= self.chunk_time:
					chunk = self.data[self.chunk_size*ii:self.chunk_size*(ii+1)]
					self.record_q.put(chunk)
					ii += 1
					if ii >= self.num_chunks:
						ii = 0
					prev_time = cur_time
				time.sleep(0.1)
		except Exception as e:
			print("ERROR: 'replay thread' got exception %s" % type(e))
			print(e)
			self.replay_keep_going.clear()

	############################################################################

################################################################################
if __name__ == "__main__":
	savefile = "C:\\Users\\rga0230\\Downloads\\test_recorder.mat"
	record_q = queue.Queue()

	replayer = Replayer(savefile, record_q)

	start_time = int(time.time())
	replayer.start()

	try:
		while replayer.is_running():
			time.sleep(1)
			elapsed_time = int(time.time()) - start_time
			qs = record_q.qsize()
			chunk_rate = qs / elapsed_time
			print("Time = %d, Queue Size = %d, Chunk Rate = %.2f" % (elapsed_time, qs, chunk_rate))
	except KeyboardInterrupt as e:
		pass

	replayer.stop()