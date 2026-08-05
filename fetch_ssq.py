"""
双色球数据抓取脚本 v10 - eastmoney 抓最新期
依赖: pip install requests
"""
import sys
import os
import json
import re
import subprocess
from datetime import datetime

try:
    import requests
except ImportError:
    print("pip install requests --break-system-packages", file=sys.stderr)
    sys.exit(0)

GITHUB_REPO = os.environ.get('GH_REPO', 'mz18607358885-cpu/ssq-data')
GITHUB_TOKEN = os.environ.get('GH_TOKEN', '').strip()
DATA_FILE = 'ssq_data.json'
EAST_MONEY_URL = 'http://caipiao.eastmoney.com/pub/result/category/ssq'


def fetch_existing_data():
    urls = [
        f'https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@main/{DATA_FILE}',
        f'https://raw.githubusercontent.com/{GITHUB_REPO}/main/{DATA_FILE}'
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200 and r.text.strip():
                data = json.loads(r.text)
                if isinstance(data, list) and data:
                    norm = []
                    for it in data:
                        period = it.get('period') or it.get('p') or it.get('lottery_no') or ''
                        reds = it.get('reds') or it.get('r') or []
                        blue = it.get('blue') or it.get('b')
                        date = it.get('date') or it.get('d') or ''
                        if period and len(reds) == 6 and blue:
                            p = str(period)
                            if len(p) == 5 and p.isdigit():
                                p = '20' + p
                            norm.append({'period': p, 'reds': [int(x) for x in reds], 'blue': int(blue), 'date': str(date)[:10]})
                    return norm
        except Exception as e:
            print(f'! {e}', file=sys.stderr)
    return []


def parse_eastmoney_html(html):
    if not html or len(html) < 1000: return []
    items = []
    for m in re.finditer(r'<div id="(20\d{5})" class="tabs-panel[^"]*">([\s\S]*?)(?=<div id="20|<div class="tabs-content")', html):
        issue = m.group(1); body = m.group(2)
        date_match = re.search(r'开奖日期：(\d{4}-\d{2}-\d{2})', body)
        date = date_match.group(1) if date_match else ''
        reds = [int(rm.group(1)) for rm in re.finditer(r'pellet-primary pellet-lg red">(\d{2})</span>', body)]
        blue_match = re.search(r'pellet-default pellet-lg blue">(\d{2})</span>', body)
        blue = int(blue_match.group(1)) if blue_match else None
        if len(reds) == 6 and blue and 1 <= blue <= 16:
            items.append({'period': issue, 'reds': reds, 'blue': blue, 'date': date})
    items.sort(key=lambda x: x['period'], reverse=True)
    return items


def fetch_eastmoney():
    try:
        r = requests.get(EAST_MONEY_URL, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            return parse_eastmoney_html(r.text)
    except Exception as e:
        print(f'! {e}', file=sys.stderr)
    return []


def merge_data(existing, new_items):
    by_period = {it['period']: it for it in existing}
    added = updated = 0
    for it in new_items:
        p = it['period']
        if p not in by_period: added += 1
        elif by_period[p].get('reds') != it.get('reds') or by_period[p].get('blue') != it.get('blue'):
            updated += 1
        by_period[p] = it
    return sorted(by_period.values(), key=lambda x: x['period']), added, updated


def main():
    print(f'=== {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===', file=sys.stderr)
    existing = fetch_existing_data()
    new_items = fetch_eastmoney()
    if not new_items: sys.exit(0)
    merged, added, updated = merge_data(existing, new_items)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, separators=(',', ':'))
    print(f'+{added}新期, ~{updated}更新, 最新{merged[-1]["period"]}', file=sys.stderr)
    # commit + push
    try:
        subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], check=True, capture_output=True)
        subprocess.run(['git', 'add', DATA_FILE], check=True, capture_output=True)
        diff = subprocess.run(['git', 'diff', '--cached', '--stat'], capture_output=True, text=True)
        if not diff.stdout.strip():
            print('✓ 无新数据', file=sys.stderr); return
        msg = f"auto: 更新到 {merged[-1]['period']} (+{added}新期, ~{updated}更新)"
        subprocess.run(['git', 'commit', '-m', msg], check=True, capture_output=True)
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        print('✓ push 成功', file=sys.stderr)
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        print(f'! git 错误: {err}', file=sys.stderr)


if __name__ == '__main__':
    main()
