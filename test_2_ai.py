# test_2_ai.py - 生肖智能预测版（无降权版）
import json
from collections import defaultdict
from typing import Dict, List, Tuple
import os

DATA_DIR = r"D:\lottery_ai\mark6"

ZODIAC = ['马', '蛇', '龙', '兔', '虎', '牛', '鼠', '猪', '狗', '鸡', '猴', '羊']
ZODIAC_IDX = {z: i for i, z in enumerate(ZODIAC)}

def get_zodiac_by_number(num: int, year: int) -> str:
    zodiac_list = ['马', '蛇', '龙', '兔', '虎', '牛', '鼠', '猪', '狗', '鸡', '猴', '羊']
    idx = (num - 1) % 12
    return zodiac_list[idx]

def get_te_ma_zodiac(rec: dict, year: int) -> str:
    codes = rec.get('openCode', '').split(',')
    if not codes:
        return None
    return get_zodiac_by_number(int(codes[-1]), year)

def get_second_zodiac(rec: dict, year: int) -> str:
    codes = rec.get('openCode', '').split(',')
    if len(codes) < 2:
        return None
    return get_zodiac_by_number(int(codes[1]), year)

def get_prev_zodiac(zodiac: str, steps: int) -> str:
    """获取某个生肖往前数N位的生肖（不包括本身）"""
    idx = ZODIAC_IDX[zodiac]
    new_idx = (idx + steps) % 12
    return ZODIAC[new_idx]

def model_basic(data: List[dict], year: int) -> Dict:
    trans = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for i in range(len(data) - 1):
        cur = get_te_ma_zodiac(data[i], year)
        nxt = get_te_ma_zodiac(data[i + 1], year)
        if cur and nxt:
            trans[cur][nxt] += 1
            total[cur] += 1
    prob = {}
    for cur, nxts in trans.items():
        prob[cur] = {n: round((c / total[cur]) * 100, 2) for n, c in nxts.items()}
    return prob

def model_weighted(data: List[dict], year: int) -> Dict:
    weighted = defaultdict(lambda: defaultdict(float))
    total_w = defaultdict(float)
    for i in range(len(data) - 1):
        cur = get_te_ma_zodiac(data[i], year)
        nxt = get_te_ma_zodiac(data[i + 1], year)
        if not cur or not nxt:
            continue
        dist = len(data) - 1 - i
        w = 1.5 if dist <= 12 else (1.2 if dist <= 24 else 1.0)
        weighted[cur][nxt] += w
        total_w[cur] += w
    prob = {}
    for cur, nxts in weighted.items():
        prob[cur] = {n: round((v / total_w[cur]) * 100, 2) for n, v in nxts.items()}
    return prob

def model_second(data: List[dict], year: int) -> Dict:
    trans = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for i in range(len(data) - 2):
        z1 = get_te_ma_zodiac(data[i], year)
        z2 = get_te_ma_zodiac(data[i + 1], year)
        z3 = get_te_ma_zodiac(data[i + 2], year)
        if z1 and z2 and z3:
            trans[(z1, z2)][z3] += 1
            total[(z1, z2)] += 1
    prob = {}
    for combo, nxts in trans.items():
        prob[combo] = {n: round((c / total[combo]) * 100, 2) for n, c in nxts.items()}
    return prob

def model_number(data: List[dict], year: int) -> Dict:
    trans = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for i in range(len(data) - 1):
        codes = data[i].get('openCode', '').split(',')
        if not codes:
            continue
        cur_num = int(codes[-1])
        nxt = get_te_ma_zodiac(data[i + 1], year)
        if nxt:
            trans[cur_num][nxt] += 1
            total[cur_num] += 1
    prob = {}
    for num, nxts in trans.items():
        prob[num] = {n: round((c / total[num]) * 100, 2) for n, c in nxts.items()}
    return prob

def main():
    all_data = []
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        fp = os.path.join(DATA_DIR, f"{year}.json")
        if os.path.exists(fp):
            data = json.load(open(fp, 'r', encoding='utf-8')).get('data', [])
            for r in data:
                r['_year'] = year
            all_data.extend(data)
            print(f"[OK] Loaded {year}: {len(data)} records")
    
    all_data.sort(key=lambda x: x.get('openTime', ''))
    last = all_data[-1]
    prev = all_data[-2] if len(all_data) > 1 else last
    year = last.get('_year', 2026)
    
    cur_zodiac = get_te_ma_zodiac(last, year)
    prev_zodiac = get_te_ma_zodiac(prev, year)
    second_zodiac = get_second_zodiac(last, year)
    
    # 杀肖计算
    kill1 = second_zodiac                          # 平二肖
    kill2 = get_prev_zodiac(second_zodiac, 3) if second_zodiac else None  # 逆数3
    kill3 = cur_zodiac                             # 本期特肖
    
    kill_zodiacs = [k for k in [kill1, kill2, kill3] if k]
    # 去重
    kill_zodiacs = list(dict.fromkeys(kill_zodiacs))
    
    # 不再使用降权，设为空列表
    weight_reduce_zodiacs = []
    
    modelA = model_basic(all_data, year)
    modelB = model_weighted(all_data, year)
    modelC = model_second(all_data, year)
    modelD = model_number(all_data, year)
    
    # 多模型投票（无降权）
    scores = defaultdict(float)
    if cur_zodiac in modelA:
        for z, p in modelA[cur_zodiac].items():
            if z not in kill_zodiacs:
                scores[z] += p * 0.30
    if cur_zodiac in modelB:
        for z, p in modelB[cur_zodiac].items():
            if z not in kill_zodiacs:
                scores[z] += p * 0.30
    if (prev_zodiac, cur_zodiac) in modelC:
        for z, p in modelC[(prev_zodiac, cur_zodiac)].items():
            if z not in kill_zodiacs:
                scores[z] += p * 0.20
    # 获取特码号码
    codes = last.get('openCode', '').split(',')
    te_ma = int(codes[-1]) if codes else 0
    if te_ma in modelD:
        for z, p in modelD[te_ma].items():
            if z not in kill_zodiacs:
                scores[z] += p * 0.20
    
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = [(z, round(s, 2)) for z, s in sorted_scores[:6]]
    
    print(f"\n[ZAI v1.0 Prediction]")
    print(f"Kill: {', '.join(kill_zodiacs)}")
    for i, (z, s) in enumerate(results, 1):
        print(f"  {i}. {z} (score: {s})")
    
    # 构建所有生肖得分字典
    all_scores = {z: round(scores.get(z, 0), 2) for z in ZODIAC}

    report = {
        'kill_zodiacs': kill_zodiacs,
        'weight_reduce_zodiacs': weight_reduce_zodiacs,
        'multi_model_vote_results': [{'zodiac': z, 'score': s} for z, s in results],
        'all_zodiac_scores': all_scores   # 新增：所有生肖的得分
    }
    with open('zodiac_ai_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n[OK] Report saved")

if __name__ == "__main__":
    main()