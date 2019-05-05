#Imports
import serial
import serial.tools.list_ports as list_ports
import threading
import queue
import numpy as np
import struct

################################################################################
class Chunked_Arduino_ADC:
	"""
	Reads values from the arduino and writes them to a queue
	"""
	def __init__(self, ts_us, chunk_size, record_qs, ser_port=None):
		"""
		PURPOSE: creates a new Chunked_Arduino_ADC
		ARGS:
			ts_us (int): sampling period of arduino (microseconds)
			chunk_size (int): number of samples to expect in one chunk
			record_qs (list): queues to push chunks to
			ser_port (str): serial port to listen on, will try to find arduino 
				if left as None
		RETURNS: new instance of an Chunked_Arduino_ADC
		NOTES:
		"""
		#Save arguments
		self.ts_us = int(ts_us)
		self.chunk_size = int(chunk_size)
		self.record_qs = record_qs
		self.ser_timeout = self.chunk_size * self.ts_us / 1e6 * 2.5
		self.ser_port = ser_port

		#Setup record thread variables
		self.record_thread = None
		self.record_keep_going = threading.Event()
		self.record_keep_going.clear()

		#Status variables
		self.connected = False
		self.receiving_data = False

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
		PURPOSE: starts the recording thread
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		if self.record_thread == None or not self.is_running():
			self.record_thread = threading.Thread(target = self.run)
			self.record_thread.start()

	############################################################################
	def stop(self):
		"""
		PURPOSE: stops the recording thread
		ARGS: none
		RETURNS: none
		NOTES: blocks until thread stops
		"""
		if self.record_thread:
			self.record_keep_going.clear()
			self.record_thread.join()
			self.record_thread = None

	############################################################################
	def is_running(self):
		"""
		PURPOSE: checks if the recording thread is running
		ARGS: none
		RETURNS: True if running, False if stopped
		NOTES:
		"""
		return self.record_keep_going.is_set()

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
			"connected" : self.connected,
			"receiving_data" : self.receiving_data
		}
		return status

	############################################################################
	def run(self):
		"""
		PURPOSE: performs the recording
		ARGS: none
		RETURNS: none
		NOTES: calling 'start' runs this in a separate thread
		"""
		#Indicate thread is running
		self.record_keep_going.set()

		sh = None
		try:
			#Run until told to stop
			while self.is_running():
				#Connect to arduino
				while self.is_running() and not self.connected:
					try:
						if self.ser_port:
							ser_port = self.ser_port
						else:
							ser_port = None
							ports = list_ports.comports()
							for port in ports:
								if port[1].find("Arduino Mega 2560") >= 0:
									ser_port = port[0]
									break
						sh = serial.Serial(ser_port, 115200, timeout=self.ser_timeout)
						if sh and not sh.isOpen():
							sh.close()
							sh = None
							self.connected = False
							self.receiving_data = False
						else:
							self.connected = True
					except serial.serialutil.SerialException as e:
						if sh:
							sh.close()
						sh = None
						self.connected = False
						self.receiving_data = False
				#We are now connected to the arduino so reset cur idx
				cur_idx = 0
				#Record from arduino
				while self.is_running() and self.connected:
					try:
						sync_count = 0
						while sync_count < 2:
							data = sh.read(1)
							if len(data):
								if data[0] == 255:
									sync_count += 1
								else:
									sync_count = 0
						data = sh.read(self.chunk_size * 2)
						sample_chunk = np.array(struct.unpack('<%dH' % self.chunk_size, data))
						to_put = sample_chunk / 1023 * 5
						for record_q in self.record_qs:
							record_q.put(to_put)
						self.receiving_data = True
					except (serial.serialutil.SerialException, struct.error) as e:
						self.receiving_data = False
						if not sh.isOpen():
							sh.close()
							sh = None
						self.connected = False
		except Exception as e:
			print("ERROR: 'recorder thread' got exception %s" % type(e))
			print(e)
			self.record_keep_going.clear()

		#Cleanup
		if sh:
			sh.close()
			sh = None
			self.connected = False
			self.receiving_data = False

	############################################################################

################################################################################
if __name__ == "__main__":
	import time
	import matplotlib.pyplot as plt

	record_q = queue.Queue()
	record_q2 = queue.Queue()
	recorder = Chunked_Arduino_ADC(200, 2500, [record_q, record_q2])

	recorder.start()

	try:
		while recorder.is_running():
			time.sleep(1)
			print(recorder.get_status())
	except KeyboardInterrupt as e:
		pass

	recorder.stop()