# combine_predict.py - 合并预测入口（动态尾数版）
import json
import os
import subprocess
import sys
from datetime import datetime

BASE_DIR = r"D:\lottery_ai"
DATA_DIR = os.path.join(BASE_DIR, "mark6")
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

ZODIAC = ['马', '蛇', '龙', '兔', '虎', '牛', '鼠', '猪', '狗', '鸡', '猴', '羊']
ZODIAC_NUMBERS = {
    '马': [1,13,25,37,49], '蛇': [2,14,26,38], '龙': [3,15,27,39],
    '兔': [4,16,28,40], '虎': [5,17,29,41], '牛': [6,18,30,42],
    '鼠': [7,19,31,43], '猪': [8,20,32,44], '狗': [9,21,33,45],
    '鸡': [10,22,34,46], '猴': [11,23,35,47], '羊': [12,24,36,48]
}

def update_data():
    sys.path.insert(0, BASE_DIR)
    from update_data import update_2026_data
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        result = update_2026_data()
    finally:
        sys.stdout.close()
        sys.stdout = original_stdout
    return result

def run_model(script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.exists(script_path):
        return False
    with open(os.devnull, 'w') as devnull:
        return subprocess.run([sys.executable, script_path], stdout=devnull, stderr=devnull).returncode == 0

def load_report(report_name):
    report_path = os.path.join(BASE_DIR, report_name)
    if not os.path.exists(report_path):
        return None
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def get_latest_record():
    file_path = os.path.join(DATA_DIR, "2026.json")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            records = json.load(f).get('data', [])
            if records:
                return sorted(records, key=lambda x: x.get('openTime', ''), reverse=True)[0]
    except:
        pass
    return None

def get_all_tail_scores():
    """直接从文件读取所有尾数的得分（10个），缺失的补0"""
    try:
        file_path = os.path.join(BASE_DIR, 'tail_ai_analysis_report.json')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scores = data.get('all_tail_scores', {})
            return {t: float(scores.get(str(t), 0)) for t in range(10)}
    except Exception as e:
        print(f"读取尾数报告失败: {e}")
        return {t: 0 for t in range(10)}

def get_tail_range_dynamic(current_tail, tail_scores):
    if not tail_scores:
        return [0,1,2,3,4,5,6]
    
    sorted_tails = sorted(tail_scores.items(), key=lambda x: x[1], reverse=True)
    prob_list = [t for t, _ in sorted_tails]
    
    if current_tail not in prob_list:
        prob_list = list(range(10))
        prob_list = sorted(prob_list, key=lambda t: tail_scores.get(t, 0), reverse=True)
    
    length = len(prob_list)
    start_idx = prob_list.index(current_tail)
    
    if current_tail == 9:
        center_idx = (start_idx - 9 + 1 + length) % length
    else:
        center_idx = (start_idx + 9 - 1) % length
    
    center = prob_list[center_idx]
    center_pos = prob_list.index(center)
    
    result = []
    for i in range(4):
        idx = (center_pos + i) % length
        result.append(prob_list[idx])
    for i in range(1, 4):
        idx = (center_pos - i + length) % length
        result.append(prob_list[idx])
    
    seen = set()
    ordered_result = []
    for x in result:
        if x not in seen:
            seen.add(x)
            ordered_result.append(x)
    
    return ordered_result

def get_zodiac_top6(zodiac_report):
    if not zodiac_report:
        return []
    return [r.get('zodiac') for r in zodiac_report.get('multi_model_vote_results', [])[:6] if r.get('zodiac')]

def get_all_zodiac_scores(zodiac_report):
    if not zodiac_report:
        return {}
    return zodiac_report.get('all_zodiac_scores', {})

def get_zodiac_by_num(num):
    return ZODIAC[(num - 1) % 12]

def generate_numbers_by_tails_and_zodiac(tail_list, zodiac_list):
    """
    新逻辑：
    1. 收集六肖的所有号码
    2. 按尾数权重从高到低排序
    3. 取前12个
    4. 按生肖分组返回
    """
    if not zodiac_list:
        return [], {}
    
    tail_numbers = set()
    for tail in tail_list:
        for n in range(1, 50):
            if n % 10 == tail:
                tail_numbers.add(n)
    
    # 构建尾数权重：位置越靠前权重越高
    tail_weight = {tail: len(tail_list) - i for i, tail in enumerate(tail_list)}
    
    # 收集六肖的所有号码，计算权重
    candidates = []
    for z in zodiac_list:
        for n in ZODIAC_NUMBERS.get(z, []):
            if n in tail_numbers:
                weight = tail_weight.get(n % 10, 0)
                candidates.append((n, weight, z))
    
    # 按尾数权重从高到低排序
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # 取前12个
    selected_numbers = [c[0] for c in candidates[:12]]
    
    # 按生肖分组用于显示
    matched_by_zodiac = {}
    for num in selected_numbers:
        z = get_zodiac_by_num(num)
        if z not in matched_by_zodiac:
            matched_by_zodiac[z] = []
        matched_by_zodiac[z].append(num)
    
    return selected_numbers, matched_by_zodiac

def generate_output_text():
    update_data()
    run_model("test_1_ai.py")
    run_model("test_2_ai.py")
    
    tail_report = load_report("tail_ai_analysis_report.json")
    zodiac_report = load_report("zodiac_ai_analysis_report.json")
    latest = get_latest_record()
    
    all_tail_scores = get_all_tail_scores()
    
    current_tail = 0
    if latest:
        codes = latest.get('openCode', '').split(',')
        if codes:
            current_tail = int(codes[-1]) % 10
    
    tail_list = get_tail_range_dynamic(current_tail, all_tail_scores)
    
    zodiac_top6 = get_zodiac_top6(zodiac_report)
    all_zodiac_scores = get_all_zodiac_scores(zodiac_report)
    kill = zodiac_report.get('kill_zodiacs', []) if zodiac_report else []
    
    numbers, matched_by_zodiac = generate_numbers_by_tails_and_zodiac(tail_list, zodiac_top6)
    
    open_code = latest.get('openCode', '') if latest else ''
    codes = open_code.split(',') if open_code else []
    pingma = [int(c) for c in codes[:6]] if len(codes) >= 6 else []
    tema = int(codes[-1]) if codes else 0
    tema_zodiac = get_zodiac_by_num(tema) if tema else ''
    
    expect = latest.get('expect', '') if latest else ''
    if expect and len(expect) >= 5:
        next_num = int(expect[4:]) + 1
        next_qihao = f"{expect[:4]}{next_num:03d}"
    else:
        next_qihao = ''
    
    open_time = latest.get('openTime', '') if latest else ''
    open_date = open_time.split(' ')[0] if ' ' in open_time else open_time[:10]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines = []
    lines.append("=" * 45)
    lines.append(f"预测时间: {current_time}")
    lines.append("=" * 45)
    lines.append(f"最新期号: {expect}")
    lines.append(f"开奖日期: {open_date}")
    lines.append("")
    lines.append(f"平码: {pingma}")
    lines.append(f"特码: {tema} ({tema_zodiac})")
    lines.append("-" * 30)
    lines.append(f"预测下一期: {next_qihao}")
    lines.append("-" * 30)
    
    # 尾数投票和生肖投票并排显示
    lines.append("\n【尾数投票从高到低】                    【生肖投票从高到低】")
    sorted_tails = sorted(all_tail_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_zodiacs = sorted(all_zodiac_scores.items(), key=lambda x: x[1], reverse=True)
    max_lines = max(len(sorted_tails), len(sorted_zodiacs))
    for i in range(max_lines):
        left = f"   {sorted_tails[i][0]}: {sorted_tails[i][1]}" if i < len(sorted_tails) else " " * 15
        right = f"   {sorted_zodiacs[i][0]}: {sorted_zodiacs[i][1]}" if i < len(sorted_zodiacs) else ""
        lines.append(f"{left:<28} {right}")
    
    # 动态尾数预测
    lines.append(f"\n【动态尾数预测】")
    lines.append(f"   当前尾数: {current_tail}")
    lines.append(f"   预测7个尾数: {tail_list}")
    
    # 大范围生肖
    kill_str = '、'.join(kill) if kill else '无'
    lines.append(f"\n【大范围生肖】(排除杀肖: {kill_str})")
    remain_zodiacs = [z for z in ZODIAC if z not in kill]
    remain_zodiacs_sorted = sorted(remain_zodiacs, key=lambda z: all_zodiac_scores.get(z, 0), reverse=True)
    lines.append("   " + "  ".join(remain_zodiacs_sorted))
    
    # 重点候选生肖
    lines.append("\n【重点候选生肖】")
    if zodiac_top6:
        zodiac_top6_sorted = sorted(zodiac_top6, key=lambda z: all_zodiac_scores.get(z, 0), reverse=True)
        lines.append("   " + "  ".join(zodiac_top6_sorted))
    else:
        lines.append("   无")
    
    # 12个候选号码（按尾数权重排序后取前12）
    lines.append("\n【12个候选号码】")
    # 按生肖评分顺序显示
    zodiac_top6_sorted = sorted(zodiac_top6, key=lambda z: all_zodiac_scores.get(z, 0), reverse=True)
    for z in zodiac_top6_sorted:
        if z in matched_by_zodiac:
            lines.append(f"   {z}: {', '.join(map(str, sorted(matched_by_zodiac[z])))}")
        else:
            lines.append(f"   {z}: (无交集号码)")
    
    lines.append("\n" + "=" * 45)
    
    return "\n".join(lines)

def main():
    print("正在生成预测报告，请稍候...")
    output = generate_output_text()
    
    log_path = os.path.join(LOG_DIR, "prediction_history.txt")
    run_date = datetime.now().strftime('%Y-%m-%d')
    
    need_save = True
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if f"## 运行日期: {run_date}" in content:
                need_save = False
                print("[SKIP] 今日已有预测记录，跳过保存")
    
    if need_save:
        separator = "=" * 45
        history_entry = f"""
{separator}
## 运行日期: {run_date}
{output}
"""
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(history_entry)
        print(f"[OK] 已保存到: {log_path}")
    
    print("\n" + "=" * 45)
    print("预测完成！结果如下：")
    print("=" * 45)
    print(output)

if __name__ == "__main__":
    main()