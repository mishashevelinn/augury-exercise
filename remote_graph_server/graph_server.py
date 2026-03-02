#!/usr/bin/env python
from flask import Flask, Response
import matplotlib.pyplot as plt
import ctypes
import mmap
import time
import io
import os

MAX_SAMPLES = 16384
FRAME_DELAY = 0.25

SAMPLE_TYPE = ctypes.c_int8


class SharedMemStruct(ctypes.Structure):
    _fields_ = [
        ("max_samples", ctypes.c_int),  # int max_samples;
        ("sample_freq", ctypes.c_int),  # int sample_freq;
        ("next_sample", ctypes.c_int),  # int next_sample;
        ("total_samples", ctypes.c_int),  # int total_samples;
        ("sample_array", SAMPLE_TYPE * MAX_SAMPLES)]  # short sample_array;


app = Flask(__name__)


class SharedMem:
    SHARED_FNAME = "/tmp/shmem_data";

    def __init__(self, init_data=True):
        self.struct_size = ctypes.sizeof(SharedMemStruct)
        self.header_size = self.struct_size - MAX_SAMPLES * ctypes.sizeof(SAMPLE_TYPE)

        if init_data:
            f = open(self.SHARED_FNAME, 'w+')
            f.truncate(ctypes.sizeof(SharedMemStruct))
            f.close()
            os.chmod(self.SHARED_FNAME, 0o666)

        self.file = open(self.SHARED_FNAME, 'r+b')
        self.buffer = mmap.mmap(self.file.fileno(), 0)
        self.struct = SharedMemStruct.from_buffer(self.buffer)

        if init_data:
            self.struct.max_samples = MAX_SAMPLES
            self.struct.next_sample = 0

        self.last_header = None

    def header_changed(self):
        '''
        Check if the struct header has changed since last check
        '''
        curr_header = repr(self.buffer[:self.header_size])
        if curr_header == self.last_header:
            return False

        self.last_header = curr_header
        return True

    def __del__(self):
        self.buffer.close()
        self.file.close()


_G_SHMEM = SharedMem()


@app.route('/')
def index():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


def get_frame():
    force_one_draw = True
    while True:
        time.sleep(FRAME_DELAY)
        if not force_one_draw:
            while not _G_SHMEM.header_changed():
                time.sleep(FRAME_DELAY)

            force_one_draw = True  # Force one extra draw at the end

        else:
            force_one_draw = False

        img_string_data = get_graph_image_bytes()
        yield (b'--frame\r\n'
               b'Content-Type: text/plain\r\n\r\n' + img_string_data + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


def get_graph_image_bytes():
    data = _G_SHMEM.struct

    fig = plt.figure()
    fig.suptitle("Real time sample plot")
    fig_plt = fig.add_subplot()
    total_samples = data.total_samples
    next_sample = data.next_sample
    print(next_sample, total_samples)
    if next_sample or total_samples:
        blanks = [] if total_samples < next_sample \
            else [None] * (total_samples - next_sample - 1)
        if blanks:
            blanks.append(0)  # must for showing anything

        fig_plt.plot(data.sample_array[:next_sample] + blanks, '-bD', c='blue', markerfacecolor='red',
                     markeredgecolor='k', ms=3)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)

    buf.seek(0)
    return buf.read()


def main():
    host = '0.0.0.0'
    app.run(host=host, debug=False, threaded=True)


if __name__ == '__main__':
    os.nice(20)
    main()
