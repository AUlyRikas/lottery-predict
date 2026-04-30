# update_data.py - 数据更新模块
import json
import os
import urllib.request
from datetime import datetime

# 使用相对路径，兼容 GitHub Actions
DATA_DIR = os.path.join(os.path.dirname(__file__), "mark6")

def fetch_2026_data():
    url = "https://history.macaumarksix.com/history/macaujc2/y/2026"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('code') == 200 and 'data' in data:
                return data['data']
    except Exception as e:
        print(f"Fetch error: {e}")
    return []

def load_local(file_path):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f).get('data', [])
    except:
        return []

def save_local(file_path, data_list):
    data = {
        "result": True, "message": "OK", "code": 200,
        "data": data_list, "timestamp": int(datetime.now().timestamp() * 1000)
    }
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if os.path.exists(file_path):
        backup_path = file_path + ".bak"
        try:
            os.replace(file_path, backup_path)
            print(f"[OK] Backup: {os.path.basename(backup_path)}")
        except:
            pass
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved: {os.path.basename(file_path)}")

def merge_data(local, remote):
    d = {r.get('expect'): r for r in local if r.get('expect')}
    new = 0
    for r in remote:
        exp = r.get('expect')
        if exp and exp not in d:
            new += 1
        d[exp] = r
    return sorted(d.values(), key=lambda x: x.get('expect', '')), new

def update_2026_data():
    fp = os.path.join(DATA_DIR, "2026.json")
    local = load_local(fp)
    print(f"Local: {len(local)} records")
    remote = fetch_2026_data()
    if not remote:
        print("No remote data, skip")
        return len(local)
    print(f"Remote: {len(remote)} records")
    merged, new = merge_data(local, remote)
    if new > 0:
        print(f"New: {new} records")
        save_local(fp, merged)
    else:
        print("Already up to date")
    return len(merged)

if __name__ == "__main__":
    update_2026_data()
