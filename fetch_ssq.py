"""
双色球数据抓取脚本 v7 - 5 源兜底
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


GITHUB_RAW = "https://raw.githubusercontent.com/mz18607358885-cpu/ssq-data/main/ssq_data.json"


def normalize_period(p):
    if not p: return ""
    p = str(p).strip()
    if len(p) == 5 and p.isdigit():
        return "20" + p[:2] + p[2:]
    if p.startswith("2026") and len(p) == 8:
        return "2026" + p[4:]
    return p


def fetch_github():
    try:
        r = requests.get(GITHUB_RAW, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"  [GitHub] 拉到 {len(data)} 期", file=sys.stderr)
                return data
    except Exception as e:
        print(f"  [GitHub] 失败: {e}", file=sys.stderr)
    return []


def fetch_500():
    url = "https://datachart.500.com/ssq/history/history.shtml"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.encoding = r.apparent_encoding
        if r.status_code != 200 or len(r.text) < 1000: return []
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
                if len(reds) != 6 or not (1 <= blue <= 16) or not all(1 <= r <= 33 for r in reds): continue
                date = tds[15].get_text(strip=True) if len(tds) > 15 else ""
                results.append({"period": period, "reds": reds, "blue": blue, "date": date})
            except: continue
        results.sort(key=lambda x: x["period"])
        if results: print(f"  [500.com] 拉到 {len(results)} 期", file=sys.stderr)
        return results
    except Exception as e:
        print(f"  [500.com] 失败: {e}", file=sys.stderr)
        return []


def fetch_sina():
    url = "https://lotto.sina.cn/trend/qxc_qlc_proxy.d.html?lottoType=ssq&actionType=chzs&type=120"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.encoding = r.apparent_encoding
        if r.status_code != 200 or len(r.text) < 1000: return []
        soup = BeautifulSoup(r.text, "html.parser")
        cpdata = soup.find(id="cpdata")
        if not cpdata: return []
        results = []
        for tr in cpdata.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 21: continue
            period = tds[0].get_text(strip=True)
            if not (period.startswith("20") and len(period) == 7): continue
            reds = []
            blue = None
            for i, td in enumerate(tds):
                cls = td.get("class")
                cls_name = cls[0] if cls else ""
                if cls_name in ("chartball01", "chartball20") and 4 <= i <= 38:
                    try:
                        v = int(td.get_text(strip=True))
                        if 1 <= v <= 33: reds.append(v)
                    except: pass
                elif cls_name == "chartball02" and 40 <= i <= 55:
                    try:
                        v = int(td.get_text(strip=True))
                        if 1 <= v <= 16 and blue is None: blue = v
                    except: pass
            if len(reds) == 6 and blue is not None:
                results.append({"period": period, "reds": reds, "blue": blue, "date": ""})
        results.sort(key=lambda x: x["period"])
        if results: print(f"  [新浪] 拉到 {len(results)} 期", file=sys.stderr)
        return results
    except Exception as e:
        print(f"  [新浪] 失败: {e}", file=sys.stderr)
        return []


def fetch_17500():
    url = "https://www.17500.cn/ssq/all2009.php"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.encoding = r.apparent_encoding
        if r.status_code != 200 or len(r.text) < 1000: return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8: continue
            period = normalize_period(tds[0].get_text(strip=True))
            if not period.startswith("2026") or len(period) != 7: continue
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
        if unique: print(f"  [乐彩网] 拉到 {len(unique)} 期", file=sys.stderr)
        return unique
    except Exception as e:
        print(f"  [乐彩网] 失败: {e}", file=sys.stderr)
        return []


def fetch_zhcw():
    url = "https://www.zhcw.com/ssq/"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.encoding = r.apparent_encoding
        if r.status_code != 200 or len(r.text) < 1000: return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 8: continue
                period = normalize_period(tds[0].get_text(strip=True))
                if not period.startswith("2026") or len(period) != 7: continue
                try:
                    reds = [int(tds[i].get_text(strip=True)) for i in range(1, 7)]
                    blue = int(tds[7].get_text(strip=True))
                    if len(reds) == 6 and 1 <= blue <= 16 and all(1 <= r <= 33 for r in reds):
                        results.append({"period": period, "reds": reds, "blue": blue, "date": ""})
                except: continue
        if results:
            seen = set()
            unique = []
            for r in results:
                if r["period"] not in seen:
                    seen.add(r["period"])
                    unique.append(r)
            unique.sort(key=lambda x: x["period"])
            print(f"  [中彩网] 拉到 {len(unique)} 期", file=sys.stderr)
            return unique
    except Exception as e:
        print(f"  [中彩网] 失败: {e}", file=sys.stderr)
    return []


def main():
    print("v7 拉取数据中...", file=sys.stderr)
    data = fetch_github() or fetch_500() or fetch_sina() or fetch_17500() or fetch_zhcw()
    out_path = os.path.join(os.path.dirname(__file__), "ssq_data.json")
    if data:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已写 {len(data)} 期,最新 {data[-1]['period']}", file=sys.stderr)
    else:
        print("⚠️ 5 源都失败,保留现有", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try: main()
    except: pass
    sys.exit(0)
