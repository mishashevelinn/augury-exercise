# Local Data Receiver (Hybrid Graph Mode)
This setup lets you keep the embedded device and samples reader running on the VM, while running the graph server and plotting UI on other machine (local for demo).
### 1. Components
- On the VM:

`embedded_device (QEMU)`

`samples_reader`

`data_server`  - Flask API exposing `/health` and `/samples` from `/tmp/shmem_data`

- On the other machine (local):

`data_receiver.py` – pulls data from the VM API and writes it into local /tmp/shmem_data
graph_server.py – copied from the VM’s graph_webserver and run locally
### 2. Pre‑requisites

#### On the other machine (local)
initialize and activate python virtual environment:

`python3 -m venv venv`

`source venv/bin/activate`

install dependencies

`pip install -r requirements.txt`


#### SSH Tunnel from Local → VM
From the local machine, open an SSH tunnel so localhost:5001 hits the VM’s API:

`ssh -L 5001:127.0.0.1:5001 username@<VM_IP>`

Keep this SSH session open.
You can verify the VM's API is reachable from local:

`curl http://localhost:5001/health# -> {"status":"ok"}`
### 4. Start data acquisition and rendering
 
- #### On the VM:
  run embedded_device and sample_reader as described in the assignment

- #### On the other machine (local):
- single snapshot (after sampling is done):

    `python3 local_client.py --once`

- continuous mirroring (live updates):

   ` python3 data_receiver.py`

- optional - change polling interval

   `python3 local_client.py --interval 0.2`


This creates/updates local /tmp/shmem_data with the same binary layout as on the VM.
 Run the Graph Server Locally

- Run graph server :
`python3 graph_server.py`

By default, it listens on 0.0.0.0:5000. Open:
http://localhost:5000/
You should see the same real‑time graph, now rendered on the local machine, driven by data pulled from the VM via the `/samples` API and written into the local `/tmp/shmem_data`.