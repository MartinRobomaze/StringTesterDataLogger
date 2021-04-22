import tkinter as tk
import numpy as np
import threading
from time import time, sleep
from tkinter import messagebox

from picosdk.ps2000 import ps2000 as ps
from picosdk.functions import assert_pico2000_ok
from scipy.signal import chirp
import serial
import serial.tools.list_ports as serial_ports_list
import ctypes
import simpleaudio as sa


state_measuring_format = 'Measuring, current frequency: {} Hz'


def setup_scope(start_freq, end_freq, freq_res, sweep_time, dwell_time):
    status = {}

    status["openUnit"] = ps.ps2000_open_unit()
    assert_pico2000_ok(status["openUnit"])

    # Create chandle for use
    chandle = ctypes.c_int16(status["openUnit"])

    sweep_type = 0

    if start_freq > end_freq:
        sweep_type = 1

    status["sigGen"] = ps.ps2000_set_sig_gen_built_in(
        chandle,
        1 * 10 ** 6,
        2 * 10 ** 6,
        1,
        start_freq,
        end_freq,
        freq_res,
        dwell_time,
        sweep_type,
        1
    )
    assert_pico2000_ok(status["sigGen"])

    status["runStreaming"] = ps.ps2000_run_streaming(chandle, 5, 1000, 0)
    assert_pico2000_ok(status["runStreaming"])

    return chandle


def generate_audio(start_freq, end_freq, sweep_time, resolution=0):
    # Generate times at which to generate the waveform.
    t = np.arange(0, int(sweep_time * 44100)) / 44100

    wave = np.zeros(int(44100 * sweep_time))

    if resolution == 0:
        # Generate linear frequency sweep.
        wave = chirp(t, f0=start_freq / 2, f1=end_freq / 2, t1=sweep_time, method='linear')
    else:
        i = 0
        for f in np.arange(start_freq, end_freq, resolution):
            duration = 44100 * (sweep_time / abs(start_freq - end_freq)) * resolution
            wave[:int(i * duration)] = (np.sin(2 * np.pi * np.arange(duration) * f / 44100)).astype(np.float32)
            i += 1

    print(len(wave))
    # Convert wave to wav.
    audio = wave * (2 ** 15 - 1) / np.max(np.abs(wave))
    audio = audio.astype(np.int16)

    return audio


def stop_scope(sweep_time, scope_handle):
    sleep(sweep_time + 0.1)
    status = {}
    status["stop"] = ps.ps2000_stop(scope_handle)
    assert_pico2000_ok(status["stop"])

    # Close unitDisconnect the scope
    # handle = chandle
    status["close"] = ps.ps2000_close_unit(scope_handle)
    assert_pico2000_ok(status["close"])


def start_audio(audio):
    print('playing')
    sa.play_buffer(audio, 1, 2, 44100)


def logger(ser: serial.Serial, file_name, start_freq, end_freq, sweep_time, dwell_time, freq_res):
    data = [['time', 'x_val', 'y_val', 'frequency']]
    start_time = time()

    change_time = start_time
    freq = start_freq

    while time() - start_time < sweep_time:
        try:
            # Get message from arduino.
            message = str(ser.readline().decode("utf-8"))

            val_x, val_y = [int(x) for x in message.strip().split(",")]
        except Exception as e:
            print(e)
            continue

        data_time = time() - start_time

        if time() - change_time >= dwell_time:
            change_time = time()
            if end_freq > start_freq:
                freq += freq_res
            else:
                freq -= freq_res

        # Calculate current from raw signal value.
        voltage_x = val_x * (5 / 1023)
        current_x = voltage_x / 100
        voltage_y = val_y * (5 / 1023)
        current_y = voltage_y / 100

        data.append([data_time, current_x, current_y, freq])
        # Display measured frequency.
        current_state.config(text=state_measuring_format.format(round(freq, 5)))

        sleep(0.00001)

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
        freq_res = float(freq_res_input.get())
        file_name = file_name_input.get()
    except ValueError:
        messagebox.showerror("ValueError", "You didn't enter/entered wrong value to some field... Try again")
        return

    # Try to open serial port.
    current_state.config(text="Connecting to Arduino...")
    try:
        ser = serial.Serial(port=serial_port, baudrate=1000000)
    except serial.SerialException:
        messagebox.showerror("Cannot connect to device", "Cannot connect to device, "
                                                         "try again with different serial port.")
        return

    # Write message to Arduino to start sending data.
    print(('{}\r\n'.format(freq_res)).encode('utf-8'))
    ser.write(('{}\r\n'.format(freq_res)).encode('utf-8'))

    current_state.config(text="Start")

    # audio = generate_audio(start_freq, end_freq, sweep_time, freq_res)

    try:
        dwell_time = sweep_time / (abs(start_freq - end_freq) / freq_res)
    except ZeroDivisionError:
        dwell_time = sweep_time

    scope_handle = setup_scope(start_freq, end_freq, freq_res, sweep_time, dwell_time)

    # Start data logger thread.
    logger_thread = threading.Thread(target=logger, args=(ser, file_name, start_freq, end_freq,
                                                          sweep_time, dwell_time, freq_res), daemon=True)
    sig_gen_thread = threading.Thread(target=stop_scope, args=(sweep_time, scope_handle))

    sig_gen_thread.start()
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
tk.Label(root, text='Frequency resolution:').grid(row=5)
freq_res_input = tk.Entry(root)
freq_res_input.grid(row=5, column=1)

tk.Button(root, text='Start measurement', command=measure).grid(row=6)

# Current state placeholder label.
current_state = tk.Label(root)
current_state.grid(row=7)

root.mainloop()
