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
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO_ROOT, "docs")
API_BASE = "https://sckd.dapanyuntu.com/api/api/industry_ma20_analysis_page"
PAGES = 3
BJ_TZ = timezone(timedelta(hours=8))

INDUSTRY_CATEGORY_MAP = {
    "专业服务": "商业服务",
    "互联网服务": "TMT服务", "软件开发": "TMT服务", "通信服务": "TMT服务",
    "游戏": "TMT服务", "教育": "TMT服务", "文化传媒": "TMT服务",
    "专用设备": "机械设备", "通用设备": "机械设备", "工程机械": "机械设备",
    "仪器仪表": "机械设备", "交运设备": "机械设备",
    "中药": "医药生物", "化学制药": "医药生物", "生物制品": "医药生物",
    "医疗器械": "医药生物", "医疗服务": "医药生物", "医药商业": "医药生物",
    "农药兽药": "医药生物",
    "光伏设备": "电力设备", "电池": "电力设备", "电源设备": "电力设备",
    "电网设备": "电力设备", "风电设备": "电力设备", "电机": "电力设备",
    "光学光电子": "电子", "半导体": "电子", "消费电子": "电子",
    "电子元件": "电子", "电子化学品": "电子",
    "保险": "金融", "银行": "金融", "证券": "金融", "多元金融": "金融",
    "农牧饲渔": "农林牧渔",
    "化学制品": "基础化工", "化学原料": "基础化工", "化肥行业": "基础化工",
    "化纤行业": "基础化工", "橡胶制品": "基础化工", "塑料制品": "基础化工",
    "非金属材料": "基础化工",
    "商业百货": "商贸零售", "贸易行业": "商贸零售",
    "家用轻工": "家用电器", "家电行业": "家用电器",
    "小金属": "有色金属", "有色金属": "有色金属", "贵金属": "有色金属",
    "能源金属": "有色金属",
    "工程咨询服务": "建筑装饰", "工程建设": "建筑装饰",
    "装修装饰": "建筑装饰", "装修建材": "建筑装饰",
    "房地产开发": "房地产", "房地产服务": "房地产",
    "旅游酒店": "社会服务", "美容护理": "社会服务",
    "水泥建材": "建筑材料", "玻璃玻纤": "建筑材料", "钢铁行业": "建筑材料",
    "汽车整车": "汽车", "汽车服务": "汽车", "汽车零部件": "汽车",
    "煤炭行业": "煤炭",
    "物流行业": "交通运输", "航运港口": "交通运输", "航空机场": "交通运输",
    "铁路公路": "交通运输", "航天航空": "交通运输", "船舶制造": "交通运输",
    "环保行业": "环保",
    "珠宝首饰": "轻工制造", "纺织服装": "轻工制造",
    "造纸印刷": "轻工制造", "包装材料": "轻工制造",
    "电力行业": "公用事业", "燃气": "公用事业", "公用事业": "公用事业",
    "石油行业": "石油石化", "采掘行业": "石油石化",
    "综合行业": "综合",
    "酿酒行业": "食品饮料", "食品饮料": "食品饮料",
    "通信设备": "通信",
}


def fetch_data():
    print(f"[{datetime.now(BJ_TZ).strftime('%H:%M:%S')}] 正在获取数据（{PAGES}页）...")
    all_dates = []
    all_data = []
    industries = None
    date_offset = 0

    for page in range(PAGES):
        url = f"{API_BASE}?page={page}"
        req = urllib.request.Request(url, headers={
            "Referer": "https://sckd.dapanyuntu.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        if not raw.get("dates"):
            break

        if industries is None:
            industries = raw["industries"]

        page_dates = raw["dates"]
        for date_idx, ind_idx, val in raw["data"]:
            all_data.append([date_idx + date_offset, ind_idx, val])

        all_dates.extend(page_dates)
        date_offset += len(page_dates)
        print(f"  Page {page}: {len(page_dates)} 天 ({page_dates[0]} ~ {page_dates[-1]})")

    return {"dates": all_dates, "industries": industries, "data": all_data}


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
            "start": raw.get("start_date", ""),
            "end": raw.get("end_date", ""),
        },
        "dates": raw["dates"],
        "fullDates": raw["dates"],
        "aggregated": aggregated,
        "subIndustries": sub_industry,
        "industryList": raw["industries"],
        "analytics": analytics,
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
