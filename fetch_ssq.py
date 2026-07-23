"""
双色球数据抓取脚本
"""
import sys
import json
import os
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先 pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


def fetch_from_500():
    url = "https://datachart.500.com/ssq/history/history.shtml"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        tbody = soup.find("tbody", id="tdata")
        if not tbody:
            return []
        results = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8:
                continue
            period_raw = tds[0].get_text(strip=True)
            if not period_raw.startswith("26"):
                continue
            period = "2026" + period_raw
            try:
                reds = [int(tds[i].get_text(strip=True)) for i in range(1, 7)]
                blue = int(tds[7].get_text(strip=True))
                date = tds[15].get_text(strip=True) if len(tds) > 15 else ""
                if len(reds) == 6 and 1 <= blue <= 16 and all(1 <= r <= 33 for r in reds):
                    results.append({"period": period, "reds": reds, "blue": blue, "date": date})
            except (ValueError, IndexError):
                continue
        results.sort(key=lambda x: x["period"])
        return results
    except Exception as e:
        print(f"500.com 失败: {e}", file=sys.stderr)
        return []


def fetch_from_17500():
    url = "https://www.17500.cn/ssq/all2009.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8:
                continue
            period_raw = tds[0].get_text(strip=True)
            if not re.match(r"^20\d{7}$", period_raw) and not period_raw.startswith("2026"):
                continue
            try:
                if period_raw.startswith("26") and len(period_raw) == 5:
                    period = "2026" + period_raw
                else:
                    period = period_raw
                reds = [int(tds[i].get_text(strip=True)) for i in range(1, 7)]
                blue = int(tds[7].get_text(strip=True))
                if len(reds) == 6 and 1 <= blue <= 16 and all(1 <= r <= 33 for r in reds):
                    results.append({"period": period, "reds": reds, "blue": blue, "date": ""})
            except (ValueError, IndexError):
                continue
        seen = set()
        unique = []
        for r in results:
            if r["period"] not in seen:
                seen.add(r["period"])
                unique.append(r)
        unique.sort(key=lambda x: x["period"])
        return unique
    except Exception as e:
        print(f"17500.cn 失败: {e}", file=sys.stderr)
        return []


def fetch_ssq_data():
    print("🔍 拉取数据...", file=sys.stderr)
    d1 = fetch_from_500()
    print(f"  500.com: {len(d1)}", file=sys.stderr)
    d2 = fetch_from_17500()
    print(f"  17500.cn: {len(d2)}", file=sys.stderr)
    all_data = d1 + d2
    seen, unique = set(), []
    for d in all_data:
        if d["period"] not in seen and d["period"].startswith("2026"):
            seen.add(d["period"])
            unique.append(d)
    unique.sort(key=lambda x: x["period"])
    print(f"  合并: {len(unique)} 期", file=sys.stderr)
    return unique


if __name__ == "__main__":
    data = fetch_ssq_data()
    out = os.path.join(os.path.dirname(__file__), "ssq_data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存: {len(data)} 期, 最新: {data[-1]['period'] if data else '无'}")
