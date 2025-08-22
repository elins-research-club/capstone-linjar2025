import subprocess

processes = []
scripts = ["jetson_send_to_software.py", 
            "jetson_read_serial.py", 
            "plan_laptop/jetson_receive_string.py", # plan laptop
            "plan_laptop/jetson_send_pict.py" # plan laptop
            ]

for script in scripts:
    p = subprocess.Popen(["python", script])
    processes.append(p)

# Wait for all to finish
for p in processes:
    p.wait()
