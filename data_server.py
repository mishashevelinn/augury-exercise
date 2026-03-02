#!/usr/bin/env python3
"""
VM-side data API server. Reads from /tmp/shmem_data (same layout as graph_server)
and exposes HTTP API for remote clients to fetch current sample data.
Does not modify graph_webserver or samples_reader.
"""
from flask import Flask, jsonify
import ctypes
import mmap
import os

MAX_SAMPLES = 16384
SHARED_FNAME = "/tmp/shmem_data"
SAMPLE_TYPE = ctypes.c_int8


class SharedMemStruct(ctypes.Structure):
    _fields_ = [
        ("max_samples", ctypes.c_int),
        ("sample_freq", ctypes.c_int),
        ("next_sample", ctypes.c_int),
        ("total_samples", ctypes.c_int),
        ("sample_array", SAMPLE_TYPE * MAX_SAMPLES),
    ]


def open_shmem():
    """Open /tmp/shmem_data, creating it with correct size if missing."""
    struct_size = ctypes.sizeof(SharedMemStruct)
    if not os.path.exists(SHARED_FNAME):
        with open(SHARED_FNAME, "w+") as f:
            f.truncate(struct_size)
        os.chmod(SHARED_FNAME, 0o666)
    f = open(SHARED_FNAME, "r+b")
    buf = mmap.mmap(f.fileno(), 0)
    struct = SharedMemStruct.from_buffer(buf)
    return f, buf, struct


app = Flask(__name__)

# One shared-mem view per process; struct fields reflect current data on each read
_shmem_file = None
_shmem_buf = None
_shmem_struct = None


def get_shmem():
    global _shmem_file, _shmem_buf, _shmem_struct
    if _shmem_struct is None:
        _shmem_file, _shmem_buf, _shmem_struct = open_shmem()
    return _shmem_struct


@app.route("/samples")
def samples():
    """Return current sample data as JSON for remote clients (e.g. local machine)."""
    try:
        s = get_shmem()
    except FileNotFoundError:
        return jsonify(error="shared memory file not found", path=SHARED_FNAME), 503
    except Exception as e:
        return jsonify(error=str(e) + " " + str(e.__traceback__.tb_frame.f_code.co_filename) + " " + str(e.__traceback__.tb_frame.f_code.co_name) + " " + str(e.__traceback__.tb_frame.f_code.co_firstlineno)), 503

    next_sample = s.next_sample
    total_samples = s.total_samples
    sample_list = list(s.sample_array[:next_sample]) if next_sample else []

    return jsonify(
        max_samples=s.max_samples,
        sample_freq=s.sample_freq,
        next_sample=next_sample,
        total_samples=total_samples,
        samples=sample_list,
    )


@app.route("/health")
def health():
    """Simple health check."""
    return jsonify(status="ok")


@app.after_request
def cors_headers(response):
    """Allow browsers on other hosts (e.g. local machine) to call this API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def main():
    host = "0.0.0.0"
    port = 5001
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()