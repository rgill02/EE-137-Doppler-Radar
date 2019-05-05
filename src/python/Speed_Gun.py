#Imports
from PyQt5 import QtCore, QtGui, QtWidgets
from mplwidget import MplWidget
from UI import Ui_MainWindow
import sys
import threading
import queue
import time
from Chunked_Arduino_ADC_2 import Chunked_Arduino_ADC
from Replayer_2 import Replayer
from Processor import Processor
from Chunk_Saver import Chunk_Saver

################################################################################
class Speed_Gun:
	"""
	Main controller class for the Speed Gun application
	"""
	def __init__(self, samp_T_us, cpi_samps, savefile, emulate=False):
		"""
		PURPOSE: creates a new Speed_Gun
		ARGS: 
			samp_T_us (float): sampling period in microseconds
			cpi_samps (int): number of samples in one cpi
			emulate (bool): if True loads pre-recorded data, if False runs for 
				real
			savefile (str): the file to save to
		RETURNS: new instance of a Speed_Gun
		NOTES:
		"""
		#Save arguments
		self.samp_T_us = samp_T_us
		self.fs = 1e6 / samp_T_us
		self.cpi_samps = cpi_samps
		self.emulate = emulate
		self.savefile = savefile

		#Setup app
		self.app = QtWidgets.QApplication(sys.argv)
		self.main_win = QtWidgets.QMainWindow()
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self.main_win)

		#Initialize UI values
		self.init_ui_values()

		#Connect buttons
		self.ui.run_button.clicked.connect(self.run_button_clicked)
		self.ui.stop_button.clicked.connect(self.stop_button_clicked)
		self.ui.vel_radbutton.toggled.connect(self.rad_button_toggled)
		self.ui.raw_sig_radbutton.toggled.connect(self.rad_button_toggled)

		#Setup queues
		self.record_q = queue.Queue()
		self.res_q = queue.Queue()
		self.save_q = queue.Queue()

		#Setup other modules
		#Setup recorder.replayer
		if emulate:
			self.recorder = Replayer("C:\\Users\\rga0230\\Documents\\School\\EE-137\\EE-137-Doppler-Radar\\data\\car.mat", [self.record_q, self.save_q], ts_us=samp_T_us, chunk_size=cpi_samps)
		else:
			self.recorder = Chunked_Arduino_ADC(samp_T_us, cpi_samps, [self.record_q, self.save_q])
		#Setup processor
		self.proc = Processor(samp_T_us, cpi_samps, self.record_q, self.res_q)
		#Setup saver
		self.saver = Chunk_Saver(savefile, samp_T_us, cpi_samps, self.save_q)

		#Setup variables for our update thread
		self.update_thread = threading.Thread(target = self.update_thread_run)
		self.update_keep_going = threading.Event()
		self.update_keep_going.set()

	############################################################################
	def run_app(self):
		"""
		PURPOSE: runs the GUI application
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		#Start update thread
		self.update_thread.start()

		#Run GUI
		self.main_win.show()
		rc = self.app.exec_()

		#Join update thread
		self.update_keep_going.clear()
		self.update_thread.join()
		self.update_thread = None

		#Return GUI exit code
		return rc

	############################################################################
	def init_ui_values(self):
		"""
		PURPOSE: initializes all of the ui input and output fields
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		self.ui.samp_freq_lbl.setText("%.2f" % (self.fs / 1e3))
		self.ui.cpi_lbl.setText(str(int(self.cpi_samps / self.fs * 1e3)))
		self.ui.ard_con_lbl.setText("No")
		self.ui.recv_data_lbl.setText("No")
		self.ui.run_lbl.setText("No")
		self.ui.cpi_num_lbl.setText("")
		self.ui.eng_lbl.setText("")
		self.ui.detc_lbl.setText("")
		self.ui.vel_lbl.setText("")
		self.ui.stop_button.setEnabled(False)
		self.ui.vel_radbutton.setChecked(True)

	############################################################################
	def rad_button_toggled(self):
		if self.ui.vel_radbutton.isChecked():
			self.proc.to_plot = "freq"
			self.proc.setup_res_dict()
		else:
			self.proc.to_plot = "raw"
			self.proc.setup_res_dict()

	############################################################################
	def run_button_clicked(self):
		"""
		PURPOSE: runs when the load/run button is clicked
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		self.ui.run_button.setEnabled(False)
		self.ui.stop_button.setEnabled(True)

		self.recorder.start()
		self.proc.start()

	############################################################################
	def stop_button_clicked(self):
		"""
		PURPOSE: runs when the stop button is clicked
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		#Stop threads
		self.recorder.stop()
		self.proc.stop()

		self.ui.run_button.setEnabled(True)
		self.ui.stop_button.setEnabled(False)

	############################################################################
	def update_thread_run(self):
		"""
		PURPOSE: constantly updates the output values on the GUI
		ARGS: none
		RETURNS: none
		NOTES:
		"""
		#Indicate thread is running
		self.update_keep_going.set()
		self.saver.start()

		try:
			#Run until we are told to stop
			prev_thread_poll_time = 0
			prev_res_time = 0
			while self.update_keep_going.is_set():
				cur_time = time.time()
				if (cur_time - prev_thread_poll_time) >= 1:
					rec_status = self.recorder.get_status()
					proc_status = self.proc.get_status()
					rec_running = rec_status.get("running", False)
					proc_running = proc_status.get("running", False)
					if rec_running and proc_running:
						ard_con = rec_status.get("connected", False)
						recv_data = rec_status.get("receiving_data", False)
						if recv_data and ard_con:
							self.ui.recv_data_lbl.setText("Yes")
						else:
							self.ui.recv_data_lbl.setText("No")
						if ard_con:
							self.ui.ard_con_lbl.setText("Yes")
						else:
							self.ui.ard_con_lbl.setText("No")
						self.ui.run_lbl.setText("Yes")
					else:
						self.ui.ard_con_lbl.setText("No")
						self.ui.recv_data_lbl.setText("No")
						self.ui.run_lbl.setText("No")
						if proc_running != rec_running:
							self.stop_button_clicked()
					prev_thread_poll_time = cur_time
				if (cur_time - prev_res_time) >= 0.1:
					try:
						sig = self.res_q.get(timeout=0.1)
						ax = self.ui.disp_plot.canvas.ax
						ax.clear()
						ax.plot(sig["x"], sig["y"])
						ax.set_xlabel(sig["xlabel"])
						ax.set_ylabel(sig["ylabel"])
						ax.set_title(sig["title"])
						ax.set_xlim(sig["xlim"][0], sig["xlim"][1])
						ax.set_ylim(sig["ylim"][0], sig["ylim"][1])
						self.ui.disp_plot.canvas.draw()
						self.ui.cpi_num_lbl.setText(str(sig["cpi_num"]))
						self.ui.eng_lbl.setText("%.4f" % (sig["eng"]))
						self.ui.detc_lbl.setText(str(sig["detc"]))
						self.ui.vel_lbl.setText("%.2f" % sig["vel"])
					except queue.Empty as e:
						pass
					prev_res_time = cur_time
				time.sleep(0.1)
		except Exception as e:
			print("ERROR: 'update_thread' got exception %s" % type(e))
			print(e)
			self.update_keep_going.clear()

		#Cleanup
		self.recorder.stop()
		self.proc.stop()
		self.saver.stop()

	############################################################################

################################################################################
if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Speed Gun")
	parser.add_argument("savefile", type=str, help="File to save to")
	parser.add_argument("-e", "--emulate", help="Emulate recording", action="store_true", default=False)
	args = parser.parse_args()

	speed_gun = Speed_Gun(200, 2500, args.savefile, emulate=args.emulate)
	speed_gun.run_app()
