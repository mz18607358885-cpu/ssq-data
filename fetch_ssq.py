
def main():
    print('=' * 50, file=sys.stderr)
    print(f'双色球数据 v11 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', file=sys.stderr)
    print('=' * 50, file=sys.stderr)
    # 1. 拉现有
    print('[1/4] 拉现有数据...', file=sys.stderr)
    existing = fetch_existing_data()
    # 2. 抓 ssqzj (快)
    print('[2/4] 抓 ssqzj.com...', file=sys.stderr)
    ssqzj_items = fetch_ssqzj()
    # 3. 抓 eastmoney
    print('[3/4] 抓 eastmoney...', file=sys.stderr)
    em_items = fetch_eastmoney()
    # 合并
    new_items = ssqzj_items + em_items
    if not new_items:
        print('  ! 所有源均失败', file=sys.stderr)
        sys.exit(0)
    # 按期号降序去重 (保留新抓的,ssqzj 优先)
    seen = {}
    for it in new_items:
        if it['period'] not in seen:
            seen[it['period']] = it
    new_items = sorted(seen.values(), key=lambda x: x['period'], reverse=True)
    print(f'  合并新数据: {len(new_items)} 期', file=sys.stderr)
    # 4. 合并 + 写
    print('[4/4] 合并数据...', file=sys.stderr)
    merged, added, updated = merge_data(existing, new_items)
    print(f'  合并后: {len(merged)} 期 (新增 {added} 期, 更新 {updated} 期)', file=sys.stderr)
    latest_issue = merged[-1]['period'] if merged else '0000000'
    print(f'  最新期: {latest_issue}', file=sys.stderr)
    # 写文件
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  ✓ {DATA_FILE} 已更新', file=sys.stderr)
    # git push
    try:
        subprocess.run(['git', 'config', 'user.name', 'ssq-bot'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'ssq@bot.local'], check=True, capture_output=True)
        subprocess.run(['git', 'add', DATA_FILE], check=True, capture_output=True)
        diff = subprocess.run(['git', 'diff', '--cached', '--stat'], capture_output=True, text=True)
        if not diff.stdout.strip():
            print('  ! 无新数据', file=sys.stderr)
            return
        msg = f"auto: 更新到 {latest_issue}"
        if added > 0: msg += f' (+{added}新期)'
        if updated > 0: msg += f' (~{updated}更新)'
        subprocess.run(['git', 'commit', '-m', msg], check=True, capture_output=True)
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        print(f'  ✓ push 成功: {msg}', file=sys.stderr)
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        print(f'  ! git 错误: {err}', file=sys.stderr)
if __name__ == '__main__':
    main()
