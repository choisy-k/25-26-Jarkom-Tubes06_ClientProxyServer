import socket
import threading
import os
import mimetypes
from datetime import datetime

# ==========================================
# KONFIGURASI JARINGAN
# ==========================================
HOST = '0.0.0.0'
PORT_TCP = 8000
PORT_UDP = 9000

def log_connection(client_ip, path, status_code):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] IP Klien: {client_ip} | Request: {path} | Status: {status_code}")

# ==========================================
# KOMPONEN 1: TCP HTTP SERVER (WEB STATIS)
# ==========================================
def handle_tcp_client(client_conn, client_addr):
    try:
        # 1. Membaca request masuk
        request = client_conn.recv(4096).decode('utf-8', errors='ignore')
        if not request:
            return

        lines = request.split('\r\n')
        first_line = lines[0].split(' ')
        if len(first_line) < 2:
            return
        
        method = first_line[0]
        path = first_line[1]

        # 2. Hanya proses jika method adalah GET
        if method == 'GET':
            # Mengatur routing dasar
            filename = path[1:] if path != '/' else 'index.html'
            
            # Keamanan dasar untuk mencegah Directory Traversal
            if '..' in filename:
                filename = 'index.html'
                
            filepath = filename

            # 3. Cek apakah file ada di direktori
            if os.path.exists(filepath) and os.path.isfile(filepath):
                try:
                    with open(filepath, 'rb') as file:
                        file_content = file.read()
                    
                    # Deteksi tipe file (HTML/CSS/PNG)
                    mime_type, _ = mimetypes.guess_type(filepath)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'
                    
                    status_code = 200
                    status_text = "OK"
                    
                    response_header = (
                        f"HTTP/1.1 {status_code} {status_text}\r\n"
                        f"Content-Type: {mime_type}\r\n"
                        f"Content-Length: {len(file_content)}\r\n"
                        "Connection: close\r\n\r\n"
                    )
                    client_conn.sendall(response_header.encode('utf-8') + file_content)
                    
                except Exception:
                    # Penanganan 500: Server Gagal Membaca File
                    status_code = 500
                    status_text = "Internal Server Error"
                    error_file = 'status/500.html'
                    
                    if os.path.exists(error_file):
                        with open(error_file, 'rb') as err_f:
                            error_msg = err_f.read()
                    else:
                        error_msg = b"<html><body><h1>500 Internal Server Error</h1></body></html>"
                        
                    response_header = f"HTTP/1.1 {status_code} {status_text}\r\nContent-Type: text/html\r\nContent-Length: {len(error_msg)}\r\nConnection: close\r\n\r\n"
                    client_conn.sendall(response_header.encode('utf-8') + error_msg)
            else:
                # Penanganan 404: File Tidak Ditemukan
                status_code = 404
                status_text = "Not Found"
                error_file = 'status/404.html'
                
                if os.path.exists(error_file):
                    with open(error_file, 'rb') as err_f:
                        error_msg = err_f.read()
                else:
                    error_msg = b"<html><body><h1>404 Not Found</h1></body></html>"
                    
                response_header = f"HTTP/1.1 {status_code} {status_text}\r\nContent-Type: text/html\r\nContent-Length: {len(error_msg)}\r\nConnection: close\r\n\r\n"
                client_conn.sendall(response_header.encode('utf-8') + error_msg)

            # Mencatat log aktivitas ke terminal
            log_connection(client_addr[0], path, status_code)
            
    except Exception as e:
        print(f"[-] Kendala pada pekerja thread: {e}")
    finally:
        client_conn.close()

def start_tcp_server():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind((HOST, PORT_TCP))
    tcp_socket.listen(20) # Mampu menampung banyak antrean
    print(f"[*] [TCP] HTTP Web Server aktif di http://{HOST}:{PORT_TCP}")
    
    while True:
        client_conn, client_addr = tcp_socket.accept()
        # Mengaktifkan Multithreading untuk setiap koneksi masuk
        client_thread = threading.Thread(target=handle_tcp_client, args=(client_conn, client_addr), daemon=True)
        client_thread.start()

# ==========================================
# KOMPONEN 2: UDP QOS ECHO SERVER
# ==========================================
def start_udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, PORT_UDP))
    print(f"[*] [UDP] QoS Echo Server mendengarkan di port {PORT_UDP}")
    
    while True:
        try:
            # Menerima paket ping dari client dan langsung melemparnya kembali (Echo)
            data, client_addr = udp_socket.recvfrom(4096)
            udp_socket.sendto(data, client_addr)
        except Exception as e:
            print(f"[-] Kendala pada UDP Server: {e}")

# ==========================================
# TITIK EKSEKUSI UTAMA
# ==========================================
if __name__ == "__main__":
    print("=======================================")
    print("      MEMULAI DUAL-PROTOCOL SERVER     ")
    print("=======================================")
    
    # 1. Jalankan UDP Server di latar belakang (Background Thread)
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()
    
    # 2. Jalankan TCP Server di jalur utama (Main Thread)
    start_tcp_server()