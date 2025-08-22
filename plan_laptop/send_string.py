# laptop_cmd_sender.py
import socket, sys

JETSON_IP = "192.168.1.23"   # <-- GANTI dengan IP Jetson
PORT = 5002

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print(f"Menghubungkan ke {JETSON_IP}:{PORT} ...")
    s.connect((JETSON_IP, PORT))
    f = s.makefile("rwb", buffering=0)
    print("Terhubung. Ketik pesan dan Enter untuk kirim. Ketik 'q' untuk keluar.")

    try:
        for line in sys.stdin:
            text = line.rstrip("\r\n")
            if text.lower() in ("q", "quit", "exit"):
                break
            # kirim satu baris
            f.write((text + "\n").encode("utf-8"))
            # baca ACK satu baris
            ack = f.readline()
            if not ack:
                print("Server menutup koneksi.")
                break
            print("ACK dari Jetson:", ack.decode("utf-8", errors="replace").rstrip())
    finally:
        try: f.close()
        except: pass
        print("Koneksi ditutup.")
