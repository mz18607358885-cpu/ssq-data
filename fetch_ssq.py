"""
双色球数据抓取脚本 v5 - 最稳版
- 单源(500.com),失败不报错
"""
import sys
import json
import os

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install needed", file=sys.stderr)
    sys.exit(0)


def normalize_period(p):
    if not p: return ""
    p = str(p).strip()
    if len(p) == 5 and p.isdigit():
        return "20" + p[:2] + p[2:]
    if p.startswith("2026") and len(p) == 8:
        return "2026" + p[4:]
    return p


def fetch_500():
    url = "https://datachart.500.com/ssq/history/history.shtml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.encoding = r.apparent_encoding
        if r.status_code != 200: return []
        soup = BeautifulSoup(r.text, "html.parser")
        tbody = soup.find("tbody", id="tdata")
        if not tbody: return []
        results = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8: continue
            period = normalize_period(tds[0].get_text(strip=True))
            if not period.startswith("2026") or len(period) != 7: continue
            try:
                reds = [int(tds[i].get_text(strip=True)) for i in range(1, 7)]
                blue = int(tds[7].get_text(strip=True))
                if len(reds) != 6: continue
                if not (1 <= blue <= 16): continue
                if not all(1 <= r <= 33 for r in reds): continue
                results.append({"period": period, "reds": reds, "blue": blue, "date": ""})
            except: continue
        results.sort(key=lambda x: x["period"])
        return results
    except Exception as e:
        print(f"500.com fail: {e}", file=sys.stderr)
        return []


def main():
    print("拉数据中...", file=sys.stderr)
    data = fetch_500()
    print(f"500.com 拉 {len(data)} 期", file=sys.stderr)
    if not data:
        print("无数据,保持现状", file=sys.stderr)
        return 0
    out_path = os.path.join(os.path.dirname(__file__), "ssq_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已写 {len(data)} 期,最新 {data[-1]['period']}", file=sys.stderr)
    return len(data)


if __name__ == "__main__":
    try: main()
    except: pass
    sys.exit(0)  # 永远成功
