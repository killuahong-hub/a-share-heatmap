#!/usr/bin/env python3
"""
市场热力图V2数据更新脚本
增强：动量指标、板块轮动信号、市场均线、时间范围筛选
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, date, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO_ROOT, "docs")
API_URL = "https://sckd.dapanyuntu.com/api/api/industry_ma20_analysis_range"
CACHE_FILE = os.path.join(REPO_ROOT, "cache.json")
BJ_TZ = timezone(timedelta(hours=8))

INDUSTRY_CATEGORY_MAP = {
    # ── AI与数字服务（原TMT + 通信 + 计算机设备）──
    "软件开发": "AI与数字服务", "互联网服务": "AI与数字服务",
    "通信服务": "AI与数字服务", "通信设备": "AI与数字服务",
    "计算机设备": "AI与数字服务",
    "游戏": "AI与数字服务", "教育": "AI与数字服务", "文化传媒": "AI与数字服务",
    # ── 半导体（从电子独立）──
    "半导体": "半导体", "电子化学品": "半导体",
    # ── 电子硬件（电子 去掉半导体和电子化学品）──
    "光学光电子": "电子硬件", "消费电子": "电子硬件", "电子元件": "电子硬件",
    # ── 机械设备 ──
    "专用设备": "机械设备", "通用设备": "机械设备", "工程机械": "机械设备",
    "仪器仪表": "机械设备", "交运设备": "机械设备",
    # ── 电力设备 ──
    "光伏设备": "电力设备", "电池": "电力设备", "电源设备": "电力设备",
    "电网设备": "电力设备", "风电设备": "电力设备", "电机": "电力设备",
    # ── 医药生物（移除农药兽药）──
    "中药": "医药生物", "化学制药": "医药生物", "生物制品": "医药生物",
    "医疗器械": "医药生物", "医疗服务": "医药生物", "医药商业": "医药生物",
    # ── 基础化工（新增农药兽药）──
    "化学制品": "基础化工", "化学原料": "基础化工", "化肥行业": "基础化工",
    "化纤行业": "基础化工", "橡胶制品": "基础化工", "塑料制品": "基础化工",
    "非金属材料": "基础化工", "农药兽药": "基础化工",
    # ── 金融 ──
    "保险": "金融", "银行": "金融", "证券": "金融", "多元金融": "金融",
    # ── 有色金属 ──
    "小金属": "有色金属", "有色金属": "有色金属", "贵金属": "有色金属",
    "能源金属": "有色金属",
    # ── 汽车 ──
    "汽车整车": "汽车", "汽车服务": "汽车", "汽车零部件": "汽车",
    # ── 建筑装饰 ──
    "工程咨询服务": "建筑装饰", "工程建设": "建筑装饰",
    "装修装饰": "建筑装饰", "装修建材": "建筑装饰",
    # ── 房地产 ──
    "房地产开发": "房地产", "房地产服务": "房地产",
    # ── 交通运输 ──
    "物流行业": "交通运输", "航天航空": "交通运输", "航空机场": "交通运输",
    "航运港口": "交通运输", "铁路公路": "交通运输", "船舶制造": "交通运输",
    # ── 食品饮料 ──
    "酿酒行业": "食品饮料", "食品饮料": "食品饮料",
    # ── 家用电器 ──
    "家用轻工": "家用电器", "家电行业": "家用电器",
    # ── 建筑材料 ──
    "水泥建材": "建筑材料", "玻璃玻纤": "建筑材料", "钢铁行业": "建筑材料",
    # ── 能源（石油石化 + 煤炭）──
    "石油行业": "能源", "采掘行业": "能源", "煤炭行业": "能源",
    # ── 公用环保（公用事业 + 环保）──
    "电力行业": "公用环保", "燃气": "公用环保",
    "公用事业": "公用环保", "环保行业": "公用环保",
    # ── 轻工制造 ──
    "珠宝首饰": "轻工制造", "纺织服装": "轻工制造",
    "造纸印刷": "轻工制造", "包装材料": "轻工制造",
    # ── 社会服务 ──
    "旅游酒店": "社会服务", "美容护理": "社会服务",
    # ── 商贸（商贸零售 + 商业服务）──
    "商业百货": "商贸", "贸易行业": "商贸", "专业服务": "商贸",
    # ── 农林牧渔 ──
    "农牧饲渔": "农林牧渔",
    # ── 综合 ──
    "综合行业": "综合",
}

# 概念标签：热门标签关联大类和核心子行业
CONCEPT_TAGS = {
    "AI": {"categories": ["AI与数字服务", "半导体", "电子硬件"],
           "subs": ["软件开发", "互联网服务", "半导体", "计算机设备", "通信设备", "光学光电子"]},
    "算力": {"categories": ["AI与数字服务", "半导体"],
             "subs": ["通信设备", "通信服务", "计算机设备", "互联网服务", "电源设备"]},
    "机器人": {"categories": ["机械设备", "电力设备", "电子硬件", "汽车"],
               "subs": ["通用设备", "专用设备", "电机", "电子元件", "汽车零部件"]},
    "半导体": {"categories": ["半导体", "电子硬件"],
               "subs": ["半导体", "电子化学品", "电子元件"]},
    "先进封装": {"categories": ["半导体"],
                 "subs": ["半导体", "电子化学品"]},
    "军工": {"categories": ["交通运输", "机械设备"],
             "subs": ["航天航空", "船舶制造", "航空机场"]},
    "航空": {"categories": ["交通运输"],
             "subs": ["航天航空", "航空机场"]},
    "低空经济": {"categories": ["交通运输", "机械设备"],
                 "subs": ["航天航空", "交运设备", "通用设备"]},
    "医疗": {"categories": ["医药生物"],
             "subs": ["医疗器械", "医疗服务", "化学制药", "生物制品", "中药"]},
    "新能源车": {"categories": ["汽车", "电力设备", "有色金属"],
                 "subs": ["汽车整车", "汽车零部件", "电池", "能源金属"]},
}


def fetch_data():
    now = datetime.now(BJ_TZ)
    print(f"[{now.strftime('%H:%M:%S')}] 正在获取数据（range接口 + 本地缓存增量）...")

    # ── 读取本地缓存 ──
    cache = None
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("dates") and cache.get("industries") and cache.get("data"):
                last_date = cache["dates"][-1]
                print(f"  缓存命中: {len(cache['dates'])} 个交易日, 最新 {last_date}")
            else:
                cache = None
                print("  缓存格式异常，重新全量获取")
        except Exception as e:
            cache = None
            print(f"  缓存读取失败({e})，重新全量获取")

    # ── 确定增量起始日期 ──
    today = now.strftime("%Y-%m-%d")
    if cache:
        last_date = cache["dates"][-1]
        ld = date.fromisoformat(last_date)
        start_date = (ld + timedelta(days=1)).isoformat()
        if start_date > today:
            print(f"  缓存已最新({last_date})，跳过请求")
            return {"dates": cache["dates"], "industries": cache["industries"], "data": cache["data"]}
    else:
        start_date = "2025-01-01"  # API会自动截断到最早可用数据(2025-05-06)

    # ── 请求range接口 ──
    headers = {
        "Referer": "https://sckd.dapanyuntu.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url = f"{API_URL}?start_date={start_date}&end_date={today}"
    print(f"  请求: {start_date} ~ {today}")

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    new_dates = raw.get("dates", [])
    new_industries = raw.get("industries", [])
    new_data = raw.get("data", [])

    if not new_dates:
        print("  无新数据返回")
        if cache:
            return {"dates": cache["dates"], "industries": cache["industries"], "data": cache["data"]}
        raise RuntimeError("无缓存且无新数据")

    print(f"  新数据: {len(new_dates)} 天 ({new_dates[0]} ~ {new_dates[-1]}), {len(new_data)} 条")

    # ── 合并缓存与新数据 ──
    if not cache:
        # 首次全量，直接存储
        result_dates = list(new_dates)
        result_industries = list(new_industries)
        result_data = [list(entry) for entry in new_data]
    else:
        # 增量合并
        n_cached = len(cache["dates"])
        result_dates = list(cache["dates"]) + list(new_dates)
        result_industries = list(cache["industries"])

        # 新数据的行业索引映射到缓存的行业索引
        ind_map = {}
        for new_idx, ind_name in enumerate(new_industries):
            try:
                ind_map[new_idx] = cache["industries"].index(ind_name)
            except ValueError:
                pass  # 缓存中不存在的新行业，跳过

        # 新数据的日期索引偏移到合并后位置
        remapped = []
        for date_idx, ind_idx, val in new_data:
            if ind_idx in ind_map:
                remapped.append([date_idx + n_cached, ind_map[ind_idx], val])

        result_data = [list(entry) for entry in cache["data"]] + remapped

    # ── 写入缓存 ──
    cache_out = {"dates": result_dates, "industries": result_industries, "data": result_data}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_out, f, ensure_ascii=False)

    print(f"  合并完成: {len(result_industries)} 行业, {len(result_dates)} 个交易日 ({result_dates[0]} ~ {result_dates[-1]})")
    print(f"  缓存已保存: {CACHE_FILE}")
    return cache_out


def aggregate_data(raw):
    industries = raw["industries"]
    dates = raw["dates"]
    data = raw["data"]

    cat_date_vals = defaultdict(lambda: defaultdict(list))
    for date_idx, ind_idx, val in data:
        ind = industries[ind_idx]
        cat = INDUSTRY_CATEGORY_MAP.get(ind)
        if cat:
            cat_date_vals[cat][date_idx].append(val)

    cat_avg = {}
    for cat, date_vals in cat_date_vals.items():
        cat_avg[cat] = {}
        for date_idx, vals in date_vals.items():
            valid = [v for v in vals if v > 0]
            cat_avg[cat][date_idx] = round(sum(valid) / len(valid), 1) if valid else None

    latest_col = len(dates) - 1
    sorted_cats = sorted(cat_avg.keys(), key=lambda c: cat_avg[c].get(latest_col, 0) or 0, reverse=True)

    return {
        "categories": sorted_cats,
        "dates": dates,
        "data": {cat: [cat_avg[cat].get(i) for i in range(len(dates))] for cat in sorted_cats}
    }


def build_sub_industry_data(raw):
    industries = raw["industries"]
    dates = raw["dates"]
    data = raw["data"]

    cat_subs = defaultdict(list)
    for ind, cat in INDUSTRY_CATEGORY_MAP.items():
        cat_subs[cat].append(ind)

    sub_data = {}
    for date_idx, ind_idx, val in data:
        ind = industries[ind_idx]
        if ind not in sub_data:
            sub_data[ind] = [None] * len(dates)
        sub_data[ind][date_idx] = val

    result = {}
    for cat in cat_subs:
        subs = cat_subs[cat]
        latest_idx = len(dates) - 1
        subs_sorted = sorted(subs, key=lambda s: sub_data.get(s, [None]*len(dates))[latest_idx] or 0, reverse=True)
        result[cat] = {
            "subIndustries": subs_sorted,
            "data": {s: sub_data.get(s, [None]*len(dates)) for s in subs_sorted}
        }
    return result


def compute_analytics(aggregated):
    """计算增强分析指标"""
    cats = aggregated["categories"]
    data = aggregated["data"]
    n_dates = len(aggregated["dates"])

    analytics = {}

    for cat in cats:
        vals = data[cat]
        latest = vals[-1] if vals else None

        # 5日动量（最近5个交易日的变化）
        momentum_5d = None
        if len(vals) >= 6 and vals[-6] is not None and vals[-1] is not None:
            momentum_5d = round(vals[-1] - vals[-6], 1)

        # 10日动量
        momentum_10d = None
        if len(vals) >= 11 and vals[-11] is not None and vals[-1] is not None:
            momentum_10d = round(vals[-1] - vals[-11], 1)

        # 30日动量（全周期）
        momentum_30d = None
        if vals[0] is not None and vals[-1] is not None:
            momentum_30d = round(vals[-1] - vals[0], 1)

        # 金叉/死叉信号（MA20上穿/下穿50%线）
        signals = []
        for i in range(1, len(vals)):
            if vals[i] is not None and vals[i-1] is not None:
                if vals[i-1] < 50 and vals[i] >= 50:
                    signals.append({"type": "golden", "dateIdx": i, "date": aggregated["dates"][i]})
                elif vals[i-1] >= 50 and vals[i] < 50:
                    signals.append({"type": "death", "dateIdx": i, "date": aggregated["dates"][i]})

        # 当前连续站上/跌破50%的天数
        streak = 0
        if latest is not None:
            above = latest >= 50
            for v in reversed(vals):
                if v is not None and (v >= 50) == above:
                    streak += 1
                else:
                    break
            if not above:
                streak = -streak  # 负数表示连续跌破天数

        # 波动率（近10日标准差）
        recent = [v for v in vals[-10:] if v is not None]
        volatility = None
        if len(recent) >= 2:
            mean_r = sum(recent) / len(recent)
            volatility = round((sum((v - mean_r) ** 2 for v in recent) / len(recent)) ** 0.5, 1)

        # 30日最高/最低
        valid_vals = [v for v in vals if v is not None]
        high_30d = max(valid_vals) if valid_vals else None
        low_30d = min(valid_vals) if valid_vals else None

        analytics[cat] = {
            "momentum5d": momentum_5d,
            "momentum10d": momentum_10d,
            "momentum30d": momentum_30d,
            "signals": signals,
            "streak": streak,
            "volatility": volatility,
            "high30d": high_30d,
            "low30d": low_30d,
        }

    # 市场均线（所有行业的平均值，作为大盘代理指标）
    market_avg = []
    for i in range(n_dates):
        day_vals = []
        for cat in cats:
            v = data[cat][i]
            if v is not None:
                day_vals.append(v)
        market_avg.append(round(sum(day_vals) / len(day_vals), 1) if day_vals else None)

    # 市场宽度统计
    breadth_stats = []
    for i in range(n_dates):
        day_vals = [data[cat][i] for cat in cats if data[cat][i] is not None]
        above50 = sum(1 for v in day_vals if v >= 50)
        breadth_stats.append({
            "above50": above50,
            "total": len(day_vals),
            "pct": round(above50 / len(day_vals) * 100, 1) if day_vals else 0,
        })

    return {
        "byCategory": analytics,
        "marketAvg": market_avg,
        "breadthStats": breadth_stats,
    }


def generate_html(output_data):
    # 模板在 assets/ 目录下（相对于仓库根目录）
    template_path = os.path.join(REPO_ROOT, "assets", "template.html")
    if not os.path.exists(template_path):
        print(f"警告: template.html 不存在: {template_path}，跳过HTML生成")
        return None

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(output_data, ensure_ascii=False)
    html = template.replace("/*__DATA__*/null", data_json)

    html_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"=== 市场热力图V2数据更新 {datetime.now(BJ_TZ).strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    try:
        raw = fetch_data()
    except Exception as e:
        print(f"错误: 数据获取失败 - {e}")
        sys.exit(1)

    aggregated = aggregate_data(raw)
    sub_industry = build_sub_industry_data(raw)
    analytics = compute_analytics(aggregated)

    output = {
        "updateTime": datetime.now(BJ_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "dateRange": {
            "start": raw["dates"][0] if raw["dates"] else "",
            "end": raw["dates"][-1] if raw["dates"] else "",
        },
        "dates": raw["dates"],
        "fullDates": raw["dates"],
        "aggregated": aggregated,
        "subIndustries": sub_industry,
        "industryList": raw["industries"],
        "analytics": analytics,
        "conceptTags": CONCEPT_TAGS,
    }

    json_path = os.path.join(OUTPUT_DIR, "market_data_v2.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    html_path = generate_html(output)

    print(f"\n[{datetime.now(BJ_TZ).strftime('%H:%M:%S')}] V2更新完成!")
    print(f"  JSON: {json_path}")
    if html_path:
        print(f"  HTML: {html_path}")
    print(f"  一级大类: {len(aggregated['categories'])} 个")
    print(f"  二级行业: {len(raw['industries'])} 个")
    print(f"  交易日: {len(raw['dates'])} 天")

    # 打印增强指标摘要
    top_momentum = sorted(
        analytics["byCategory"].items(),
        key=lambda x: x[1].get("momentum5d") or 0,
        reverse=True
    )
    top3 = []
    for k, v in top_momentum[:3]:
        m = v.get("momentum5d") or 0
        top3.append(f"{k}({m:+.1f})")
    bot3 = []
    for k, v in top_momentum[-3:]:
        m = v.get("momentum5d") or 0
        bot3.append(f"{k}({m:+.1f})")
    print(f"\n  5日动量Top3: {', '.join(top3)}")
    print(f"  5日动量Bottom3: {', '.join(bot3)}")


if __name__ == "__main__":
    main()
