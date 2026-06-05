# -*- coding: utf-8 -*-
"""
한국정치경제신문 · 해외 지수 조회 모듈
────────────────────────────────────────────────
Yahoo Finance 비공식 엔드포인트로 미국 지수 받아오기.
파이썬 표준 라이브러리만 사용 (추가 설치 불필요).

실행 (단독 테스트):
    py -3.13-32 overseas_indices.py
"""
import urllib.request
import json


# 받아올 해외 지수 목록
OVERSEAS_INDICES = [
    {"symbol": "^IXIC",  "name": "나스닥"},
    {"symbol": "^DJI",   "name": "다우"},
    {"symbol": "^SOX",   "name": "필라델피아"},
    {"symbol": "KRW=X",  "name": "USD/KRW"},
]


def fetch_yahoo(symbol):
    """Yahoo Finance에서 한 지수의 시세를 받아옴."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    # Yahoo가 파이썬 기본 User-Agent를 차단하므로 브라우저처럼 위장
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        meta = data["chart"]["result"][0]["meta"]
        current = float(meta.get("regularMarketPrice", 0) or 0)
        prev_close = float(meta.get("previousClose", 0) or
                           meta.get("chartPreviousClose", 0) or 0)

        if prev_close > 0:
            change_rate = ((current - prev_close) / prev_close) * 100
        else:
            change_rate = 0.0

        return {"price": current, "change_rate": change_rate}

    except Exception as e:
        print(f"  [X] {symbol} 조회 실패: {e}")
        return None


def collect_overseas():
    """해외 지수 전체 수집."""
    print("해외 지수 수집 중...")
    results = {}
    for idx in OVERSEAS_INDICES:
        sym = idx["symbol"]
        name = idx["name"]
        print(f"   {name} ({sym}) 조회 중...", end=" ")
        data = fetch_yahoo(sym)
        if data and data["price"] > 0:
            arrow = "▲" if data["change_rate"] > 0 else ("▼" if data["change_rate"] < 0 else "─")
            print(f"{data['price']:,.2f}  {arrow}{abs(data['change_rate']):.2f}%")
            results[name] = data
        else:
            print("실패")
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("해외 지수 조회 테스트")
    print("=" * 60)
    results = collect_overseas()

    print("\n" + "=" * 60)
    print(f"수집 결과: {len(results)} / {len(OVERSEAS_INDICES)}")
    print("=" * 60)
    for name, data in results.items():
        sign = "+" if data["change_rate"] >= 0 else ""
        print(f"  {name:12s}  {data['price']:>12,.2f}  ({sign}{data['change_rate']:.2f}%)")
