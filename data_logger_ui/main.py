import tkinter as tk
import numpy as np
import threading
from time import time
from tkinter import messagebox
from scipy.signal import chirp
import serial
import serial.tools.list_ports as serial_ports_list
import simpleaudio as sa


state_measuring_format = 'Measuring, current frequency: {} Hz'


def start_audio(start_freq, end_freq, sweep_time):
    # Generate times at which to generate the waveform.
    t = np.arange(0, int(sweep_time * 44100)) / 44100

    # Generate linear frequency sweep.
    wave = chirp(t, f0=start_freq / 2, f1=end_freq / 2, t1=sweep_time, method='linear')

    # Convert wave to wav.
    audio = wave * (2 ** 15 - 1) / np.max(np.abs(wave))
    audio = audio.astype(np.int16)

    # Play the wave.
    sa.play_buffer(audio, 1, 2, 44100)


def logger(ser: serial.Serial, sample_rate, file_name, start_freq, end_freq, sweep_time):
    data = [['time', 'y_val', 'frequency']]
    start_time = time()

    # Write message to Arduino to start sending data.
    ser.write(('{}\r\n'.format(sample_rate)).encode('utf-8'))

    while time() - start_time < sweep_time:
        try:
            # Get message from arduino.
            message = str(ser.readline().decode("utf-8"))

            # Strip message and convert it to number.
            val_y = int(message.strip())
        except Exception:
            continue

        data_time = time() - start_time

        # Calculate current output frequency -
        # calculation from scipy docs(https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.chirp.html).
        freq = start_freq + (end_freq - start_freq) * data_time / sweep_time

        # Calculate current from raw signal value.
        voltage_y = val_y * (5 / 1023)
        current_y = voltage_y / 100

        data.append([data_time, current_y, freq])
        # Display measured frequency.
        current_state.config(text=state_measuring_format.format(round(freq, 5)))

    ser.close()

    # Write measured data to file.
    with open(file_name, mode='w') as out:
        output_string = ''

        for row in data:
            row_string = ','.join(str(x) for x in row)
            output_string += '{}\n'.format(row_string)

        out.write(output_string)


def measure():
    # Get all input values.
    try:
        start_freq = float(start_freq_input.get())
        end_freq = float(end_freq_input.get())

        sweep_time = float(sweep_time_input.get())

        serial_port = serial_port_selected.get()
        sample_rate = int(sample_rate_input.get())
        file_name = file_name_input.get()
    except ValueError:
        messagebox.showerror("ValueError", "You didn't enter/entered wrong value to some field... Try again")
        return

    # Try to open serial port.
    try:
        ser = serial.Serial(port=serial_port, baudrate=115200)
    except serial.SerialException:
        messagebox.showerror("Cannot connect to device", "Cannot connect to device, "
                                                         "try again with different serial port.")
        return

    # Start audio output thread.
    audio_thread = threading.Thread(target=start_audio, args=(start_freq, end_freq, sweep_time,), daemon=True)
    audio_thread.start()

    # Start data logger thread.
    logger_thread = threading.Thread(target=logger, args=(ser, sample_rate, file_name, start_freq, end_freq,
                                                          sweep_time,), daemon=True)
    logger_thread.start()


# Get all connected serial ports.
ports_list = [port[0] for port in serial_ports_list.comports()]

root = tk.Tk()

serial_port_selected = tk.StringVar(root)

# Frequency range input.
tk.Label(root, text='Frequency range(Hz):').grid(row=1)
start_freq_input = tk.Entry(root)
start_freq_input.grid(row=1, column=1)
end_freq_input = tk.Entry(root)
end_freq_input.grid(row=1, column=2)

# Sweep time input.
tk.Label(root, text='Sweep time(sec):').grid(row=2)
sweep_time_input = tk.Entry(root)
sweep_time_input.grid(row=2, column=1)

# Check if there are any serial ports available.
if len(ports_list) != 0:
    # Serial port selection.
    tk.Label(root, text='Serial port:').grid(row=3)
    serial_port_opt = tk.OptionMenu(root, serial_port_selected, *ports_list).grid(row=3, column=1)
else:
    messagebox.showwarning("No device connected", "No device connected. Restart with connected device "
                                                  "to start measuring.")

# Output filename input.
tk.Label(root, text='Output file name:').grid(row=4)
file_name_input = tk.Entry(root)
file_name_input.grid(row=4, column=1)

# Sample rate input.
tk.Label(root, text='Sample rate(samples/sec):').grid(row=5)
sample_rate_input = tk.Entry(root)
sample_rate_input.grid(row=5, column=1)

tk.Button(root, text='Start measurement', command=measure).grid(row=6)

# Current state placeholder label.
current_state = tk.Label(root)
current_state.grid(row=7)

root.mainloop()
