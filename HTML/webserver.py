import socket
import threading
import os
import mimetypes
from datetime import datetime
import time

#KONFIGURASI
HOST = '0.0.0.0'
PORT_TCP = 8000
PORT_UDP = 9000

#Mengubah port jika port default unavailable
def bind_port(sock, start_port):
    port = start_port
    while True:
        try:
            sock.bind((HOST, port))
            return port
        except OSError:
            port += 1
            
#Log di cmd
def log_connection(client_ip, path, status_code):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] IP Proxy: {client_ip} | Request: {path} | Status: {status_code}")
    
#TCP HTTP Server
def handle_tcp_client(client_conn, client_addr):
    try:
        #time.sleep(10)
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
        
#Membuat koneksi TCP
def start_tcp_server():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port = bind_port(tcp_socket, PORT_TCP)
    tcp_socket.listen(20) # Mampu menampung banyak antrean
    tcp_socket.settimeout(1) #agar bisa Ctrl+C
    print(f"[TCP] HTTP Web Server aktif di http://{HOST}:{port}")
    
    while True:
        try: 
            client_conn, client_addr = tcp_socket.accept()
            # Mengaktifkan Multithreading untuk setiap koneksi masuk
            client_thread = threading.Thread(target=handle_tcp_client, args=(client_conn, client_addr), daemon=True)
            client_thread.start()
        
        except socket.timeout:
            continue

#Membuat koneksi UDP
def start_udp_server():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port = bind_port(udp_socket, PORT_UDP)
    print(f"[UDP] QoS Echo Server mendengarkan di port: {port}")
    udp_socket.settimeout(1)
    
    while True:
        try:
            data, client_addr = (udp_socket.recvfrom(4096))
            print(f"[UDP] menerima {len(data)} bytes dari {client_addr}")
            udp_socket.sendto(data, client_addr)
        #periodically checks for KeyboardInterrupt
        except socket.timeout:
            continue
        except Exception as e:
            print(f"---[UDP ERROR] {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("                WEB SERVER              ")    
    print("Tekan [ Ctrl+C ] untuk menghentikan program")
    print("=" * 50)

    try:
        #Background thread
        threading.Thread(target=start_udp_server, daemon=True).start()
        
        #Main thread
        start_tcp_server()
        
    except KeyboardInterrupt:
        print("\nServer terminated by user.")