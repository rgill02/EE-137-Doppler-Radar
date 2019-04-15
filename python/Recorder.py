#Imports
import queue
import Chunked_Arduino_ADC
import Chunk_Saver
import time

################################################################################
class Recorder:
	"""
	Records values coming from the arduino to a matlab file
	"""
	def __init__(self):
		"""
		PURPOSE: creates a new Recorder
		ARGS: none
		RETURNS: new instance of a Recorder
		NOTES:
		"""
		pass

	############################################################################
	def record(self, savefile, ts_us=200, chunk_size=2500, ser_port=None):
		"""
		PURPOSE: records data to matlab file
		ARGS:
			savefile (str): .mat file to save to
			ts_us (int): the sample period in microseconds
			chunk_size (int): the size of the chunks the arduino is sending
			ser_port (str): the serial port to listen on  (will search on its 
				own if its None)
		RETURNS: none
		NOTES:
		"""
		record_q = queue.Queue()
		adc = Chunked_Arduino_ADC.Chunked_Arduino_ADC(ts_us, chunk_size, record_q, ser_port)
		saver = Chunk_Saver.Chunk_Saver(savefile, ts_us, chunk_size, record_q)

		print("Starting recorder...")

		#Start threads
		adc.start()
		saver.start()

		print("Recorder started!")
		print("Use 'ctrl-c' to stop!")

		#Monitor threads
		try:
			while True:
				adc_status = adc.get_status()
				saver_status = saver.get_status()
				print("-------------------------")
				print("ADC Connected = %s" % bool(adc_status["connected"]))
				print("ADC Receiving Data = %s" % bool(adc_status["receiving_data"]))
				print("Chunk Count = %d" % saver_status["chunk_count"])
				print("-------------------------")
				if not adc_status["running"]:
					print("ERROR: ADC stopped unexpectedly!")
					break
				if not saver_status["running"]:
					print("ERROR: Saver stopped unexpectedly!")
					break
				time.sleep(1)
		except KeyboardInterrupt as e:
			pass

		print("Stopping recorder...")

		#Stop threads
		adc.stop()
		saver.stop()

		print("Recorder stopped!")

	############################################################################

################################################################################
if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Recorder")
	parser.add_argument("savefile", type=str, help=".mat file to save data to")
	parser.add_argument("-t", "--ts_us", type=int, help="Sampling period (us)", default=200)
	parser.add_argument("-c", "--chunk_size", type=int, help="Samples per chunk", default=2500)
	parser.add_argument("-s", "--ser_port", type=str, help="Serial port to listen on", default=None)
	args = parser.parse_args()

	recorder = Recorder()
	recorder.record(args.savefile, args.ts_us, args.chunk_size, args.ser_port)