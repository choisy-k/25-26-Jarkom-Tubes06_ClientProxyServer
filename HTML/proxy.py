import socket
import threading
import time

# =========================
# CONFIGURATION
# =========================
DEFAULT_TCP_PORT = 8080
DEFAULT_UDP_PORT = 9090

WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8000

CACHE_TIMEOUT = 10  # seconds

cache = {}
cache_lock = threading.Lock()


# =========================
# FIND AVAILABLE PORT
# =========================
def bind_available_port(sock, start_port):
    port = start_port

    while True:
        try:
            sock.bind(("0.0.0.0", port))
            return port
        except OSError:
            port += 1


# =========================
# LOGGING
# =========================
def log(client_ip,
        protocol,
        cache_status,
        size,
        url,
        response_time):

    print(
        f"[{client_ip}] "
        f"{protocol} | "
        f"{cache_status} | "
        f"{size} bytes | "
        f"{url} | "
        f"{response_time:.3f}s"
    )


# =========================
# CACHE
# =========================
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


# =========================
# TCP PROXY HANDLER
# =========================
def handle_client(client_socket, client_addr):

    start = time.time()

    try:

        request = client_socket.recv(8192)

        if not request:
            client_socket.close()
            return

        first_line = request.decode(
            errors="ignore"
        ).split("\r\n")[0]

        try:
            method, path, version = first_line.split()
        except:
            path = "/"

        # -----------------
        # CACHE HIT
        # -----------------
        cached = get_cache(path)

        if cached:

            client_socket.sendall(cached)

            log(
                client_addr[0],
                "TCP",
                "HIT",
                len(cached),
                path,
                time.time() - start
            )

            client_socket.close()
            return

        # -----------------
        # FORWARD TO SERVER
        # -----------------
        try:

            server_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            server_socket.settimeout(5)

            server_socket.connect(
                (WEB_SERVER_HOST,
                 WEB_SERVER_PORT)
            )

            server_socket.sendall(request)

            response = b""

            while True:

                chunk = server_socket.recv(4096)

                if not chunk:
                    break

                response += chunk

            server_socket.close()

        except socket.timeout:

            response = (
                b"HTTP/1.1 504 Gateway Timeout\r\n"
                b"Content-Type:text/html\r\n\r\n"
                b"<h1>504 Gateway Timeout</h1>"
            )

            client_socket.sendall(response)

            log(
                client_addr[0],
                "TCP",
                "TIMEOUT",
                len(response),
                path,
                time.time() - start
            )

            client_socket.close()
            return

        except Exception:

            response = (
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Content-Type:text/html\r\n\r\n"
                b"<h1>502 Bad Gateway</h1>"
            )

            client_socket.sendall(response)

            log(
                client_addr[0],
                "TCP",
                "BAD_GATEWAY",
                len(response),
                path,
                time.time() - start
            )

            client_socket.close()
            return

        put_cache(path, response)

        client_socket.sendall(response)

        log(
            client_addr[0],
            "TCP",
            "MISS",
            len(response),
            path,
            time.time() - start
        )

    except Exception as e:
        print("Proxy error:", e)

    finally:
        client_socket.close()


# =========================
# TCP PROXY SERVER
# =========================
def start_tcp_proxy():

    proxy_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    proxy_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    tcp_port = bind_available_port(
        proxy_socket,
        DEFAULT_TCP_PORT
    )

    proxy_socket.listen(20)

    print(f"[TCP Proxy] Running on port {tcp_port}")

    while True:

        client_socket, client_addr = (
            proxy_socket.accept()
        )

        threading.Thread(
            target=handle_client,
            args=(client_socket, client_addr),
            daemon=True
        ).start()


# =========================
# UDP PROXY
# =========================
def start_udp_proxy():

    udp_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    udp_port = bind_available_port(
        udp_socket,
        DEFAULT_UDP_PORT
    )

    print(f"[UDP Proxy] Running on port {udp_port}")

    while True:

        data, addr = udp_socket.recvfrom(
            4096
        )

        server = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        server.sendto(
            data,
            (WEB_SERVER_HOST, 9000)
        )

        response, _ = server.recvfrom(
            4096
        )

        udp_socket.sendto(
            response,
            addr
        )


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    threading.Thread(
        target=start_udp_proxy,
        daemon=True
    ).start()

    start_tcp_proxy()