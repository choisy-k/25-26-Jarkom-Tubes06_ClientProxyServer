import socket
import threading
import time

#KONFIGURASI
PORT_TCP = 8080
PORT_UDP = 9090
PORT_SERVER_TCP = 8000
PORT_SERVER_UDP = 9000

CACHE_TIMEOUT = 10

cache = {}
cache_lock = threading.Lock()

#Mengubah port jika port default unavailable
def bind_port(sock, start_port):
    port = start_port
    while True:
        try:
            sock.bind(('0.0.0.0', port))
            return port
        except OSError:
            port += 1

#Memastikan Server IP benar
def get_server_ip():
    while True:
        ip = input("Masukkan Web Server IP: ").strip()
        try:
            socket.inet_aton(ip)
            return ip
        except OSError:
            print("[ERROR] Format IP tidak valid.")
    
#Log di cmd
def log_connection(client_ip, protocol, cache_status, status_code, size, url, response_time):
    print(f"[{client_ip}] {protocol} | {cache_status} | Status: {status_code} | {size} bytes | {url} | {response_time:.3f} s")
    
#=====CACHE======
def get_cache(path):
    with cache_lock:
        if path in cache:
            data, timestamp = cache[path]
            
            if time.time() - timestamp < CACHE_TIMEOUT:
                return data
            del cache[path]
            
    return None

def put_cache(path, data):
    with cache_lock:
        cache[path] = (data, time.time())
        
# TCP PROXY
def handle_client(client_socket, client_addr):
    
    start = time.time()
    
    try:
        #Menerima request dari client_addr
        request = client_socket.recv(8192)
        if not request:
            client_socket.close()
            return
        
        #parse request path
        first_line = request.decode(errors="ignore").split("\r\n")[0]
        
        try:
            method, path, version = first_line.split()
        except:
            path = "/"
            
        #CACHE HIT
        cached = get_cache(path)
        
        if cached:
            client_socket.sendall(cached)
            log_connection(client_addr[0], "TCP", "HIT", "200", len(cached), path, time.time() - start)
            client_socket.close()
            return
        
        #Forwarding ke server
        status_code = "UNKNOWN"
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(5)
            server_socket.connect((WEBSERVER_IP, PORT_SERVER_TCP))
            server_socket.sendall(request)
            
            response = b""
            
            while True:
                chunk = server_socket.recv(4096)
                
                if not chunk:
                    break
                    
                response += chunk
                
                try:
                    first_line = (response.decode(errors="ignore").split("\r\n")[0])
                    status_code = (first_line.split()[1])
                except:
                    pass
                    
            server_socket.close()
            
        #Error handling
        except socket.timeout:
            
            response = (
                b"HTTP/1.1 504 Gateway Timeout\r\n"
                b"Content-Type:text/html\r\n\r\n"
                b"<h1>504 Gateway Timeout</h1>"
            )

            client_socket.sendall(response)

            log_connection(client_addr[0], "TCP", "TIMEOUT", status_code, len(response), path, time.time() - start)

            client_socket.close()
            return
            
        except Exception:

            response = (
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Content-Type:text/html\r\n\r\n"
                b"<h1>502 Bad Gateway</h1>"
            )

            client_socket.sendall(response)
            
            log_connection(client_addr[0], "TCP", "BAD_GATEWAY", status_code, len(response), path, time.time() - start)
            
            client_socket.close()
            return
        
        #CACHE MISS
        put_cache(path, response)
        client_socket.sendall(response)
        
        log_connection(client_addr[0], "TCP", "MISS", status_code, len(response), path, time.time() - start)
        
    except Exception as e:
        print(f"---[PROXY ERROR] {e}")
        
    finally:
        client_socket.close()
        

def start_tcp_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_port = bind_port(proxy_socket, PORT_TCP)
    proxy_socket.listen(20)
    print(f"[TCP] Proxy mendengarkan di port: {tcp_port}")
    proxy_socket.settimeout(1)
    
    while True:
        try:
            client_conn, client_addr = proxy_socket.accept()
            # Mengaktifkan Multithreading untuk setiap koneksi masuk
            client_thread = threading.Thread(target=handle_client, args=(client_conn, client_addr), daemon=True)
            client_thread.start()
        #agar Ctrl+C bisa digunakan
        except socket.timeout:
            continue

# UDP PROXY
def start_udp_proxy():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port = bind_port(udp_socket, PORT_UDP)
    print(f"[UDP] Proxy mendengarkan di port: {port}")
    
    while True:
        data, addr = udp_socket.recvfrom(4096)
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.settimeout(1)
        print(f"[UDP] Paket di-forward.")
        server.sendto(data, (WEBSERVER_IP, PORT_SERVER_UDP))
        
        try:
            response, _ = server.recvfrom(4096)
            udp_socket.sendto(response, addr)
        except socket.timeout:
            print("[UDP] Server timeout")


if __name__ == "__main__":
    print("=" * 50)
    print("                   PROXY              ")    
    print("Tekan [ Ctrl+C ] untuk menghentikan program")
    print("=" * 50)
    WEBSERVER_IP = get_server_ip()

    try:
        #Background thread
        threading.Thread(target=start_udp_proxy, daemon=True).start()
        
        #Main thread
        start_tcp_proxy()
        
    except KeyboardInterrupt:
        print("\nServer terminated by user.")