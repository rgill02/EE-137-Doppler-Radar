# EE-137-Doppler-Radar
A doppler radar for measuring the speed of a vehicle for the Tufts Radar Engineering Class

## Project Description
* Using HB100 Module, build a radar (speed gun) to measure a speed of normal size vehicle.
* The radar should have accuracy of at least of ±5 mph.
* The radar should have a user friendly interface (GUI).
* The radar should use radar signal processing to be able to accurately measure the speed of the vehicle.
* [Optional for extra credit] the radar should be able to measure distance with accuracy of ±10 meters.

## Radar Hardware
We are using the HB-100 doppler radar module for our radar. It is an X-Band monostatic doppler transceiver. The board housing the electronics also contains two sets of patch antennas, one for transmitting and the other for receiving. +5 V powers a an oscillator that generates a 10.525 GHz tone. This signal is split and half of it goes to the transmit antenna to be transmitted at the target. The other half goes to the LO port of a mixer, whose RF port is connected to the receive antenna. The reflected signal off the target is received by the receive antenna, and is then mixed with the original signal down to baseband. The IF signal is then output at the IF terminal on the radar module.