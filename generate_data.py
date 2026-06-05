# -*- coding: utf-8 -*-
"""
[OK] 한국정치경제신문 · data.js 생성기 (Phase 1)
=============================================
articles.json (기사 데이터) + 시세 (키움 + Yahoo) 를 합쳐서
신문 폴더의 data.js 로 저장한다.

새 articles.json 구조:
    {
      "reporters": [...],
      "articles": [...],   ← 매일 새 기사를 여기에 추가
      "opinion": {...}
    }

실행:
    py -3.13-32 generate_data.py
"""
import os
import json
import time
import subprocess
from datetime import datetime
from kiwoom_connector import KiwoomAPI
from overseas_indices import collect_overseas


# ============================================================
# 설정
# ============================================================
NEWSPAPER_FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(NEWSPAPER_FOLDER, "data.js")
ARTICLES_FILE = os.path.join(NEWSPAPER_FOLDER, "articles.json")

INDEX_LIST = [
    {"code": "001", "name": "KOSPI"},
    {"code": "101", "name": "KOSDAQ"},
    {"code": "201", "name": "KOSPI200"},
]


# ============================================================
# articles.json 로드
# ============================================================
def load_articles():
    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[OK] articles.json 로드: {ARTICLES_FILE}")
        n = len(data.get("articles", []))
        m = len(data.get("reporters", []))
        print(f"     기사 {n}개, 기자 {m}명")
        return data
    except FileNotFoundError:
        print(f"[!] articles.json 없음. 빈 신문으로 진행.")
        return {"reporters": [], "articles": [], "opinion": {}}
    except json.JSONDecodeError as e:
        print(f"[X] articles.json 형식 오류: {e}")
        return {"reporters": [], "articles": [], "opinion": {}}


# ============================================================
# 시세 수집
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
            arrow = "▲" if data["change_rate"] > 0 else ("▼" if data["change_rate"] < 0 else "-")
            print(f"{data['price']:,.2f}  {arrow}{abs(data['change_rate']):.2f}%")
        else:
            print("실패")
        time.sleep(0.3)
    return results


def build_market_rows(indices, overseas):
    rows = []
    for idx in INDEX_LIST:
        name = idx["name"]
        if name in indices:
            d = indices[name]
            arrow = "▲" if d["change_rate"] > 0 else ("▼" if d["change_rate"] < 0 else "-")
            rows.append({
                "name": name,
                "value": f"{d['price']:,.2f} {arrow}{abs(d['change_rate']):.2f}%",
                "dir": "up" if d["change_rate"] > 0 else ("down" if d["change_rate"] < 0 else ""),
            })
    if "USD/KRW" in overseas:
        d = overseas["USD/KRW"]
        arrow = "▲" if d["change_rate"] > 0 else ("▼" if d["change_rate"] < 0 else "-")
        rows.append({
            "name": "USD/KRW",
            "value": f"{d['price']:,.2f} {arrow}{abs(d['change_rate']):.2f}%",
            "dir": "up" if d["change_rate"] > 0 else ("down" if d["change_rate"] < 0 else ""),
        })
    for name in ["다우", "필라델피아", "나스닥"]:
        if name in overseas:
            d = overseas[name]
            arrow = "▲" if d["change_rate"] > 0 else ("▼" if d["change_rate"] < 0 else "-")
            rows.append({
                "name": name,
                "value": f"{d['price']:,.2f} {arrow}{abs(d['change_rate']):.2f}%",
                "dir": "up" if d["change_rate"] > 0 else ("down" if d["change_rate"] < 0 else ""),
            })
    return rows


# ============================================================
# data.js 빌드
# ============================================================
def build_data(articles_data, indices, overseas):
    print("\n" + "=" * 60)
    print("[2/3] data.js 빌드")
    print("=" * 60)

    market_rows = build_market_rows(indices, overseas)

    # articles.json 의 모든 데이터를 그대로 사용 + 시세 추가
    out = {
        "reporters": articles_data.get("reporters", []),
        "articles": articles_data.get("articles", []),
        "columns": articles_data.get("columns", []),
        "opinion": articles_data.get("opinion", {}),  # 옛 구조 호환용
        "publisher": load_publisher(),
        "market": market_rows,
    }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""// 한국정치경제신문 · 일간 데이터
// 자동 생성: {now}
window.NEWSPAPER = {json.dumps(out, ensure_ascii=False, indent=2)};
"""


def save_file(text):
    print("\n" + "=" * 60)
    print("[3/3] data.js 저장")
    print("=" * 60)
    if not os.path.exists(NEWSPAPER_FOLDER):
        print(f"[X] 신문 폴더 없음: {NEWSPAPER_FOLDER}")
        return False
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[OK] 저장: {OUTPUT_FILE}  ({os.path.getsize(OUTPUT_FILE)/1024:.1f} KB)")
    return True


# ============================================================
# 기사별 HTML 자동 생성 (카톡 미리보기용 OG 메타태그 포함)
# ============================================================
SITE_URL = "https://pcwon2026-ctrl.github.io/news"
ARTICLES_DIR = os.path.join(NEWSPAPER_FOLDER, "articles")
PUBLISHER_FILE = os.path.join(NEWSPAPER_FOLDER, "publisher.json")


def load_publisher():
    """publisher.json 읽기 (없으면 기본값)."""
    if os.path.exists(PUBLISHER_FILE):
        try:
            with open(PUBLISHER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] publisher.json 읽기 실패: {e}")
    return {
        "name": "박창원",
        "title": "발행인",
        "tagline": "정확한 사실 · 깊은 시각",
    }


def html_escape(s):
    """HTML 속성/텍스트에 들어가는 문자 이스케이프."""
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace('"', "&quot;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def parse_video_url(url):
    """동영상 URL을 파싱해서 임베드 URL 반환. 지원: 유튜브/네이버TV/카카오TV/비메오/직접 mp4."""
    import re
    if not url:
        return None
    url = url.strip()

    # YouTube
    m = re.search(r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]+)', url)
    if m:
        return {
            "type": "youtube",
            "id": m.group(1),
            "embed_url": f"https://www.youtube.com/embed/{m.group(1)}",
            "thumb": f"https://img.youtube.com/vi/{m.group(1)}/hqdefault.jpg",
        }

    # Naver TV
    m = re.search(r'tv\.naver\.com/v/(\d+)', url)
    if m:
        return {
            "type": "navertv",
            "id": m.group(1),
            "embed_url": f"https://tv.naver.com/embed/{m.group(1)}?autoPlay=false",
            "thumb": "",
        }

    # Kakao TV
    m = re.search(r'tv\.kakao\.com/(?:channel/\d+/)?cliplink/(\d+)', url)
    if m:
        return {
            "type": "kakaotv",
            "id": m.group(1),
            "embed_url": f"https://tv.kakao.com/embed/player/cliplink/{m.group(1)}?service=kakao_tv",
            "thumb": "",
        }

    # Vimeo
    m = re.search(r'vimeo\.com/(\d+)', url)
    if m:
        return {
            "type": "vimeo",
            "id": m.group(1),
            "embed_url": f"https://player.vimeo.com/video/{m.group(1)}",
            "thumb": "",
        }

    # 직접 링크
    if re.search(r'\.(mp4|webm|ogg)(\?|$)', url, re.I):
        return {"type": "direct", "id": "", "embed_url": url, "thumb": ""}

    return None


def build_video_embed(url, caption=""):
    """동영상 URL → HTML 임베드 코드 (기사 페이지에 박을 용도)."""
    v = parse_video_url(url)
    if not v:
        return ""
    if v["type"] == "direct":
        iframe = f'<video controls src="{v["embed_url"]}"></video>'
    else:
        iframe = (f'<iframe src="{v["embed_url"]}" '
                  f'allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" '
                  f'allowfullscreen></iframe>')
    html = f'<div class="video-embed">{iframe}</div>'
    if caption:
        html += f'<p class="video-caption">{caption}</p>'
    return html


def render_article_page(article, reporter, opinion):
    """기사 한 개의 정적 HTML 페이지 텍스트 반환."""
    headline = html_escape(article.get("headline", ""))
    deck = html_escape(article.get("deck", ""))
    summary = html_escape(article.get("summary", ""))
    dept = article.get("dept", "")
    date = article.get("date", "")
    photo = article.get("photo", "")
    photo_caption = html_escape(article.get("photoCaption", ""))
    reporter_str = ""
    if reporter:
        reporter_str = f"{reporter.get('dept','')}부 {reporter.get('name','')} 기자"

    # 본문 paragraph 처리
    body_text = article.get("body", "")
    paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]
    body_html = "\n".join(f"      <p>{html_escape(p)}</p>" for p in paragraphs)

    # 사진 블록 — Base64(data:image)면 그대로, 일반 경로면 ../ 붙임
    if photo:
        if photo.startswith("data:"):
            img_src = photo
        elif photo.startswith("http"):
            img_src = photo
        else:
            img_src = f"../{photo}"
        photo_html = f'''<div class="photo">
        <img src="{img_src}" alt="">
        <p class="caption">{photo_caption}</p>
      </div>'''
    else:
        photo_html = ""

    # 동영상 블록 (서버 사이드에서 임베드 코드 생성)
    video_url = article.get("video", "").strip()
    video_caption = html_escape(article.get("videoCaption", ""))
    video_html = build_video_embed(video_url, video_caption)

    # OG 이미지 URL — photoFile(추출된 파일) 우선
    photo_for_og = article.get("photoFile") or (photo if photo and not photo.startswith("data:") else "")
    if photo_for_og:
        og_image = photo_for_og if photo_for_og.startswith("http") else f"{SITE_URL}/{photo_for_og}"
    else:
        og_image = ""

    # OG 메타태그
    og_tags = [
        f'<meta property="og:type" content="article">',
        f'<meta property="og:title" content="{headline}">',
        f'<meta property="og:description" content="{summary or deck}">',
        f'<meta property="og:site_name" content="한국정치경제신문">',
        f'<meta property="og:url" content="{SITE_URL}/articles/{article["id"]}.html">',
    ]
    if og_image:
        og_tags.append(f'<meta property="og:image" content="{og_image}">')

    # Twitter Card (카톡도 이거 읽음)
    twitter_tags = [
        f'<meta name="twitter:card" content="{"summary_large_image" if og_image else "summary"}">',
        f'<meta name="twitter:title" content="{headline}">',
        f'<meta name="twitter:description" content="{summary or deck}">',
    ]
    if og_image:
        twitter_tags.append(f'<meta name="twitter:image" content="{og_image}">')

    meta_html = "\n".join(og_tags + twitter_tags)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline} · 한국정치경제신문</title>
<meta name="description" content="{summary or deck}">
<meta name="keywords" content="한국정치경제신문, {dept}, {headline}, 박창원, 종합일간지">
<meta name="author" content="한국정치경제신문 · 박창원">
<meta name="robots" content="index, follow">

{meta_html}

<script async src="https://www.googletagmanager.com/gtag/js?id=G-WHJER2HRM9"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-WHJER2HRM9');
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Noto+Serif+KR:wght@300;400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../style.css">
</head>
<body>

<button class="share-btn" onclick="(function(){{
  var u=location.protocol==='file:'?'{SITE_URL}/articles/{article["id"]}.html':location.href;
  navigator.clipboard.writeText(u).then(function(){{
    var b=document.querySelector('.share-btn');
    b.textContent='✓ 복사됨!';b.classList.add('copied');
    setTimeout(function(){{b.textContent='🔗 공유 URL 복사';b.classList.remove('copied');}},2000);
  }}).catch(function(){{prompt('이 URL을 복사하세요 (Ctrl+C):',u);}});
}})()">🔗 공유 URL 복사</button>

<div class="paper">

  <div class="top-strip">
    <span>한국정치경제신문</span>
    <span>창간 2026년 1월 1일</span>
    <span>{date.replace('-', '.')}</span>
  </div>

  <header class="masthead">
    <h1><a href="../index.html">한국정치경제신문</a></h1>
    <p class="tagline">정확한 사실 · 깊은 시각</p>
  </header>

  <nav class="nav">
    <a href="../index.html">1 면</a>
    <a href="../archive.html">아 카 이 브</a>
    <a href="../videos.html">뉴 스 영 상</a>
    <a href="../about.html">발 행 인</a>
  </nav>

  <article class="article-page">
    <p class="dept-row"><span class="dept-tag dept-tag-{dept}">{dept}부</span></p>
    <h1>{headline}</h1>
    <p class="deck">{deck}</p>
    <div class="meta-row">
      <span>{date.replace('-', '.')}</span>
      <span>{html_escape(reporter_str)}</span>
    </div>
    {photo_html}
    {video_html}
    <div class="body">
{body_html}
    </div>
    <a class="back-link" href="../index.html">← 1면으로</a>
  </article>

  <footer>
    <span>한국정치경제신문 · 발행인 박창원</span>
    <span>© 2026 본지 무단 전재·재배포 금지</span>
  </footer>

</div>
</body>
</html>
"""


def generate_article_pages(articles_data):
    """모든 기사를 articles/{id}.html 로 저장."""
    print("\n" + "=" * 60)
    print("[3.5/4] 기사별 HTML 생성 (카톡 미리보기용)")
    print("=" * 60)

    if not os.path.exists(NEWSPAPER_FOLDER):
        print("[X] 신문 폴더 없음")
        return

    os.makedirs(ARTICLES_DIR, exist_ok=True)

    articles = articles_data.get("articles", [])
    reporters = {r["id"]: r for r in articles_data.get("reporters", [])}
    opinion = articles_data.get("opinion", {})

    count = 0
    for art in articles:
        art_id = art.get("id")
        if not art_id:
            continue
        reporter = reporters.get(art.get("reporterId"))
        page = render_article_page(art, reporter, opinion)
        out_path = os.path.join(ARTICLES_DIR, f"{art_id}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)
        count += 1

    print(f"[OK] {count}개 기사 HTML 생성: {ARTICLES_DIR}")


# ============================================================
# 칼럼/사설 페이지 자동 생성
# ============================================================
COLUMNS_DIR = os.path.join(NEWSPAPER_FOLDER, "column")


def render_column_page(col):
    """사설/칼럼 한 개의 단독 HTML 페이지 텍스트 반환."""
    headline = html_escape(col.get("headline", ""))
    label = html_escape(col.get("label", "사 설"))
    date = col.get("date", "")
    photo = col.get("photo", "")
    photo_caption = html_escape(col.get("photoCaption", ""))
    author_name = html_escape(col.get("authorName", ""))
    author_title = html_escape(col.get("authorTitle", ""))
    author_photo = col.get("authorPhoto", "")
    author_legacy = html_escape(col.get("author", ""))

    # 본문 처리 (\n\n 으로 문단 구분)
    body_text = col.get("body", "")
    paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]
    body_html = "\n".join(f"      <p>{html_escape(p)}</p>" for p in paragraphs)

    # 첫 문단 발췌 (미리보기용)
    excerpt = paragraphs[0][:120] if paragraphs else ""

    # 칼럼 사진 블록
    if photo:
        if photo.startswith("data:") or photo.startswith("http"):
            img_src = photo
        else:
            img_src = f"../{photo}"
        photo_html = f'''<div class="column-photo">
        <img src="{img_src}" alt="">
        <p class="caption">{photo_caption}</p>
      </div>'''
    else:
        photo_html = ""

    # 필자 사진 블록
    if author_photo or author_name or author_title:
        if author_photo:
            if author_photo.startswith("data:") or author_photo.startswith("http"):
                ap_src = author_photo
            else:
                ap_src = f"../{author_photo}"
            author_img = f'<img class="author-photo" src="{ap_src}" alt="">'
        else:
            author_img = ''
        author_html = f'''<div class="author-row" style="display:flex">
        <div class="author-text">
          <span class="name">{author_name}</span>
          <span>{author_title}</span>
        </div>
        {author_img}
      </div>'''
    elif author_legacy:
        author_html = f'<p class="author">{author_legacy}</p>'
    else:
        author_html = ""

    # OG 이미지 — photoFile(추출된 파일) 우선, 없으면 일반 photo 경로
    photo_for_og = col.get("photoFile") or (photo if photo and not photo.startswith("data:") else "")
    if not photo_for_og:
        # 칼럼 사진 없으면 필자 사진 사용
        photo_for_og = col.get("authorPhotoFile") or ""
    if photo_for_og:
        og_image = photo_for_og if photo_for_og.startswith("http") else f"{SITE_URL}/{photo_for_og}"
    else:
        og_image = ""

    og_tags = [
        f'<meta property="og:type" content="article">',
        f'<meta property="og:title" content="{headline}">',
        f'<meta property="og:description" content="{html_escape(excerpt)}">',
        f'<meta property="og:site_name" content="한국정치경제신문">',
        f'<meta property="og:url" content="{SITE_URL}/column/{col["id"]}.html">',
    ]
    if og_image:
        og_tags.append(f'<meta property="og:image" content="{og_image}">')

    twitter_tags = [
        f'<meta name="twitter:card" content="{"summary_large_image" if og_image else "summary"}">',
        f'<meta name="twitter:title" content="{headline}">',
        f'<meta name="twitter:description" content="{html_escape(excerpt)}">',
    ]
    if og_image:
        twitter_tags.append(f'<meta name="twitter:image" content="{og_image}">')

    meta_html = "\n".join(og_tags + twitter_tags)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline} · 한국정치경제신문</title>
<meta name="description" content="{html_escape(excerpt)}">
<meta name="keywords" content="한국정치경제신문, 사설, 칼럼, {author_name}, 박창원">
<meta name="author" content="한국정치경제신문">
<meta name="robots" content="index, follow">

{meta_html}

<script async src="https://www.googletagmanager.com/gtag/js?id=G-WHJER2HRM9"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-WHJER2HRM9');
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=Noto+Serif+KR:wght@300;400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../style.css">
</head>
<body>

<button class="share-btn" onclick="(function(){{
  var u=location.protocol==='file:'?'{SITE_URL}/column/{col["id"]}.html':location.href;
  navigator.clipboard.writeText(u).then(function(){{
    var b=document.querySelector('.share-btn');
    b.textContent='✓ 복사됨!';b.classList.add('copied');
    setTimeout(function(){{b.textContent='🔗 공유 URL 복사';b.classList.remove('copied');}},2000);
  }}).catch(function(){{prompt('이 URL을 복사하세요 (Ctrl+C):',u);}});
}})()">🔗 공유 URL 복사</button>

<div class="paper">

  <div class="top-strip">
    <span>한국정치경제신문</span>
    <span>창간 2026년 1월 1일</span>
    <span>{date.replace('-', '.')}</span>
  </div>

  <header class="masthead">
    <h1><a href="../index.html">한국정치경제신문</a></h1>
    <p class="tagline">정확한 사실 · 깊은 시각</p>
  </header>

  <nav class="nav">
    <a href="../index.html">1 면</a>
    <a href="../archive.html">아 카 이 브</a>
    <a href="../videos.html">뉴 스 영 상</a>
    <a href="../about.html">발 행 인</a>
  </nav>

  <section class="opinion" style="max-width:720px;margin:30px auto 0">
    <p class="label">{label}</p>
    <h2>{headline}</h2>
    {photo_html}
    <div>
{body_html}
    </div>
    {author_html}
    <p style="text-align:center;margin-top:40px;padding-top:20px;border-top:0.5px solid var(--hair);font-size:13px;color:var(--ink-mute)">
      <a href="../index.html" style="color:inherit;text-decoration:none;letter-spacing:2px">← 1면으로</a>
    </p>
  </section>

  <footer>
    <span>한국정치경제신문 · 발행인 박창원</span>
    <span>© 2026 본지 무단 전재·재배포 금지</span>
  </footer>

</div>
</body>
</html>
"""


def generate_column_pages(articles_data):
    """모든 사설을 column/{id}.html 로 저장."""
    print("\n" + "=" * 60)
    print("[3.7/4] 사설/칼럼 HTML 생성")
    print("=" * 60)

    if not os.path.exists(NEWSPAPER_FOLDER):
        print("[X] 신문 폴더 없음")
        return

    os.makedirs(COLUMNS_DIR, exist_ok=True)

    columns = articles_data.get("columns", [])
    count = 0
    for col in columns:
        col_id = col.get("id")
        if not col_id:
            continue
        page = render_column_page(col)
        out_path = os.path.join(COLUMNS_DIR, f"{col_id}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)
        count += 1

    print(f"[OK] {count}개 사설 HTML 생성: {COLUMNS_DIR}")


# ============================================================
# Base64 사진 자동 추출 (카톡 미리보기용)
# ============================================================
import base64

AUTO_IMAGES_DIR = os.path.join(NEWSPAPER_FOLDER, "images", "auto")


def extract_base64_photo(data_url, file_id):
    """Base64 사진을 실제 파일로 저장하고 경로 반환."""
    if not data_url or not data_url.startswith("data:"):
        return ""
    try:
        header, b64data = data_url.split(",", 1)
        if "image/png" in header:
            ext = "png"
        elif "image/webp" in header:
            ext = "webp"
        else:
            ext = "jpg"
        os.makedirs(AUTO_IMAGES_DIR, exist_ok=True)
        out_path = os.path.join(AUTO_IMAGES_DIR, f"{file_id}.{ext}")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64data))
        return f"images/auto/{file_id}.{ext}"
    except Exception as e:
        print(f"   [!] Base64 추출 실패 ({file_id}): {e}")
        return ""


def extract_all_base64_photos(articles_data):
    """articles.json 안의 모든 Base64 사진을 파일로 추출하고 photoFile 필드 추가."""
    print("\n" + "=" * 60)
    print("[3.3/4] Base64 사진 추출 (카톡 미리보기용)")
    print("=" * 60)

    count = 0
    for art in articles_data.get("articles", []):
        if art.get("photo", "").startswith("data:"):
            path = extract_base64_photo(art["photo"], art["id"])
            if path:
                art["photoFile"] = path
                count += 1

    for col in articles_data.get("columns", []):
        if col.get("photo", "").startswith("data:"):
            path = extract_base64_photo(col["photo"], col["id"])
            if path:
                col["photoFile"] = path
                count += 1
        if col.get("authorPhoto", "").startswith("data:"):
            path = extract_base64_photo(col["authorPhoto"], col["id"] + "_author")
            if path:
                col["authorPhotoFile"] = path
                count += 1

    print(f"[OK] {count}개 사진 파일로 추출: {AUTO_IMAGES_DIR}")


# ============================================================
# GitHub 업로드
# ============================================================
def upload_to_github():
    print("\n" + "=" * 60)
    print("[4/4] GitHub Pages 업로드")
    print("=" * 60)
    if not os.path.exists(NEWSPAPER_FOLDER):
        print(f"[X] 신문 폴더 없음")
        return False
    try:
        subprocess.run(["git", "add", "."], cwd=NEWSPAPER_FOLDER, check=True)
        result = subprocess.run(
            ["git", "commit", "-m", "Daily update"],
            cwd=NEWSPAPER_FOLDER,
            capture_output=True, text=True
        )
        push_result = subprocess.run(
            ["git", "push"], cwd=NEWSPAPER_FOLDER,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if push_result.returncode == 0:
            print("[OK] GitHub 업로드 완료")
            print("  URL: https://pcwon2026-ctrl.github.io/news/")
            return True
        else:
            print("[X] GitHub 업로드 실패")
            print(push_result.stderr or push_result.stdout)
            return False
    except FileNotFoundError:
        print("[X] git 명령어를 찾을 수 없음")
        return False
    except Exception as e:
        print(f"[X] 업로드 중 에러: {e}")
        return False


# ============================================================
# 메인
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("[0/3] articles.json 로드")
    print("=" * 60)
    articles_data = load_articles()

    indices = collect_indices()

    print("\n" + "=" * 60)
    print("[1.5/3] 해외 지수 수집 (Yahoo Finance)")
    print("=" * 60)
    overseas = collect_overseas()

    js_text = build_data(articles_data, indices, overseas)
    if save_file(js_text):
        extract_all_base64_photos(articles_data)
        generate_article_pages(articles_data)
        generate_column_pages(articles_data)
        print("\n[OK] 신문 데이터 갱신 완료")
        upload_to_github()
        print("\n  브라우저: https://pcwon2026-ctrl.github.io/news/")
