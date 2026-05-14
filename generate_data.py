# -*- coding: utf-8 -*-
"""
한국정치경제신문 · data.js 자동 생성기 (v2)
────────────────────────────────────────────────
키움에서 지수(KOSPI, KOSDAQ, KOSPI200) 자동 갱신.
나머지 콘텐츠(기사, 시초가, 사설)는 아래 CONTENT 영역에서 매일 수정.

실행:
    py -3.13-32 generate_data.py
"""
import os
import time
import json
from datetime import datetime
from kiwoom_connector import KiwoomAPI
from overseas_indices import collect_overseas


# ============================================================
# 설정 — 신문 폴더 위치
# ============================================================
NEWSPAPER_FOLDER = r"C:\Users\intty\한국정치경제신문"
OUTPUT_FILE = os.path.join(NEWSPAPER_FOLDER, "data.js")
ARTICLES_FILE = os.path.join(NEWSPAPER_FOLDER, "articles.json")


# ============================================================
# articles.json 에서 기사 로드 (편집실에서 만든 파일)
# ============================================================
def load_articles():
    """articles.json 읽기. 없거나 깨지면 기본값 반환."""
    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✓ articles.json 로드: {ARTICLES_FILE}")
        return data
    except FileNotFoundError:
        print(f"! articles.json 없음 → 기본 기사 사용")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ articles.json 형식 오류: {e}")
        print(f"   기본 기사로 진행합니다.")
        return None


# 기본값 (articles.json 없을 때 fallback)
DEFAULT_HOME_LEAD = {
    "flag": "오 늘 의  1 면",
    "headline": "여야, 추경 처리 합의… 반도체·AI에 4조원 집중 투입",
    "deck": "국회 본회의 통과, 시장 즉각 반응",
    "byline": "정치부·경제부 종합",
    "body": [
        "여야가 본회의에서 올해 추가경정예산안을 합의 처리했다.",
        "코스피는 상승 마감, 외국인은 순매수를 기록했다.",
    ],
}
DEFAULT_HOME_OPINION = {
    "label": "사 설",
    "headline": "추경 통과, 이제 집행의 속도가 관건이다",
    "body": [
        "여야가 추경을 합의 처리한 것은 다행이다. 정책의 효과는 집행 속도에 달려 있다.",
    ],
    "author": "— 본지 논설위원실",
}


# ============================================================
# 자동 갱신할 지수 (키움에서 가져옴)
# ============================================================
INDEX_LIST = [
    {"code": "001", "name": "KOSPI"},
    {"code": "101", "name": "KOSDAQ"},
    {"code": "201", "name": "KOSPI200"},
]


# ============================================================
# 수동 항목 (필요시 여기에 추가)
# ============================================================
MANUAL_RATES = []


# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃        ★ 시초가 카드와 정치·경제 기사는 여기서 수정 ★        ┃
# ┃        (1면 톱기사·사설은 editor.html 로 편집)              ┃
# ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

# ───── 시초가 후보 카드 ─────
TIER_CARDS = [
    {"name": "삼성E&A",        "tier": "TIER 1", "note": "체결강도 139.59 · 실적+수주 더블호재"},
    {"name": "와이지원",        "tier": "TIER 1", "note": "체결강도 140.60 · 정배열+신고가"},
    {"name": "해성디에스",      "tier": "TIER 2", "note": "일봉 정배열 · HBM 동조"},
    {"name": "HD현대마린엔진",  "tier": "TIER 0", "note": "체결강도 146.69 · 갭 7% 이상 추격 금지"},
]

# ───── 정치 기사 ─────
POLITICS_ARTICLES_HOME = [
    {"size": "h3", "headline": "국정감사 일정 확정… 22개 상임위, 다음 달 4일 개회",
     "byline": "정치부 / 이기자", "twoCol": True,
     "body": ["국회는 다음 달 4일부터 22개 상임위 국정감사에 돌입한다.",
              "여야는 증인 채택 명단을 두고 막판 협상을 진행 중이다."]},
]

# ───── 경제 기사 ─────
ECONOMY_ARTICLES_HOME = [
    {"size": "h3", "headline": "한은, 기준금리 동결… 성장률 전망 상향",
     "byline": "금융부 / 윤기자",
     "body": ["한은은 올해 성장률 전망치를 상향 조정했다."]},
]

# ===== 위까지가 직접 수정하는 부분 =====


# ============================================================
# 데이터 수집
# ============================================================
def collect_indices():
    print("=" * 60)
    print("[1/3] 키움 지수 수집")
    print("=" * 60)

    kw = KiwoomAPI()
    kw.login()

    results = {}
    for idx in INDEX_LIST:
        code, name = idx["code"], idx["name"]
        print(f"   {name} ({code}) 조회 중...", end=" ")
        data = kw.get_index_price(code)
        if data and data["price"] > 0:
            results[name] = data
            arrow = "▲" if data["change_rate"] > 0 else ("▼" if data["change_rate"] < 0 else "─")
            print(f"{data['price']:,.2f}  {arrow}{abs(data['change_rate']):.2f}%")
        else:
            print("실패")
        time.sleep(0.3)
    return results


# ============================================================
# data.js 빌더
# ============================================================
def build_market_rows(indices, overseas):
    """시세 박스 — 키움 지수 + Yahoo 환율 + Yahoo 해외지수."""
    rows = []

    # 국내 지수 (KOSPI, KOSDAQ, KOSPI200) → 1열·2열 윗줄
    for idx in INDEX_LIST:
        name = idx["name"]
        if name in indices:
            d = indices[name]
            arrow = "▲" if d["change_rate"] > 0 else ("▼" if d["change_rate"] < 0 else "─")
            rows.append({
                "name": name,
                "value": f"{d['price']:,.2f} {arrow}{abs(d['change_rate']):.2f}%",
                "dir": "up" if d["change_rate"] > 0 else ("down" if d["change_rate"] < 0 else ""),
            })

    # USD/KRW (자동) → 2열 아랫줄
    if "USD/KRW" in overseas:
        d = overseas["USD/KRW"]
        arrow = "▲" if d["change_rate"] > 0 else ("▼" if d["change_rate"] < 0 else "─")
        rows.append({
            "name": "USD/KRW",
            "value": f"{d['price']:,.2f} {arrow}{abs(d['change_rate']):.2f}%",
            "dir": "up" if d["change_rate"] > 0 else ("down" if d["change_rate"] < 0 else ""),
        })

    # 해외 지수 (다우, 필라델피아, 나스닥) → 3열
    for name in ["다우", "필라델피아", "나스닥"]:
        if name in overseas:
            d = overseas[name]
            arrow = "▲" if d["change_rate"] > 0 else ("▼" if d["change_rate"] < 0 else "─")
            rows.append({
                "name": name,
                "value": f"{d['price']:,.2f} {arrow}{abs(d['change_rate']):.2f}%",
                "dir": "up" if d["change_rate"] > 0 else ("down" if d["change_rate"] < 0 else ""),
            })

    # 추가 수동 항목 (있으면)
    rows.extend(MANUAL_RATES)
    return rows


def to_js(py_dict):
    return json.dumps(py_dict, ensure_ascii=False, indent=2)


def build_data(indices, overseas, articles):
    print("\n" + "=" * 60)
    print("[2/3] data.js 빌드")
    print("=" * 60)

    market_rows = build_market_rows(indices, overseas)
    cols = [market_rows[0:2], market_rows[2:4], market_rows[4:]]

    # articles.json 에서 가져오기 (없으면 기본값)
    home = (articles or {}).get("home", {})
    home_lead = home.get("lead") or DEFAULT_HOME_LEAD
    home_opinion = home.get("opinion") or DEFAULT_HOME_OPINION
    politics_articles = home.get("politicsArticles") or POLITICS_ARTICLES_HOME
    economy_articles = home.get("economyArticles") or ECONOMY_ARTICLES_HOME

    data_obj = {
        "home": {
            "lead": home_lead,
            "politicsArticles": politics_articles,
            "market": market_rows,
            "economyArticles": economy_articles,
            "tiers": TIER_CARDS,
            "opinion": home_opinion,
        },
        "politics": {
            "lead": home_lead,
            "sections": [
                {"label": "국 회", "articles": politics_articles},
                {"label": "외 교  ·  정 당", "articles": []},
            ],
            "opinion": {"label": "정 치 칼 럼", "headline": "정치 칼럼 제목",
                        "body": ["내용"], "author": "— 정치부장"},
        },
        "economy": {
            "lead": {"flag": "경 제 면  ·  톱",
                     "headline": "한은, 기준금리 동결",
                     "deck": "성장률 전망 상향",
                     "byline": "금융부 종합",
                     "body": ["한은은 올해 성장률 전망치를 상향 조정했다."]},
            "marketWide": {"title": "마 감 시 세", "cols": cols},
            "tiers": TIER_CARDS,
            "mapping": [
                {"sector": "HBM / AI 메모리", "us": "MU · NVDA · AVGO",
                 "kr": "SK하이닉스 · 한미반도체 · 해성디에스"},
                {"sector": "원전 SMR", "us": "OKLO · SMR · CEG",
                 "kr": "두산에너빌리티 · 한국전력"},
                {"sector": "방산 · 우주", "us": "PLTR · RTX · LMT",
                 "kr": "한화에어로 · 현대로템 · LIG넥스원"},
            ],
            "sections": [
                {"label": "증 시", "articles": economy_articles},
                {"label": "매 크 로  ·  글 로 벌", "articles": []},
            ],
            "opinion": {"label": "시 황  분 석",
                        "headline": "외국인 연속 순매수, 본격 상승의 신호인가",
                        "body": ["판단 기준은 매수 규모, 섹터 다변화, 시간외 흐름이다."],
                        "author": "— 증권부장"},
        },
    }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""// ============================================================
// 한국정치경제신문 · 일간 데이터 (data.js)
// 자동 생성: {now}
// ============================================================

window.NEWSPAPER = {to_js(data_obj)};
"""


# ============================================================
# 파일 저장
# ============================================================
def save_file(text):
    print("\n" + "=" * 60)
    print("[3/3] data.js 저장")
    print("=" * 60)

    if not os.path.exists(NEWSPAPER_FOLDER):
        print(f"✗ 신문 폴더 없음: {NEWSPAPER_FOLDER}")
        return False

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✓ 저장: {OUTPUT_FILE}  ({os.path.getsize(OUTPUT_FILE)/1024:.1f} KB)")
    return True


# ============================================================
# 메인
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("[0/3] 기사 로드")
    print("=" * 60)
    articles = load_articles()

    indices = collect_indices()

    print("\n" + "=" * 60)
    print("[1.5/3] 해외 지수 수집 (Yahoo Finance)")
    print("=" * 60)
    overseas = collect_overseas()

    js_text = build_data(indices, overseas, articles)
    if save_file(js_text):
        print("\n✓ 신문 데이터 갱신 완료")
        print("  브라우저 새로고침(Ctrl+F5)으로 확인하세요.")
