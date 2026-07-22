#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARX 네이버쇼핑 순위 추적기
- keywords.json에 등록된 상품들의 키워드별 네이버쇼핑 노출 순위를 조회하고
- data/history.json에 날짜별로 누적 기록하고
- index.html(크롬에서 바로 보는 대시보드)을 다시 생성한다.

실행 환경: GitHub Actions (매일 자동) 또는 로컬(python scripts/track.py)
필요 환경변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
"""
import os
import sys
import json
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "keywords.json")
HISTORY_PATH = os.path.join(BASE_DIR, "data", "history.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "index.html")

MAX_SCAN = 1000  # 네이버 오픈API가 조회 가능한 최대 순위 범위
PAGE_SIZE = 100


def api_search(client_id, client_secret, query, start):
    params = urllib.parse.urlencode({
        "query": query, "display": PAGE_SIZE, "start": start, "sort": "sim"
    })
    url = f"https://openapi.naver.com/v1/search/shop.json?{params}"
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_rank(client_id, client_secret, keyword, target_product_id):
    """키워드 검색결과 안에서 target_product_id의 위치를 찾는다.
    최대 MAX_SCAN위까지 스캔. 못 찾으면 rank=None."""
    total = None
    for start in range(1, MAX_SCAN, PAGE_SIZE):
        try:
            data = api_search(client_id, client_secret, keyword, start)
        except urllib.error.HTTPError as e:
            return {"rank": None, "total": None, "error": f"HTTP {e.code}"}
        except Exception as e:
            return {"rank": None, "total": None, "error": str(e)}
        if total is None:
            total = data.get("total")
        items = data.get("items", [])
        if not items:
            break
        for i, item in enumerate(items):
            if str(item.get("productId")) == str(target_product_id):
                return {"rank": start + i, "total": total, "error": None}
        time.sleep(0.15)
    return {"rank": None, "total": total, "error": None}


def kst_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    config = load_json(CONFIG_PATH, {"products": []})
    history = load_json(HISTORY_PATH, {})

    now = kst_now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M") + " KST"

    history.setdefault(today, {})

    for product in config["products"]:
        pid = product["id"]
        history[today].setdefault(pid, {})
        for kw in product["keywords"]:
            result = get_rank(client_id, client_secret, kw, product["product_id"])
            history[today][pid][kw] = result
            print(f"[{pid}] {kw} -> {result}")

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    render_html(config, history, time_str)


def render_html(config, history, time_str):
    dates = sorted(history.keys())
    latest = dates[-1]
    prev = dates[-2] if len(dates) >= 2 else None

    products_html = []
    for product in config["products"]:
        pid = product["id"]
        rows_html = []
        for kw in product["keywords"]:
            cur = history[latest].get(pid, {}).get(kw, {})
            cur_rank = cur.get("rank")
            prev_rank = None
            if prev:
                prev_rank = history[prev].get(pid, {}).get(kw, {}).get("rank")

            if cur_rank is not None:
                rank_display = f"{cur_rank}위"
            else:
                rank_display = "1000위 밖"

            delta_html = '<span class="delta flat">-</span>'
            if cur_rank is not None and prev_rank is not None:
                diff = prev_rank - cur_rank  # 양수 = 순위 상승(더 앞으로)
                if diff > 0:
                    delta_html = f'<span class="delta up">▲{diff}</span>'
                elif diff < 0:
                    delta_html = f'<span class="delta down">▼{abs(diff)}</span>'
            elif cur_rank is not None and prev is None:
                delta_html = '<span class="delta new">NEW</span>'

            # 최근 최대 14개 기록으로 스파크라인
            recent_dates = dates[-14:]
            spark_points = []
            for d in recent_dates:
                r = history[d].get(pid, {}).get(kw, {}).get("rank")
                spark_points.append(r)
            spark_svg = render_sparkline(spark_points)

            rows_html.append(f"""
            <div class="kw-row">
              <div class="kw-name">{escape_html(kw)}</div>
              <div class="kw-spark">{spark_svg}</div>
              <div class="kw-rank">{rank_display}</div>
              <div class="kw-delta">{delta_html}</div>
            </div>""")

        products_html.append(f"""
        <div class="product-card">
          <div class="product-head">
            <div class="product-thumb">ARX</div>
            <div class="product-info">
              <div class="product-title">{escape_html(product['label'])}</div>
              <div class="product-sub">{escape_html(product['product_title'])}</div>
              <a class="product-link" href="{escape_html(product['product_url'])}" target="_blank">상품 페이지 열기 ↗</a>
            </div>
          </div>
          <div class="kw-table">
            <div class="kw-row kw-header">
              <div class="kw-name">키워드</div>
              <div class="kw-spark">추이(최근 {len(recent_dates)}회)</div>
              <div class="kw-rank">현재 순위</div>
              <div class="kw-delta">변동</div>
            </div>
            {''.join(rows_html)}
          </div>
        </div>""")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARX 네이버쇼핑 순위 추적기</title>
<style>
  :root {{
    --bg: #f5f6f8;
    --card-bg: #ffffff;
    --border: #e3e5e9;
    --text: #1a1d23;
    --sub: #767c88;
    --up: #1a9e5c;
    --down: #e0334f;
    --flat: #9aa0ab;
    --accent: #2a5bd7;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 32px 20px 80px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .updated {{ color: var(--sub); font-size: 13px; margin-bottom: 28px; }}
  .product-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 20px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}
  .product-head {{ display: flex; gap: 14px; margin-bottom: 16px; align-items: flex-start; }}
  .product-thumb {{
    width: 52px; height: 52px; border-radius: 10px;
    background: linear-gradient(135deg,#2a2f3a,#4a5568);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 13px; letter-spacing: 0.5px; flex-shrink: 0;
  }}
  .product-title {{ font-size: 15px; font-weight: 700; margin-bottom: 2px; }}
  .product-sub {{ font-size: 12.5px; color: var(--sub); line-height: 1.4; margin-bottom: 6px; }}
  .product-link {{ font-size: 12.5px; color: var(--accent); text-decoration: none; }}
  .product-link:hover {{ text-decoration: underline; }}
  .kw-table {{ display: flex; flex-direction: column; }}
  .kw-row {{
    display: grid;
    grid-template-columns: 1.3fr 1.4fr 0.9fr 0.7fr;
    align-items: center;
    padding: 10px 0;
    border-top: 1px solid var(--border);
    font-size: 13.5px;
  }}
  .kw-header {{ color: var(--sub); font-size: 12px; border-top: none; padding-top: 0; padding-bottom: 8px; }}
  .kw-name {{ font-weight: 600; }}
  .kw-rank {{ font-weight: 700; }}
  .delta {{ font-weight: 700; font-size: 12.5px; padding: 2px 7px; border-radius: 6px; }}
  .delta.up {{ color: var(--up); background: rgba(26,158,92,0.1); }}
  .delta.down {{ color: var(--down); background: rgba(224,51,79,0.1); }}
  .delta.flat {{ color: var(--flat); background: rgba(154,160,171,0.12); }}
  .delta.new {{ color: var(--accent); background: rgba(42,91,215,0.1); }}
  .footer-note {{ color: var(--sub); font-size: 12px; margin-top: 24px; line-height: 1.6; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>ARX 네이버쇼핑 순위 추적기</h1>
    <div class="updated">마지막 갱신: {time_str} · 매일 자동 갱신(GitHub Actions)</div>
    {''.join(products_html)}
    <div class="footer-note">
      순위는 네이버 검색 오픈API(쇼핑) 기준 근사치이며, 실제 소비자 화면과 개인화 등으로 다를 수 있습니다.
      최대 1000위까지 조회되며 "1000위 밖"은 해당 범위 안에서 상품을 찾지 못했다는 뜻입니다.
    </div>
  </div>
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


def render_sparkline(points, width=120, height=28):
    """rank 리스트(작을수록 좋음, None=결측)를 미니 SVG 라인차트로."""
    valid = [(i, p) for i, p in enumerate(points) if p is not None]
    if len(valid) < 2:
        return '<span style="color:#c2c6cc;font-size:11px;">데이터 누적중</span>'
    ranks = [p for _, p in valid]
    lo, hi = min(ranks), max(ranks)
    span = max(hi - lo, 1)
    n = len(points)

    def x_of(i):
        return 4 + (i / max(n - 1, 1)) * (width - 8)

    def y_of(rank):
        # 순위가 낮을(좋을)수록 위로 오도록 반전
        return 4 + ((rank - lo) / span) * (height - 8)

    coords = []
    for i, p in valid:
        coords.append((x_of(i), y_of(p)))

    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    last_x, last_y = coords[-1]
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<polyline points="{path}" fill="none" stroke="#2a5bd7" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.4" fill="#2a5bd7"/>'
        f'</svg>'
    )


def escape_html(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    main()
