# StringTesterDataLogger
Data logger for string tester.  
# data_logger
Arduino code that reads optical sensor data and sends them via serial link.  
The code needs to run on Atmega328p processor - low level register reading/writing is used. To change board to other atmega328p arduino board, go to `platformio.ini` and set `board` flag to specified board.  
Serial communication speed is 115200 bps. You can change it in `main.cpp`  
# data_logger_ui
Python program that outputs frequency sweep waveform and collects data from Arduino data logger.  
Note: it requires Python3 to run.
## Dependencies
`pip3 install numpy scipy pyserial simpleaudio`  
Note: If you are installing on Linux, install `libasound2-dev` using your package manager for simpleaudio to build correctly.
## Executing
### Linux & Mac OSX
`cd data_logger_ui/ && python main.py`
