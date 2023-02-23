import picoscope
import numpy as np
from scipy.signal import chirp

import h5py
import matplotlib.pyplot as plt
import simpleaudio


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


string_diameter = float(input('String diameter[mm]: '))
string_tension = float(input('String tension[N]: '))
string_length = float(input('String length[cm]: '))

freq_start = float(input('Start frequency[Hz]: '))
freq_end = float(input('End frequency[Hz]: '))

freq_res_str = input('Frequency resolution[0.1Hz]: ')
freq_res = float(freq_res_str) if freq_res_str != '' else 0.1

sweep_time = int(input('Sweep time[s]: '))

data_filename = input('Filename[exp_db.hdf5]: ')
data_filename = 'exp_db.hdf5' if data_filename == '' else data_filename

picoscope_for_driving_prompt = input('Use picoscope[p] or sound card[s] for generating driving wave[p]: ')
picoscope_for_driving = picoscope_for_driving_prompt == 'p' or picoscope_for_driving_prompt == ''

print('Connecting to picoscope')

scope = picoscope.Picoscope(potential_range=picoscope.PotentialRange.PS2000_5V)

print('Starting measurement')

if picoscope_for_driving:
    try:
        dwell_time = sweep_time / (abs(freq_start - freq_end) / freq_res)
    except ZeroDivisionError:
        dwell_time = sweep_time

    scope.setup_sig_gen(freq_start, freq_end, freq_res, dwell_time)
else:
    wave = generate_audio(freq_start, freq_end, sweep_time)
    simpleaudio.WaveObject(wave).play()

scope.setup_streaming(10 ** 3 * sweep_time, 10 ** 3)

values_A, values_B = scope.gather()
scope.close()

print('Measurement done')

print("Saving to '{}'".format(data_filename))
f = h5py.File(data_filename, 'a')

if str(string_diameter) not in f.keys():
    f.create_group(str(string_diameter))
if str(string_tension) not in f[str(string_diameter)].keys():
    f[str(string_diameter)].create_group(str(string_tension))
if str(string_length) not in f["/{}/{}".format(string_diameter, string_tension)].keys():
    f["/{}/{}".format(string_diameter, string_tension)].create_group(str(string_length))

labels_list = ['time', 'freq', 'x', 'y']

data_type = np.dtype({'names': labels_list, 'formats': [float] * 4})
time_total = (scope.end_time - scope.start_time) / 10 ** 9
times = np.linspace(0, time_total, len(values_A))

if picoscope_for_driving:
    time_d_freq = time_total / ((freq_end - freq_start) / freq_res)
    frequencies = np.zeros(len(times))
    freq = freq_start
    t_change = 0
    for i, t in enumerate(times):
        if t - t_change >= time_d_freq:
            freq += freq_res
            t_change = t
        frequencies[i] = freq
else:
    f_t = lambda t: (freq_end - freq_start) / time_total * t + freq_start

    frequencies = f_t(times)

data = np.rec.fromarrays([times, frequencies, values_A, values_B], dtype=data_type)

data_grp = f["/{}/{}/{}".format(string_diameter, string_tension, string_length)]

print('Compressing...')
data_grp.create_dataset(
    '{}Hz-{}Hz'.format(freq_start, freq_end),
    len(times),
    data=data,
    compression='gzip',
    compression_opts=9
)

f.close()
print('Data saved')
