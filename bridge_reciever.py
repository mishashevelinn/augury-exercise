#!/usr/bin/env python3
"""
Local client: fetches /samples from VM (localhost:5001 via SSH tunnel),
writes into local /tmp/shmem_data so graph_server.py can run locally and plot.
"""
import ctypes
import os
import time
import urllib.request
import json

# Same layout as graph_server.py SharedMemStruct
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


def ensure_shmem_file():
    """Create or truncate local shared memory file to the right size."""
    struct_size = ctypes.sizeof(SharedMemStruct)
    with open(SHARED_FNAME, "wb") as f:
        f.truncate(struct_size)
    os.chmod(SHARED_FNAME, 0o666)


def write_snapshot(data: dict):
    """Write API response into local /tmp/shmem_data (binary layout for graph_server)."""
    struct_size = ctypes.sizeof(SharedMemStruct)
    with open(SHARED_FNAME, "r+b") as f:
        f.truncate(struct_size)
        buf = bytearray(struct_size)
        # Header: 4 ints (each 4 bytes on typical 32/64-bit)
        base = 0
        for key in ("max_samples", "sample_freq", "next_sample", "total_samples"):
            val = data.get(key, 0)
            ctypes.c_int.from_buffer(buf, base).value = val
            base += ctypes.sizeof(ctypes.c_int)
        # sample_array: c_int8 per sample
        samples = data.get("samples", [])
        for i, v in enumerate(samples):
            if i >= MAX_SAMPLES:
                break
            ctypes.c_int8.from_buffer(buf, base + i).value = v & 0xFF if isinstance(v, int) else 0
        f.seek(0)
        f.write(buf)


def fetch_and_write(api_base: str = "http://localhost:5001"):
    url = f"{api_base.rstrip('/')}/samples"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    write_snapshot(data)
    return data



def main():
    import argparse
    p = argparse.ArgumentParser(description="Fetch samples from VM API and write to local /tmp/shmem_data")
    p.add_argument("--api", default="http://localhost:5001", help="API base URL (default: localhost:5001)")
    p.add_argument("--once", action="store_true", help="Fetch once and exit (default: poll every 0.5s)")
    p.add_argument("--interval", type=float, default=0.5, help="Poll interval in seconds (default: 0.5)")
    args = p.parse_args()

    ensure_shmem_file()

    if args.once:
        d = fetch_and_write(args.api)
        print("Written: next_sample=%d total_samples=%d" % (d.get("next_sample"), d.get("total_samples")))
        return

    print("Polling %s/samples and writing to %s (Ctrl+C to stop)" % (args.api, SHARED_FNAME))
    while True:
        try:
            fetch_and_write(args.api)
        except Exception as e:
            print("Error:", e)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()