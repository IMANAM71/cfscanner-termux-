import requests
import socket
import threading
import ssl
from icmplib import ping
import concurrent.futures
import warnings
import sys
import ipaddress
import random
import time
from queue import Queue
import queue
from typing import List, Dict

warnings.filterwarnings("ignore")
log_lock = threading.Lock()

# ─── Default settings ───
DEFAULT_DOMAIN = "www.speedtest.net"
DEFAULT_PORT = 443
DEFAULT_MAX_PING = 150.0
DEFAULT_BATCH_SIZE = 1000
DEFAULT_MAX_WORKERS = 250
TEST_DOWNLOAD = True
DOWNLOAD_SIZE = 102400
TIMEOUT_CONNECT = 3.0
TIMEOUT_READ = 5.0
RANDOMIZE = True
RANDOM_IPS_PER_24 = 32
MIX_RANGES = True

# ─── Convert single CIDR or IP to list ───
def all_ips_from_cidr(line: str) -> List[str]:
    try:
        net = ipaddress.ip_network(line.strip(), strict=False)
        return [str(ip) for ip in net.hosts()]
    except:
        s = line.strip()
        if s.count('.') == 3:
            return [s]
        return []

# ─── Generate IPs from ranges ───
def collect_all_ips(ip_lines: List[str]) -> List[str]:
    all_subnets = set()
    for line in ip_lines:
        try:
            net = ipaddress.ip_network(line.strip(), strict=False)
            all_subnets.add(net)
        except:
            pass

    ranges_24 = set()
    for net in all_subnets:
        if net.prefixlen <= 24:
            for sub in net.subnets(new_prefix=24):
                ranges_24.add(sub)
        else:
            ranges_24.add(net)

    ranges_24 = list(ranges_24)
    if MIX_RANGES:
        random.shuffle(ranges_24)

    all_ips = []
    for net in ranges_24:
        hosts = list(net.hosts())
        if RANDOMIZE:
            num = min(RANDOM_IPS_PER_24, len(hosts))
            selected = random.sample(hosts, num) if num > 0 else []
            all_ips.extend(str(ip) for ip in selected)
        else:
            all_ips.extend(str(ip) for ip in hosts)

    random.shuffle(all_ips)
    return all_ips

# ─── Test IP ───
def test_ip_advanced(ip: str) -> Dict | None:
    try:
        start = time.time()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT_CONNECT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((ip, PORT))

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        ssl_sock = context.wrap_socket(sock, server_hostname=DOMAIN)

        if MODE == "trojan":
            ssl_sock.sendall(b'trojan\r\n')
        else:
            ssl_sock.sendall(b'\x00' * 16)

        data = ssl_sock.recv(32)
        if len(data) <= 4:
            return None

        downloaded = 0
        speed_kbps = 0.0
        if TEST_DOWNLOAD:
            request = f"GET / HTTP/1.1\r\nHost: {DOMAIN}\r\nConnection: close\r\n\r\n"
            ssl_sock.send(request.encode())

            start_dl = time.time()
            while downloaded < DOWNLOAD_SIZE:
                try:
                    chunk = ssl_sock.recv(8192)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                except socket.timeout:
                    break
            dl_time = time.time() - start_dl
            speed_kbps = (downloaded / 1024) / (dl_time or 0.001)

        ssl_sock.close()
        sock.close()

        latency_ms = (time.time() - start) * 1000

        loss, ping_rtt = get_ping_loss(ip)
        if ping_rtt is None or loss is None or loss >= 40:
            return None

        return {
            'ip': ip,
            'ping': ping_rtt,
            'loss': loss,
            'latency_ms': round(latency_ms, 2),
            'speed_kbps': round(speed_kbps, 2),
            'dl_bytes': downloaded,
            'proto': MODE.upper()
        }

    except Exception:
        return None

# ─── Ping ───
def get_ping_loss(ip: str) -> tuple:
    try:
        res = ping(ip, count=1, interval=0.2, timeout=0.6, privileged=False)
        if res.packets_received == 0:
            return None, None
        loss = 100 - (res.packets_received / res.packets_sent * 100)
        return loss, res.avg_rtt
    except:
        return None, None

# ─── Scoring ───
def score_result(r: Dict) -> float:
    ping_score = (r['ping'] or 999) ** 1.4
    loss_score = (r['loss'] or 100) * 3
    latency_score = (r.get('latency_ms', 999)) * 0.8
    speed_bonus = max(0, r.get('speed_kbps', 0) / 5)
    return ping_score + loss_score + latency_score - speed_bonus

# ─── Save realtime ───
def save_realtime(ip: str, filename="good_ips.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(ip + "\n")

# ─── Show progress ───
def show_progress(current: int, total: int, found: int):
    with log_lock:
        print(f"  {current:6,} / {total:6,}   →   Found good: {found:4}", end="\r")

# ─── Live printer ───
def live_good_ips_printer(good_queue: Queue, stop_event: threading.Event, max_ping: float):
    while not stop_event.is_set():
        try:
            r = good_queue.get(timeout=1.0)
            if r['ping'] <= max_ping:
                with log_lock:
                    print(f"  GOOD → {r['ip']:15}  ping:{r['ping']:5.1f}ms  loss:{r['loss']:5.1f}%  speed:{r.get('speed_kbps',0):.1f}KB/s")
        except queue.Empty:
            time.sleep(0.3)

# ─── Save top 20 after showing top 5 ───
def save_top_ips(results: List[Dict], max_ping: float, filename="scan.txt"):
    candidates = [r for r in results if r['ping'] <= max_ping]
    candidates.sort(key=score_result)

    if not candidates:
        print("\nNo suitable IPs found.")
        return

    print("\n" + "=" * 70)
    print(f"Top 5 Best IPs (Ping <= {max_ping:.0f} ms) - Quick check")
    print("=" * 70)
    print("  # | IP               | Ping  | Loss  | Speed KB/s | Proto ")
    print("-" * 70)

    for i, r in enumerate(candidates[:5], 1):
        print(f"{i:3} | {r['ip']:16} | {r['ping']:5.1f} | {r['loss']:5.1f}% | {r.get('speed_kbps', 0):10.1f} | {r['proto']}")

    top_ips = [r['ip'] for r in candidates[:20]]
    with open(filename, "w", encoding="utf-8") as f:
        for ip in top_ips:
            f.write(ip + "\n")

    print(f"\nSaved {len(top_ips)} best IPs to {filename}")

# ─── Main ───
def main():
    global MODE, DOMAIN, PORT, MAX_PING, BATCH_SIZE, MAX_WORKERS

    print("Cloudflare IP Scanner (user configurable batch & workers)")
    print(f"Default domain: {DEFAULT_DOMAIN} | Default port: {DEFAULT_PORT}")

    domain_input = input(f"Test domain [{DEFAULT_DOMAIN}]: ").strip()
    DOMAIN = domain_input if domain_input else DEFAULT_DOMAIN

    port_input = input(f"Port [{DEFAULT_PORT}]: ").strip()
    PORT = int(port_input) if port_input else DEFAULT_PORT

    ping_input = input(f"Max acceptable ping (ms) [{DEFAULT_MAX_PING}]: ").strip()
    MAX_PING = float(ping_input) if ping_input else DEFAULT_MAX_PING

    batch_input = input(f"Batch size (IPs per batch) [{DEFAULT_BATCH_SIZE}]: ").strip()
    BATCH_SIZE = int(batch_input) if batch_input else DEFAULT_BATCH_SIZE

    workers_input = input(f"Max concurrent threads (workers) [{DEFAULT_MAX_WORKERS}]: ").strip()
    MAX_WORKERS = int(workers_input) if workers_input else DEFAULT_MAX_WORKERS

    mode_input = input("Mode → 1=VLESS  2=Trojan  [1]: ").strip() or "1"
    MODE = "trojan" if mode_input == "2" else "vless"
    print(f"→ Mode: {MODE.upper()} | Batch: {BATCH_SIZE} | Workers: {MAX_WORKERS}\n")

    try:
        with open("ip.txt", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("ip.txt file not found!")
        return

    if not lines:
        print("ip.txt is empty!")
        return

    print("\nAvailable ranges / lines in ip.txt:")
    print("-" * 60)
    for i, line in enumerate(lines, 1):
        typ = "CIDR" if '/' in line else "Single IP" if line.count('.') == 3 else "Other"
        print(f"{i:3} | {typ:10} | {line}")
    print("-" * 60)

    choice = input("\n1 = Scan ALL   2 = Scan ONE range   [1]: ").strip() or "1"

    if choice == "2":
        while True:
            sel = input(f"Enter number (1-{len(lines)}): ").strip()
            try:
                num = int(sel)
                if 1 <= num <= len(lines):
                    selected = lines[num-1]
                    print(f"→ Selected: {selected}")
                    all_ips = all_ips_from_cidr(selected)
                    if not all_ips:
                        print("Invalid range → exiting")
                        return
                    break
                else:
                    print(f"Number must be 1-{len(lines)}")
            except ValueError:
                print("Enter a valid number")
    else:
        all_ips = collect_all_ips(lines)
        print(f"→ Scanning ALL ({len(all_ips):,} IPs)")

    if not all_ips:
        print("No IPs to scan.")
        return

    print(f"\nTotal IPs: {len(all_ips):,} | Batch: {BATCH_SIZE} | Workers: {MAX_WORKERS}\n")

    stop_event = threading.Event()

    def wait_for_stop():
        print("\nPress Enter to stop scanning")
        input()
        stop_event.set()

    threading.Thread(target=wait_for_stop, daemon=True).start()

    good_queue = Queue()
    results: List[Dict] = []

    printer_thread = threading.Thread(
        target=live_good_ips_printer,
        args=(good_queue, stop_event, MAX_PING),
        daemon=True
    )
    printer_thread.start()

    found_count = 0
    current_batch = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for start in range(0, len(all_ips), BATCH_SIZE):
            if stop_event.is_set():
                break

            batch = all_ips[start:start + BATCH_SIZE]
            futures = [executor.submit(test_ip_advanced, ip) for ip in batch]

            for future in concurrent.futures.as_completed(futures):
                if stop_event.is_set():
                    break
                res = future.result()
                if res:
                    results.append(res)
                    good_queue.put(res)
                    save_realtime(res['ip'])
                    found_count += 1

            current_batch += len(batch)
            show_progress(current_batch, len(all_ips), found_count)

    stop_event.set()
    printer_thread.join(timeout=2.0)

    print(f"\n\nScan finished. Good IPs found: {found_count:,}")

    save_top_ips(results, MAX_PING)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScan stopped by user. Good IPs saved realtime to good_ips.txt")
    except Exception as e:
        print(f"\nError: {e}")
