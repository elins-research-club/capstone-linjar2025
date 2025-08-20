# jetson_cam_sender.py
import socket, json, struct, hashlib, threading, sys, time
from datetime import datetime
import cv2

LAPTOP_IP = "192.168.1.50"   # GANTI: IP laptop-mu
PORT = 5001
PERIOD = 2.0                 # jeda antar-capture (detik)
JPEG_QUALITY = 90            # kualitas JPEG 0..100

stop_event = threading.Event()

def input_watcher():
    print("Ketik 'q' lalu Enter untuk berhenti.")
    for line in sys.stdin:
        if line.strip().lower() in ("q", "quit", "exit"):
            stop_event.set()
            break

def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def send_msg(sock, obj: dict):
    payload = json.dumps(obj).encode("utf-8")
    sock.sendall(struct.pack("!I", len(payload)))
    sock.sendall(payload)

def recv_msg(sock) -> dict:
    raw = sock.recv(4)
    if not raw:
        raise EOFError("server closed")
    (n,) = struct.unpack("!I", raw)
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("server closed mid-ack")
        buf += chunk
    return json.loads(buf.decode("utf-8"))

def main():
    t = threading.Thread(target=input_watcher, daemon=True)
    t.start()

    cap = cv2.VideoCapture(0)   # sesuaikan index kamera jika perlu
    if not cap.isOpened():
        raise RuntimeError("Kamera tidak ditemukan / tidak bisa dibuka.")

    # (Opsional) atur resolusi:
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Menghubungkan ke {LAPTOP_IP}:{PORT} ...")
        s.connect((LAPTOP_IP, PORT))
        print("Terhubung. Mulai kirim frame kamera. (q + Enter untuk berhenti)")

        try:
            while not stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Gagal capture dari kamera")

                ok, enc = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if not ok:
                    raise RuntimeError("Gagal encode JPEG")
                data = enc.tobytes()

                fname = f"cam_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                header = {
                    "op": "FILE",
                    "filename": fname,
                    "filesize": len(data),
                    "sha256": sha256_bytes(data),
                }

                # kirim header + data
                send_msg(s, header)
                s.sendall(data)

                # tunggu ACK
                ack = recv_msg(s)
                status = ack.get("status")
                saved_as = ack.get("saved_as")
                print(f"ACK: {status} -> {saved_as}")

                # jeda sebelum kirim berikutnya
                for _ in range(int(PERIOD * 10)):
                    if stop_event.is_set():
                        break
                    time.sleep(0.1)

        except KeyboardInterrupt:
            pass
        finally:
            # kirim BYE agar server menutup koneksi dengan baik
            try:
                send_msg(s, {"op": "BYE"})
                _ = recv_msg(s)
            except Exception:
                pass
            cap.release()
            print("Pengiriman dihentikan.")

if __name__ == "__main__":
    main()
