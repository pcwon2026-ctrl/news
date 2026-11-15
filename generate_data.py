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
from urllib.parse import quote as _urlquote
from overseas_indices import collect_overseas, fetch_yahoo


# ============================================================
# 설정
# ============================================================
# 이 파일이 들어있는 폴더를 신문 폴더로 자동 인식
NEWSPAPER_FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(NEWSPAPER_FOLDER, "data.js")
ARTICLES_FILE = os.path.join(NEWSPAPER_FOLDER, "articles.json")

# 국내 지수 — 키움 대신 Yahoo Finance에서 받아옴 (로그인 불필요)
INDEX_LIST = [
    {"code": "^KS11",  "name": "KOSPI"},
    {"code": "^KQ11",  "name": "KOSDAQ"},
    {"code": "^KS200", "name": "KOSPI200"},
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
    print("[1/3] 국내 지수 수집 (Yahoo Finance)")
    print("=" * 60)

    results = {}
    for idx in INDEX_LIST:
        code, name = idx["code"], idx["name"]
        print(f"   {name} ({code}) 조회 중...", end=" ")
        data = fetch_yahoo(code)
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
SITE_URL = "https://www.kpen.kr"
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


# ============================================================
# SEO 도우미 — 태그 · 키워드 · 사진 alt · 파일명
# ============================================================
import re as _re

ARCHIVE_URL = f"{SITE_URL}/archive.html"


def parse_tags(raw):
    """'#젠슨황 #트럼프, 엔비디아' → ['젠슨황', '트럼프', '엔비디아'] (중복 제거, 순서 유지)."""
    if not raw:
        return []
    if isinstance(raw, list):
        parts = raw
    else:
        parts = _re.split(r"[#,\s]+", str(raw))
    seen, out = set(), []
    for p in parts:
        p = p.strip().strip("#").strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def keyword_slug(text, limit=40):
    """사진 파일명에 넣을 키워드 조각. 한글·영문·숫자만 남기고 공백은 '-'."""
    if not text:
        return ""
    s = _re.sub(r"[^\w가-힣]+", "-", str(text), flags=_re.UNICODE)
    s = _re.sub(r"-{2,}", "-", s).strip("-_")
    return s[:limit].rstrip("-_")


def build_keywords(base, tags, extra=""):
    """<meta name="keywords"> 내용. base 리스트 + 태그 + 추가 문자열, 중복 제거."""
    items = []
    for k in list(base) + list(tags) + ([extra] if extra else []):
        k = str(k).strip()
        if k and k not in items:
            items.append(k)
    return ", ".join(items)


def render_tags_block(tags, label="태그"):
    """기사 하단 태그란 HTML. 태그 클릭 → 아카이브 검색."""
    if not tags:
        return ""
    links = "\n".join(
        f'      <a class="tag" href="{ARCHIVE_URL}?tag={html_escape(t)}" rel="tag">#{html_escape(t)}</a>'
        for t in tags
    )
    return f'''<div class="article-tags" aria-label="{label}">
      <span class="tags-label">{label}</span>
{links}
    </div>'''


def render_tag_meta(tags):
    """포털·SNS가 읽는 article:tag 메타 태그."""
    return "\n".join(f'<meta property="article:tag" content="{html_escape(t)}">' for t in tags)


def render_jsonld(kind, headline, description, url, image, date, author, tags, section=""):
    """구글 뉴스·네이버가 읽는 NewsArticle 구조화 데이터."""
    data = {
        "@context": "https://schema.org",
        "@type": "NewsArticle" if kind == "article" else "OpinionNewsArticle",
        "headline": headline,
        "description": description,
        "mainEntityOfPage": url,
        "url": url,
        "datePublished": date,
        "dateModified": date,
        "inLanguage": "ko",
        "author": {"@type": "Person", "name": author or "박창원"},
        "publisher": {
            "@type": "NewsMediaOrganization",
            "name": "한국정치경제신문",
            "url": SITE_URL,
        },
    }
    if image:
        data["image"] = [image]
    if tags:
        data["keywords"] = ", ".join(tags)
    if section:
        data["articleSection"] = section
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False)
            + "</script>")


def photo_alt_text(caption, headline, tags):
    """사진 alt — 캡션이 있으면 캡션, 없으면 헤드라인 + 태그 앞 3개."""
    if caption:
        return caption
    core = headline or ""
    if tags:
        core = f"{core} — {' '.join(tags[:3])}" if core else " ".join(tags[:3])
    return core


def render_article_page(article, reporter, opinion):
    """기사 한 개의 정적 HTML 페이지 텍스트 반환."""
    headline = html_escape(article.get("headline", ""))
    deck = html_escape(article.get("deck", ""))
    summary = html_escape(article.get("summary", ""))
    dept = article.get("dept", "")
    date = article.get("date", "")
    photo = article.get("photo", "")
    photo_caption_raw = article.get("photoCaption", "")
    photo_caption = html_escape(photo_caption_raw)
    tags = parse_tags(article.get("tags", ""))
    reporter_str = ""
    reporter_name = ""
    if reporter:
        reporter_name = reporter.get("name", "")
        reporter_str = f"{reporter.get('dept','')}부 {reporter_name} 기자"

    # 본문 paragraph 처리
    body_text = article.get("body", "")
    paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]
    body_html = "\n".join(f"      <p>{html_escape(p)}</p>" for p in paragraphs)

    # 사진 블록 — 추출된 파일(키워드 파일명) 우선, 없으면 원본 경로
    photo_src_path = article.get("photoFile") or photo
    photo_alt = html_escape(photo_alt_text(photo_caption_raw, article.get("headline", ""), tags))
    if photo_src_path:
        if photo_src_path.startswith("data:") or photo_src_path.startswith("http"):
            img_src = photo_src_path
        else:
            img_src = f"../{_urlquote(photo_src_path)}"
        photo_html = f'''<figure class="photo">
        <img src="{img_src}" alt="{photo_alt}" title="{photo_alt}" loading="lazy">
        <figcaption class="caption">{photo_caption}</figcaption>
      </figure>'''
    else:
        photo_html = ""

    # 동영상 블록 (서버 사이드에서 임베드 코드 생성)
    video_url = article.get("video", "").strip()
    video_caption = html_escape(article.get("videoCaption", ""))
    video_html = build_video_embed(video_url, video_caption)

    # OG 이미지 URL — photoFile(추출된 파일) 우선
    photo_for_og = article.get("photoFile") or (photo if photo and not photo.startswith("data:") else "")
    if photo_for_og:
        og_image = photo_for_og if photo_for_og.startswith("http") else f"{SITE_URL}/{_urlquote(photo_for_og)}"
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
        og_tags.append(f'<meta property="og:image:alt" content="{photo_alt}">')
    og_tags.append(f'<meta property="article:published_time" content="{date}">')
    og_tags.append(f'<meta property="article:section" content="{dept}">')

    page_url = f"{SITE_URL}/articles/{article['id']}.html"
    meta_html = "\n".join(og_tags + twitter_tags + [render_tag_meta(tags)])
    keywords = build_keywords(
        ["한국정치경제신문", dept, article.get("headline", ""), "박창원", "종합일간지"],
        tags, article.get("photoCaption", ""))
    jsonld = render_jsonld("article", article.get("headline", ""),
                           article.get("summary") or article.get("deck", ""),
                           page_url, og_image, date, reporter_name, tags, section=dept)
    tags_html = render_tags_block(tags)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline} · 한국정치경제신문</title>
<meta name="description" content="{summary or deck}">
<meta name="keywords" content="{html_escape(keywords)}">
<meta name="news_keywords" content="{html_escape(', '.join(tags))}">
<meta name="author" content="한국정치경제신문 · 박창원">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{page_url}">

{meta_html}
{jsonld}

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
    {tags_html}
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
    photo_caption_raw = col.get("photoCaption", "")
    photo_caption = html_escape(photo_caption_raw)
    tags = parse_tags(col.get("tags", ""))
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

    # 칼럼 사진 블록 — 추출된 파일(키워드 파일명) 우선
    photo_src_path = col.get("photoFile") or photo
    photo_alt = html_escape(photo_alt_text(photo_caption_raw, col.get("headline", ""), tags))
    if photo_src_path:
        if photo_src_path.startswith("data:") or photo_src_path.startswith("http"):
            img_src = photo_src_path
        else:
            img_src = f"../{_urlquote(photo_src_path)}"
        photo_html = f'''<figure class="column-photo">
        <img src="{img_src}" alt="{photo_alt}" title="{photo_alt}" loading="lazy">
        <figcaption class="caption">{photo_caption}</figcaption>
      </figure>'''
    else:
        photo_html = ""

    # 필자 사진 블록
    if author_photo or author_name or author_title:
        if author_photo:
            if author_photo.startswith("data:") or author_photo.startswith("http"):
                ap_src = author_photo
            else:
                ap_src = f"../{author_photo}"
            author_img = f'<img class="author-photo" src="{ap_src}" alt="{author_name} {author_title}" loading="lazy">'
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
        og_image = photo_for_og if photo_for_og.startswith("http") else f"{SITE_URL}/{_urlquote(photo_for_og)}"
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
        og_tags.append(f'<meta property="og:image:alt" content="{photo_alt}">')
    og_tags.append(f'<meta property="article:published_time" content="{date}">')
    og_tags.append(f'<meta property="article:section" content="사설">')

    page_url = f"{SITE_URL}/column/{col['id']}.html"
    meta_html = "\n".join(og_tags + twitter_tags + [render_tag_meta(tags)])
    keywords = build_keywords(
        ["한국정치경제신문", "사설", "칼럼", col.get("headline", ""), col.get("authorName", ""), "박창원"],
        tags, col.get("photoCaption", ""))
    jsonld = render_jsonld("column", col.get("headline", ""), excerpt, page_url, og_image,
                           date, col.get("authorName", ""), tags, section="사설")
    tags_html = render_tags_block(tags)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline} · 한국정치경제신문</title>
<meta name="description" content="{html_escape(excerpt)}">
<meta name="keywords" content="{html_escape(keywords)}">
<meta name="news_keywords" content="{html_escape(', '.join(tags))}">
<meta name="author" content="한국정치경제신문">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{page_url}">

{meta_html}
{jsonld}

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
    {tags_html}
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


def seo_photo_name(item, file_id, suffix=""):
    """사진 파일명에 키워드를 넣는다 (검색엔진 이미지 색인용).
    우선순위: 사진 캡션 → 태그 앞 3개 → 헤드라인.
    예) a20261116001_젠슨-황-앨리스-황-엔비디아-AI-칩-중국-유출.jpg
    """
    tags = parse_tags(item.get("tags", ""))
    src = item.get("photoCaption", "") or " ".join(tags[:3]) or item.get("headline", "")
    slug = keyword_slug(src)
    name = f"{file_id}{suffix}"
    return f"{name}_{slug}" if slug else name


def extract_base64_photo(data_url, file_id, item=None, suffix=""):
    """Base64 사진을 실제 파일로 저장하고 경로 반환. item 이 있으면 키워드 파일명."""
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
        base = seo_photo_name(item, file_id, suffix) if item else f"{file_id}{suffix}"
        out_path = os.path.join(AUTO_IMAGES_DIR, f"{base}.{ext}")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64data))
        # 예전 이름(키워드 없는 파일)이 남아 있으면 정리
        for old_ext in ("jpg", "png", "webp"):
            old = os.path.join(AUTO_IMAGES_DIR, f"{file_id}{suffix}.{old_ext}")
            if base != f"{file_id}{suffix}" and os.path.exists(old):
                try:
                    os.remove(old)
                except OSError:
                    pass
        return f"images/auto/{base}.{ext}"
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
            path = extract_base64_photo(art["photo"], art["id"], item=art)
            if path:
                art["photoFile"] = path
                count += 1

    for col in articles_data.get("columns", []):
        if col.get("photo", "").startswith("data:"):
            path = extract_base64_photo(col["photo"], col["id"], item=col)
            if path:
                col["photoFile"] = path
                count += 1
        if col.get("authorPhoto", "").startswith("data:"):
            path = extract_base64_photo(col["authorPhoto"], col["id"], suffix="_author")
            if path:
                col["authorPhotoFile"] = path
                count += 1

    print(f"[OK] {count}개 사진 파일로 추출: {AUTO_IMAGES_DIR}")


# ============================================================
# 1면 index.html 카톡 미리보기 사진(og:image) 자동 갱신
# ============================================================
import re

INDEX_HTML_FILE = os.path.join(NEWSPAPER_FOLDER, "index.html")


def update_index_og_image(articles_data):
    """1면 index.html의 og:image를 가장 최근 사진 있는 기사로 갱신."""
    print("\n" + "=" * 60)
    print("[3.4/4] 1면 카톡 미리보기 사진(og:image) 갱신")
    print("=" * 60)

    if not os.path.exists(INDEX_HTML_FILE):
        print(f"[X] index.html 없음: {INDEX_HTML_FILE}")
        return

    candidates = []
    for a in articles_data.get("articles", []):
        if a.get("photoFile"):
            candidates.append((a, a["photoFile"]))
        elif a.get("photo") and not a.get("photo", "").startswith("data:"):
            candidates.append((a, a["photo"]))

    if not candidates:
        print("[!] 사진 있는 기사가 없음. 건너뜀.")
        return

    candidates.sort(key=lambda x: x[0].get("date", ""), reverse=True)
    top, photo_path = candidates[0]
    og_image_url = photo_path if photo_path.startswith("http") else f"{SITE_URL}/{_urlquote(photo_path.lstrip('/'))}"
    print(f"   톱기사: [{top.get('dept','?')}] {top.get('headline','')[:50]}")
    print(f"   og:image: {og_image_url}")

    with open(INDEX_HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    new_og = f'<meta property="og:image" content="{og_image_url}">'
    new_tw = f'<meta name="twitter:image" content="{og_image_url}">'

    pat = re.compile(r'<meta\s+property=["\']og:image["\'][^>]*?>')
    if pat.search(html):
        html = pat.sub(new_og, html)
    else:
        html = re.sub(r'(<meta\s+property=["\']og:url["\'][^>]*?>)', r'\1\n' + new_og, html, count=1)

    pat = re.compile(r'<meta\s+name=["\']twitter:image["\'][^>]*?>')
    if pat.search(html):
        html = pat.sub(new_tw, html)
    else:
        html = re.sub(r'(<meta\s+name=["\']twitter:card["\'][^>]*?>)', r'\1\n' + new_tw, html, count=1)

    with open(INDEX_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] index.html 갱신 완료")


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
        def git(*args):
            return subprocess.run(
                ["git", *args], cwd=NEWSPAPER_FOLDER,
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )

        git("add", ".")
        git("commit", "-m", "Daily update")

        # GitHub 쪽에 먼저 생긴 변경(예: 도메인 설정 CNAME)을 받아와 합침.
        # 충돌이 나면 컴퓨터 쪽 내용을 우선함.
        print("   GitHub 변경 사항 받아오는 중...")
        pull = git("pull", "--rebase", "--autostash", "-X", "theirs", "origin", "main")
        if pull.returncode != 0:
            print("[!] 받아오기 실패 — 그래도 업로드 시도")
            print((pull.stderr or pull.stdout).strip()[-800:])
            git("rebase", "--abort")

        push_result = git("push", "origin", "main")
        if push_result.returncode == 0:
            print("[OK] GitHub 업로드 완료")
            print("  URL: https://www.kpen.kr/")
            return True
        else:
            print("[X] GitHub 업로드 실패 — 아래 메시지를 캡처해서 보내주세요")
            print((push_result.stderr or push_result.stdout).strip()[-1200:])
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
        update_index_og_image(articles_data)
        generate_article_pages(articles_data)
        generate_column_pages(articles_data)
        print("\n[OK] 신문 데이터 갱신 완료")
        upload_to_github()
        print("\n  브라우저: https://pcwon2026-ctrl.github.io/news/")
