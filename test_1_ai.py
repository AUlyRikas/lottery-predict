# test_1_ai.py - 尾数智能预测版（完整版，输出10个尾数得分）
import json
from collections import defaultdict
from typing import Dict, List, Tuple
import os

DATA_DIR = r"D:\lottery_ai\mark6"

def load_data(file_path: str) -> List[dict]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('data', [])
    except:
        return []

def get_te_ma_tail(record: dict) -> int:
    open_code = record.get('openCode', '')
    if not open_code:
        return None
    codes = open_code.split(',')
    if not codes:
        return None
    return int(codes[-1]) % 10

def model_basic_transition(data: List[dict]) -> Dict:
    transition = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for i in range(len(data) - 1):
        cur = get_te_ma_tail(data[i])
        nxt = get_te_ma_tail(data[i + 1])
        if cur is not None and nxt is not None:
            transition[cur][nxt] += 1
            total[cur] += 1
    prob = {}
    for cur, nxts in transition.items():
        prob[cur] = {n: round((c / total[cur]) * 100, 2) for n, c in nxts.items()}
    return prob

def model_weighted_trend(data: List[dict]) -> Dict:
    weighted = defaultdict(lambda: defaultdict(float))
    total_w = defaultdict(float)
    for i in range(len(data) - 1):
        cur = get_te_ma_tail(data[i])
        nxt = get_te_ma_tail(data[i + 1])
        if cur is None or nxt is None:
            continue
        dist = len(data) - 1 - i
        w = 1.5 if dist <= 12 else (1.2 if dist <= 24 else 1.0)
        weighted[cur][nxt] += w
        total_w[cur] += w
    prob = {}
    for cur, nxts in weighted.items():
        prob[cur] = {n: round((v / total_w[cur]) * 100, 2) for n, v in nxts.items()}
    return prob

def model_second_order(data: List[dict]) -> Dict:
    trans = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for i in range(len(data) - 2):
        cur1 = get_te_ma_tail(data[i])
        cur2 = get_te_ma_tail(data[i + 1])
        nxt = get_te_ma_tail(data[i + 2])
        if cur1 is not None and cur2 is not None and nxt is not None:
            trans[(cur1, cur2)][nxt] += 1
            total[(cur1, cur2)] += 1
    prob = {}
    for combo, nxts in trans.items():
        prob[combo] = {n: round((c / total[combo]) * 100, 2) for n, c in nxts.items()}
    return prob

def model_volatility(data: List[dict]) -> Dict:
    trans = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for i in range(len(data) - 1):
        cur = get_te_ma_tail(data[i])
        nxt = get_te_ma_tail(data[i + 1])
        if cur is not None and nxt is not None:
            trans[cur][nxt] += 1
            total[cur] += 1
    prob = {}
    for cur, nxts in trans.items():
        prob[cur] = {n: round((c / total[cur]) * 100, 2) for n, c in nxts.items()}
    return prob

def get_volatility_range(tail: int) -> List[int]:
    return list(range(max(0, tail-3), min(9, tail+3)+1))

def multi_model_vote(cur, prev, modelA, modelB, modelC, modelD, range_tails):
    scores = defaultdict(float)
    
    if cur in modelA:
        for t, p in modelA[cur].items():
            scores[t] += p * 0.30
    if cur in modelB:
        for t, p in modelB[cur].items():
            scores[t] += p * 0.30
    if (prev, cur) in modelC:
        for t, p in modelC[(prev, cur)].items():
            scores[t] += p * 0.20
    if cur in modelD:
        for t, p in modelD[cur].items():
            scores[t] += p * 0.20
    for t in range_tails:
        scores[t] += 5.0
    
    # 确保所有10个尾数都有得分
    all_scores = {}
    for t in range(10):
        all_scores[t] = round(scores.get(t, 0), 2)
    
    # 按得分从高到低排序
    sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    results = [(t, s) for t, s in sorted_scores[:7]]
    
    return results, all_scores

def main():
    all_data = []
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        fp = os.path.join(DATA_DIR, f"{year}.json")
        if os.path.exists(fp):
            data = load_data(fp)
            all_data.extend(data)
            print(f"[OK] Loaded {year}: {len(data)} records")
    print(f"Total: {len(all_data)} records")
    
    all_data.sort(key=lambda x: x.get('openTime', ''))
    last = all_data[-1]
    prev = all_data[-2] if len(all_data) > 1 else last
    
    cur_tail = get_te_ma_tail(last)
    prev_tail = get_te_ma_tail(prev)
    
    print(f"\nLatest: {last.get('expect')} | Tail: {cur_tail}")
    
    modelA = model_basic_transition(all_data)
    modelB = model_weighted_trend(all_data)
    modelC = model_second_order(all_data)
    modelD = model_volatility(all_data)
    range_tails = get_volatility_range(cur_tail)
    
    results, all_scores = multi_model_vote(cur_tail, prev_tail, modelA, modelB, modelC, modelD, range_tails)
    
    print("\n[TAI v1.0 Prediction]")
    for i, (t, s) in enumerate(results, 1):
        print(f"  {i}. Tail {t} (score: {s})")
    
    # 显示全部10个尾数得分
    print("\n[All Tails Score]")
    sorted_all = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    for t, s in sorted_all:
        print(f"  Tail {t}: {s}")
    
    report = {
        'multi_model_vote_results': [{'tail': t, 'score': s} for t, s in results],
        'all_tail_scores': all_scores
    }
    with open('tail_ai_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n[OK] Report saved")

if __name__ == "__main__":
    main()