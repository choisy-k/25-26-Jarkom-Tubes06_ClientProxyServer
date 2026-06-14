import sys
import socket
import time
import threading

#Sesuai file tubes
def main():
    if len(sys.argv) != 3:
        print("Usage:")
        print("python client.py -mode tcp")
        print("python client.py -mode udp")
        return

    if sys.argv[1] != "-mode":
        print("Invalid argument")
        return

    mode = sys.argv[2].lower()

    if mode == "tcp":
        print("=" * 50)
        print("               TCP MODE              ")    
        print("Tekan [ Ctrl+C ] untuk menghentikan program")
        print("=" * 50)
        ip = get_proxy_ip()
        port = get_port()
        while True:
            choice = input("Jumlah client (1 atau 5): ").strip()
            if choice in ("1", "5"):
                client_count = int(choice)
                break
            print("Masukkan 1 atau 5.")
            
        if client_count == 1:
            tcp_mode(ip,port)
        else:
            run_five_tcp_clients(ip, port)

    elif mode == "udp":
        print("=" * 50)
        print("                UDP MODE              ")    
        print("Tekan [ Ctrl+C ] untuk menghentikan program")
        print("=" * 50)
        ip = get_proxy_ip()
        port = get_port()
        udp_mode(ip, port)

    else:
        print("Mode harus tcp atau udp")
            
#Memastikan Proxy IP benar
def get_proxy_ip():
    while True:
        ip = input("Masukkan Proxy IP: ").strip()
        try:
            socket.inet_aton(ip)
            return ip
        except OSError:
            print("[ERROR] Format IP tidak valid.")
            
#Memastikan Port benar
def get_port():
    while True:
        try:
            port = int(input("Masukkan nomor port: "))

            if 1 <= port <= 65535:
                return port

            print("Port harus antara 1 dan 65535.")

        except ValueError:
            print("Masukkan angka valid.")
            

def tcp_mode(ip, port):    
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1)
        client_socket.connect((ip, port))

        request = (
            "GET / HTTP/1.1\r\n"
            f"Host: {ip}\r\n"
            "Connection: close\r\n\r\n"
        )

        client_socket.sendall(request.encode('utf-8'))

        response = b""

        while True:
            try:
                data = client_socket.recv(4096)

                if not data:
                    break

                response += data
            except socket.timeout:
                continue

        print("\n===== HTTP RESPONSE =====")
        decoded = response.decode(errors="replace")

        MAX_DISPLAY = 250

        if len(decoded) > MAX_DISPLAY:
            print(decoded[:MAX_DISPLAY])
            print(f"\n... ({len(decoded) - MAX_DISPLAY} more characters)")
        else:
            print(decoded)

    except Exception as e:
        print("[TCP Error]", e)

    finally:
        client_socket.close()
        
def run_five_tcp_clients(proxy_ip,proxy_port):

    threads = []
    for i in range(5):
        t = threading.Thread(target=tcp_mode,args=(proxy_ip,proxy_port))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    
def udp_mode(ip, port):
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)

    rtts = []
    packets_sent = 10
    packets_received = 0

    print("\n===== UDP PING =====")

    for seq in range(1, 11):

        timestamp = time.time()
        payload = f"Ping {seq} {timestamp}"

        try:
            start_time = time.time()

            sock.sendto(payload.encode(), (ip, port))

            reply, _ = sock.recvfrom(1024)

            rtt = (time.time() - start_time) * 1000

            rtts.append(rtt)
            packets_received += 1

            print(f"Reply: {reply.decode()} | RTT={rtt:.2f} ms")

        except socket.timeout:
            print(f"Ping {seq}: Request timed out")

        time.sleep(1)

    print_udp_statistics(packets_sent,packets_received,rtts)

    sock.close()    
    
def print_udp_statistics(sent,received,rtts):

    print("\n===== UDP STATISTICS =====")

    loss = ((sent - received) / sent) * 100

    print(f"Paket terkirim  : {received}/{sent}")
    print(f"Packet Loss     : {loss:.2f}%")

    if len(rtts) == 0:
        return

    minimum = min(rtts)
    maximum = max(rtts)
    average = sum(rtts) / len(rtts)

    if len(rtts) > 1:

        differences = []

        for i in range(1, len(rtts)):
            diff = abs(rtts[i] - rtts[i - 1])
            differences.append(diff)

        jitter = (sum(differences) / len(differences))

    else:
        jitter = 0

    print(f"RTT Min : {minimum:.2f} ms")
    print(f"RTT Avg : {average:.2f} ms")
    print(f"RTT Max : {maximum:.2f} ms")
    print(f"Jitter  : {jitter:.2f} ms")    
    

if __name__ == "__main__":
    try:
        main()        
    except KeyboardInterrupt:
        print("\nProgram berhenti.")
