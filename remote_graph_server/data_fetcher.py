#!/usr/bin/env python3
"""
Remote client: fetches /samples from VM (localhost:5001 via SSH tunnel),
writes into local /tmp/shmem_data so graph_server.py can run locally and plot.
"""
import ctypes
import os
import time
import urllib.request
import json

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


class DataFetcher:
    def __init__(self, api_base: str = "http://localhost:5001", shmem_path: str = SHARED_FNAME):
        self.api_base = api_base.rstrip("/")
        self.shmem_path = shmem_path

    def ensure_shmem_file(self) -> None:
        """Ensure /tmp/shmem_data exists and has the right size; otherwise raise."""
        struct_size = ctypes.sizeof(SharedMemStruct)
        if not os.path.exists(self.shmem_path):
            raise RuntimeError(
                f"{self.shmem_path} does not exist. Start graph_server.py first."
            )
        if os.path.getsize(self.shmem_path) != struct_size:
            raise RuntimeError(
                f"{self.shmem_path} has wrong size (got {os.path.getsize(self.shmem_path)}, "
                f"expected {struct_size}). Make sure graph_server.py created it."
            )

    def write_snapshot(self, data: dict) -> None:
        struct_size = ctypes.sizeof(SharedMemStruct)
        with open(self.shmem_path, "r+b") as f:
            buf = bytearray(struct_size)
            base = 0
            for key in ("max_samples", "sample_freq", "next_sample", "total_samples"):
                val = data.get(key, 0)
                ctypes.c_int.from_buffer(buf, base).value = val
                base += ctypes.sizeof(ctypes.c_int)

            samples = data.get("samples", [])
            for i, v in enumerate(samples):
                if i >= MAX_SAMPLES:
                    break
                ctypes.c_int8.from_buffer(buf, base + i).value = v

            f.seek(0)
            f.write(buf)

    def fetch_and_write(self) -> dict:
        url = f"{self.api_base}/samples"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        self.write_snapshot(data)
        return data


    def run_loop(self, interval: float = 0.5) -> None:
        self.ensure_shmem_file()
        print("Polling %s/samples and writing to %s (Ctrl+C to stop)" % (self.api_base, self.shmem_path))
        while True:
            try:
                self.fetch_and_write()
            except Exception as e:
                print("Error:", e)
            time.sleep(interval)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Fetch samples from VM API and write to local /tmp/shmem_data")

    p.add_argument("--api", default="http://localhost:5001", help="API base URL")
    p.add_argument("--interval", type=float, default=0.5, help="Poll interval in seconds")
    args = p.parse_args()

    fetcher = DataFetcher(api_base=args.api)

    fetcher.run_loop(interval=args.interval)


if __name__ == "__main__":
    main()