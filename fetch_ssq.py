"""
双色球数据抓取脚本 v3 - 强化版
- 多源 + 重试
- 失败不覆盖现有数据
- 合并所有期,保留早期期
"""
import sys
import json
import os
import re
import time

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先 pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


def fetch_with_retry(url, headers=None, max_retry=3, timeout=15):
    headers = headers or {"User-Agent": "Mozilla/5.0"}
    for i in range(max_retry):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.encoding = r.apparent_encoding
            if r.status_code == 200 and len(r.text) > 1000:
                return r.text
        except Exception as e:
            print(f"  重试 {i+1}/{max_retry}: {e}", file=sys.stderr)
            time.sleep(1)
    return None


def normalize_period(p):
    if not p: return ""
    p = str(p).strip()
    if p.startswith("2026") and len(p) == 8:
        return "2026" + p[4:]
    return p


def fetch_from_500():
    url = "https://datachart.500.com/ssq/history/history.shtml"
    html = fetch_with_retry(url)
    if not html: return []
    try:
        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody", id="tdata")
        if not tbody: return []
        results = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8: continue
            period_raw = tds[0].get_text(strip=True)
            if len(period_raw) == 5 and period_raw.isdigit():
                period = "20" + period_raw[:2] + period_raw[2:]
            elif len(period_raw) == 7 and period_raw.startswith("2026"):
                period = period_raw
            else:
                continue
            try:
                reds = [int(tds[i].get_text(strip=True)) for i in range(1, 7)]
                blue = int(tds[7].get_text(strip=True))
                date = tds[15].get_text(strip=True) if len(tds) > 15 else ""
                if len(reds) == 6 and 1 <= blue <= 16 and all(1 <= r <= 33 for r in reds):
                    results.append({"period": period, "reds": reds, "blue": blue, "date": date})
            except: continue
        results.sort(key=lambda x: x["period"])
        return results
    except Exception as e:
        print(f"  500.com 解析失败: {e}", file=sys.stderr)
        return []


def fetch_from_17500():
    url = "https://www.17500.cn/ssq/all2009.php"
    html = fetch_with_retry(url)
    if not html: return []
    try:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8: continue
            period_raw = tds[0].get_text(strip=True)
            if len(period_raw) == 5 and period_raw.isdigit():
                period = "20" + period_raw[:2] + period_raw[2:]
            elif len(period_raw) == 7 and period_raw.startswith("2026"):
                period = period_raw
            else:
                continue
            try:
                reds = [int(tds[i].get_text(strip=True)) for i in range(1, 7)]
                blue = int(tds[7].get_text(strip=True))
                if len(reds) == 6 and 1 <= blue <= 16 and all(1 <= r <= 33 for r in reds):
                    results.append({"period": period, "reds": reds, "blue": blue, "date": ""})
            except: continue
        seen = set()
        unique = []
        for r in results:
            if r["period"] not in seen:
                seen.add(r["period"])
                unique.append(r)
        unique.sort(key=lambda x: x["period"])
        return unique
    except Exception as e:
        print(f"  17500.cn 解析失败: {e}", file=sys.stderr)
        return []


def main():
    print("🔍 拉取双色球数据...", file=sys.stderr)
    all_data = []

    print("  [1/2] 500.com...", file=sys.stderr)
    d1 = fetch_from_500()
    print(f"    -> {len(d1)} 期", file=sys.stderr)
    all_data.extend(d1)

    if len(d1) < 50:
        print("  [2/2] 17500.cn(补全)...", file=sys.stderr)
        d2 = fetch_from_17500()
        print(f"    -> {len(d2)} 期", file=sys.stderr)
        all_data.extend(d2)

    out_path = os.path.join(os.path.dirname(__file__), "ssq_data.json")

    # 关键: 读取现有数据(保留你之前手动加的早期期)
    existing = []
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            print(f"  现有 {len(existing)} 期,保留合并", file=sys.stderr)
        except Exception as e:
            print(f"  读取现有失败: {e}", file=sys.stderr)

    # 合并去重: 云端新数据优先
    seen = {}
    for d in existing:
        norm_p = normalize_period(d["period"])
        d["period"] = norm_p
        seen[norm_p] = d
    for d in all_data:
        norm_p = normalize_period(d["period"])
        d["period"] = norm_p
        seen[norm_p] = d  # 云端覆盖 existing 同期的数据
    unique = sorted(seen.values(), key=lambda x: x["period"])

    if not unique:
        print("❌ 没有数据", file=sys.stderr)
        return 0

    # 写回
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"💾 合并后共 {len(unique)} 期", file=sys.stderr)
    if unique:
        print(f"   范围: {unique[0]['period']} ~ {unique[-1]['period']}", file=sys.stderr)
        print(f"   最新: {unique[-1]['period']} 红{unique[-1]['reds']} 蓝{unique[-1]['blue']}", file=sys.stderr)
    return len(unique)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(0)  # 失败也 exit 0,不阻止 commit
