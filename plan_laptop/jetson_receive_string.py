# jetson_cmd_receiver.py
import socket, threading, sys, time

HOST = "0.0.0.0"
PORT = 5002
stop_event = threading.Event()

def input_watcher():
    print("Ketik 'q' lalu Enter untuk menghentikan receiver perintah.")
    for line in sys.stdin:
        if line.strip().lower() in ("q", "quit", "exit"):
            stop_event.set()
            break

def handle_client(conn, addr):
    print(f"[+] Terhubung dari {addr}")
    f = conn.makefile("rwb", buffering=0)
    try:
        while not stop_event.is_set():
            line = f.readline()
            if not line:
                print("[-] Client menutup koneksi.")
                break
            msg = line.decode("utf-8", errors="replace").rstrip("\r\n")
            print(f"[CMD] {msg}")
            # Kirim ACK satu baris
            ack = f"ACK: {msg}\n".encode("utf-8")
            f.write(ack)
    except Exception as e:
        print(f"[!] Error client {addr}: {e}")
    finally:
        try: f.close()
        except: pass
        conn.close()
        print(f"[-] Koneksi tertutup: {addr}")

def main():
    threading.Thread(target=input_watcher, daemon=True).start()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        s.settimeout(1.0)
        print(f"Receiver CMD listening on {HOST}:{PORT}")

        while not stop_event.is_set():
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            handle_client(conn, addr)

    print("Receiver CMD berhenti.")

if __name__ == "__main__":
    main()
