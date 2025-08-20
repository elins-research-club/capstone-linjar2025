# laptop_receiver.py
import socket, json, struct, os, hashlib, threading, sys, time
from pathlib import Path
from datetime import datetime

HOST = "0.0.0.0"   # dengarkan di semua interface
PORT = 5001
SAVE_DIR = Path("received")
SAVE_DIR.mkdir(exist_ok=True)

stop_event = threading.Event()

def input_watcher():
    print("Ketik 'q' lalu Enter untuk menghentikan server.")
    for line in sys.stdin:
        if line.strip().lower() in ("q", "quit", "exit"):
            stop_event.set()
            break

def recv_exact(conn, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            raise EOFError("Connection closed")
        data += chunk
    return data

def recv_msg(conn) -> dict:
    raw_len = recv_exact(conn, 4)              # 4-byte panjang header
    (n,) = struct.unpack("!I", raw_len)
    payload = recv_exact(conn, n)
    return json.loads(payload.decode("utf-8"))

def send_msg(conn, obj: dict):
    payload = json.dumps(obj).encode("utf-8")
    conn.sendall(struct.pack("!I", len(payload)))
    conn.sendall(payload)

def unique_path(base: Path, name: str) -> Path:
    name = os.path.basename(name)
    p = base / name
    if not p.exists():
        return p
    stem, ext = os.path.splitext(name)
    i = 1
    while True:
        q = base / f"{stem}_{i}{ext}"
        if not q.exists():
            return q
        i += 1

def handle_client(conn, addr):
    print(f"[+] Koneksi dari {addr}")
    try:
        while not stop_event.is_set():
            header = recv_msg(conn)  # {'op':'FILE'|'BYE', 'filename', 'filesize', 'sha256'}
            op = header.get("op", "FILE")

            if op == "BYE":
                send_msg(conn, {"status": "bye"})
                print(f"[=] {addr} menutup koneksi")
                break

            if op != "FILE":
                send_msg(conn, {"status": "error", "reason": "unknown op"})
                continue

            filename = header["filename"]
            filesize = int(header["filesize"])
            sha256_expect = header.get("sha256")

            dest = unique_path(SAVE_DIR, filename)
            received = 0
            hasher = hashlib.sha256()

            with open(dest, "wb") as f:
                while received < filesize:
                    if stop_event.is_set():
                        raise EOFError("Stop requested")
                    chunk = conn.recv(min(65536, filesize - received))
                    if not chunk:
                        raise EOFError("Connection closed mid-file")
                    f.write(chunk)
                    hasher.update(chunk)
                    received += len(chunk)

            digest = hasher.hexdigest()
            ok = (sha256_expect is None) or (digest == sha256_expect)

            meta = {
                "status": "ok" if ok else "checksum_mismatch",
                "saved_as": str(dest.resolve()),
                "bytes": received,
                "sha256": digest,
                "time": datetime.now().isoformat(timespec="seconds"),
            }
            send_msg(conn, meta)
            print(f"[✓] Tersimpan: {dest.name} ({received} B) sha256_ok={ok}")

    except EOFError as e:
        print(f"[!] {addr} eof: {e}")
    except Exception as e:
        print(f"[!] {addr} error: {e}")
    finally:
        conn.close()
        print(f"[-] Koneksi ditutup: {addr}")

def main():
    t = threading.Thread(target=input_watcher, daemon=True)
    t.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        s.settimeout(1.0)  # supaya bisa cek stop_event tiap detik
        print(f"Receiver listening on {HOST}:{PORT}. Folder simpan: {SAVE_DIR.resolve()}")

        try:
            while not stop_event.is_set():
                try:
                    conn, addr = s.accept()
                except socket.timeout:
                    continue
                handle_client(conn, addr)
                # setelah client selesai, kembali menunggu
        finally:
            print("Server berhenti.")

if __name__ == "__main__":
    main()