// ============================================================
// 한국정치경제신문 · 렌더링 엔진 (Phase 1)
// ----------------------------------------------------------
// 데이터 소스:
//   window.NEWSPAPER = { reporters, articles, opinion, market, ... }
//   articles 배열은 매일 누적되며, 각 기사는 고유 id 보유.
// 페이지별 렌더링:
//   index.html   → 오늘자 기사 카드 + 시세박스 + 사설
//   article.html → ?id=xxx 로 받은 한 기사의 전문
//   archive.html → 모든 기사 목록 + 부서 필터
// ============================================================

(function () {

  // ============================================================
  // 공유 버튼 자동 생성 — 모든 페이지에 우측 상단 떠 있음
  // PC 신문(file:///)에서도 진짜 인터넷 URL을 클립보드에 복사
  // ============================================================
  const SITE_URL = 'https://pcwon2026-ctrl.github.io/news';

  function makeShareUrl() {
    const pathname = location.pathname;
    const search = location.search;

    // file:/// 경로면 → 신문 폴더 이후 부분만 추출해서 https URL로 변환
    if (location.protocol === 'file:') {
      // 예: file:///C:/Users/intty/한국정치경제신문/column/c2026....html
      //  → /column/c2026....html 만 뽑아내기
      const idx = pathname.indexOf('/한국정치경제신문/');
      if (idx >= 0) {
        const rel = pathname.substring(idx + '/한국정치경제신문/'.length);
        return SITE_URL + '/' + rel + search;
      }
      // fallback — index.html 가정
      return SITE_URL + '/';
    }

    // https://, http:// 이면 그대로
    return location.origin + pathname + search;
  }

  function injectShareButton() {
    const btn = document.createElement('button');
    btn.className = 'share-btn';
    btn.textContent = '🔗 공유 URL 복사';
    btn.onclick = async () => {
      const url = makeShareUrl();
      try {
        await navigator.clipboard.writeText(url);
        btn.textContent = '✓ 복사됨!';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.textContent = '🔗 공유 URL 복사';
          btn.classList.remove('copied');
        }, 2000);
      } catch (e) {
        // clipboard API 실패 시 fallback: 화면에 띄워서 직접 복사
        prompt('이 URL을 복사하세요 (Ctrl+C):', url);
      }
    };
    document.body.appendChild(btn);
  }

  injectShareButton();

  // ---- 공통: 날짜·호수·메뉴 ----
  const FOUNDING_DATE = new Date(2026, 0, 1);
  const today = new Date();
  const days = ['일', '월', '화', '수', '목', '금', '토'];
  const todayStr = `${today.getFullYear()}년 ${today.getMonth() + 1}월 ${today.getDate()}일 (${days[today.getDay()]}요일)`;
  const issueStr = `제 ${Math.floor((today - FOUNDING_DATE) / 86400000) + 1}호`;
  document.querySelectorAll('[data-today]').forEach(el => el.textContent = todayStr);
  document.querySelectorAll('[data-issue]').forEach(el => el.textContent = issueStr);

  const page = (location.pathname.split('/').pop() || 'index.html');
  document.querySelectorAll('.nav a').forEach(a => {
    if (a.getAttribute('href') === page) a.classList.add('active');
  });

  // ---- 데이터 ----
  const D = window.NEWSPAPER;
  if (!D) return;

  // 기자 ID로 기자 정보 찾기
  const reporterById = (id) => (D.reporters || []).find(r => r.id === id) || null;

  // 부서 색상 매핑 (확장 가능)
  const deptLabel = (d) => d || '';

  // 날짜 표시 (YYYY-MM-DD → 'YYYY.MM.DD')
  const fmtDate = (s) => s ? s.replace(/-/g, '.') : '';

  // 헬퍼
  const $ = (sel) => document.querySelector(sel);
  const set = (sel, text) => { const el = $(sel); if (el && text !== undefined) el.textContent = text; };
  const html = (sel, h) => { const el = $(sel); if (el) el.innerHTML = h; };

  // ============================================================
  // index.html — 1면 (오늘자 기사 카드 + 시세 + 사설)
  // ============================================================
  function renderHome() {
    const allArticles = D.articles || [];

    // 오늘 날짜 기준 기사만 (없으면 가장 최근 날짜)
    let activeDate = today.toISOString().slice(0, 10);
    const datesAvailable = [...new Set(allArticles.map(a => a.date))].sort().reverse();
    if (datesAvailable.length && !allArticles.some(a => a.date === activeDate)) {
      activeDate = datesAvailable[0];
    }
    const todayArticles = allArticles.filter(a => a.date === activeDate);
    const lead = todayArticles.find(a => a.isLead);
    const others = todayArticles.filter(a => !a.isLead);

    // ---- 톱기사 영역 ----
    if (lead) {
      set('[data-lead-dept]', `${deptLabel(lead.dept)}부`);
      set('[data-lead-headline]', lead.headline);
      set('[data-lead-deck]', lead.deck);
      const reporter = reporterById(lead.reporterId);
      set('[data-lead-byline]', reporter ? `${reporter.dept}부 / ${reporter.name}` : '');

      const photoBox = $('[data-lead-photo]');
      if (photoBox) {
        if (lead.photo) {
          photoBox.style.display = 'block';
          const img = photoBox.querySelector('img');
          const cap = photoBox.querySelector('.caption');
          if (img) img.src = lead.photo;
          if (cap) cap.textContent = lead.photoCaption || '';
        } else {
          photoBox.style.display = 'none';
        }
      }

      // 톱기사는 요약 표시 + 전문 링크
      const leadSummary = $('[data-lead-summary]');
      if (leadSummary) leadSummary.textContent = lead.summary || '';

      const leadLink = $('[data-lead-link]');
      if (leadLink) leadLink.href = `articles/${lead.id}.html`;
    }

    // ---- 기사 카드 목록 ----
    const cardsHtml = others.map(a => {
      const r = reporterById(a.reporterId);
      const meta = r ? `${r.dept}부 / ${r.name}` : '';
      const thumb = a.photo ? `<img class="thumb" src="${a.photo}" alt="">` : '';
      return `
        <a class="article-card-link" href="articles/${a.id}.html">
          ${thumb}
          <p class="dept">${deptLabel(a.dept)}</p>
          <h3>${a.headline}</h3>
          <p class="summary">${a.summary || ''}</p>
          <p class="meta">${meta}</p>
        </a>
      `;
    }).join('');
    html('[data-article-cards]', cardsHtml);

    // ---- 시세 박스 ----
    if (D.market && Array.isArray(D.market)) {
      const rows = D.market.map(r =>
        `<tr><td>${r.name}</td><td class="${r.dir}">${r.value}</td></tr>`
      ).join('');
      html('[data-market-small]', rows);
    }

    // ---- 사설 (columns 배열에서 최신 1개) ----
    const cols = (D.columns || []).slice().sort((a, b) =>
      b.date.localeCompare(a.date) || b.id.localeCompare(a.id)
    );
    const op = cols[0];  // 가장 최신 사설
    if (op) {
      set('[data-opinion-label]', op.label);
      set('[data-opinion-headline]', op.headline);
      set('[data-opinion-author]', op.author);
      if (op.body) {
        const paras = op.body.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
        html('[data-opinion-body]', paras.map(p => `<p>${p}</p>`).join(''));
      }

      // 사설 단독 URL 링크
      const opLink = $('[data-opinion-link]');
      if (opLink) opLink.href = `column/${op.id}.html`;

      // 칼럼 사진 (본문 위 큰 사진)
      const opPhoto = $('[data-opinion-photo]');
      if (opPhoto) {
        if (op.photo) {
          opPhoto.style.display = 'block';
          const img = opPhoto.querySelector('img');
          const cap = opPhoto.querySelector('.caption');
          if (img) img.src = op.photo;
          if (cap) cap.textContent = op.photoCaption || '';
        } else {
          opPhoto.style.display = 'none';
        }
      }

      // 필자 사진 처리
      const authorRow = $('[data-opinion-author-row]');
      const authorPara = $('[data-opinion-author]');
      if (op.authorPhoto) {
        authorRow.style.display = 'flex';
        if (authorPara) authorPara.style.display = 'none';
        const img = $('[data-opinion-author-photo]');
        if (img) img.src = op.authorPhoto;
        set('[data-opinion-author-name]', op.authorName || '');
        set('[data-opinion-author-title]', op.authorTitle || op.author || '');
      } else if (op.authorName || op.authorTitle) {
        // 사진 없어도 이름/직책 있으면 표시
        authorRow.style.display = 'flex';
        if (authorPara) authorPara.style.display = 'none';
        const img = $('[data-opinion-author-photo]');
        if (img) img.style.display = 'none';
        set('[data-opinion-author-name]', op.authorName || '');
        set('[data-opinion-author-title]', op.authorTitle || '');
      } else {
        authorRow.style.display = 'none';
        if (authorPara) authorPara.style.display = '';
      }
    }
  }

  // ============================================================
  // article.html — 기사 전문 페이지
  // ============================================================
  function renderArticle() {
    const params = new URLSearchParams(location.search);
    const id = params.get('id');
    if (!id) {
      html('[data-article-content]', '<p style="text-align:center;color:#888">기사 ID가 없습니다.</p>');
      return;
    }

    const a = (D.articles || []).find(x => x.id === id);
    if (!a) {
      html('[data-article-content]', `<p style="text-align:center;color:#888">기사를 찾을 수 없습니다 (id: ${id})</p>`);
      return;
    }

    const reporter = reporterById(a.reporterId);
    const reporterStr = reporter ? `${reporter.dept}부 ${reporter.name} 기자` : '';

    // 페이지 제목도 바꾸기
    document.title = `${a.headline} · 한국정치경제신문`;

    set('[data-art-dept]', `${deptLabel(a.dept)}부`);
    set('[data-art-headline]', a.headline);
    set('[data-art-deck]', a.deck || '');
    set('[data-art-date]', fmtDate(a.date));
    set('[data-art-reporter]', reporterStr);

    // 사진 (전문 페이지에서는 본문 위)
    const photoBox = $('[data-art-photo]');
    if (photoBox) {
      if (a.photo) {
        photoBox.style.display = 'block';
        const img = photoBox.querySelector('img');
        const cap = photoBox.querySelector('.caption');
        if (img) img.src = a.photo;
        if (cap) cap.textContent = a.photoCaption || '';
      } else {
        photoBox.style.display = 'none';
      }
    }

    // 본문 — \n\n 으로 문단 구분
    const paragraphs = (a.body || '').split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
    html('[data-art-body]', paragraphs.map(p => `<p>${p}</p>`).join(''));
  }

  // ============================================================
  // archive.html — 아카이브 페이지 (기사 + 사설)
  // ============================================================
  function renderArchive() {
    // 기사 + 사설 합치기
    const articles = (D.articles || []).map(a => ({
      kind: 'article',
      id: a.id,
      date: a.date,
      dept: a.dept,
      headline: a.headline,
      summary: a.summary,
      reporterId: a.reporterId
    }));
    const columns = (D.columns || []).map(c => ({
      kind: 'column',
      id: c.id,
      date: c.date,
      dept: '사설',
      headline: c.headline,
      summary: (c.body || '').split('\n\n')[0].slice(0, 80) + '...',
      authorName: c.authorName
    }));
    const all = [...articles, ...columns].sort((a, b) =>
      b.date.localeCompare(a.date) || b.id.localeCompare(a.id)
    );
    const departments = ['전체', ...new Set(all.map(a => a.dept))];

    // 필터 버튼
    const filterEl = $('[data-archive-filters]');
    if (filterEl) {
      filterEl.innerHTML = departments.map(d =>
        `<button data-filter="${d}" class="${d === '전체' ? 'active' : ''}">${d}</button>`
      ).join('');
    }

    // 기사 목록
    function showList(filter) {
      const filtered = filter === '전체' ? all : all.filter(a => a.dept === filter);
      const itemsHtml = filtered.map(a => {
        let metaRight = '';
        if (a.kind === 'article') {
          const r = reporterById(a.reporterId);
          metaRight = `${fmtDate(a.date)}${r ? ' · ' + r.name + ' 기자' : ''}`;
        } else {
          metaRight = `${fmtDate(a.date)}${a.authorName ? ' · ' + a.authorName : ''}`;
        }
        const url = a.kind === 'article'
          ? `articles/${a.id}.html`
          : `column/${a.id}.html`;
        return `
          <div class="archive-item">
            <a href="${url}">
              <div class="row">
                <span class="dept">${deptLabel(a.dept)}${a.kind === 'article' ? '부' : ''}</span>
                <span class="date">${metaRight}</span>
              </div>
              <h3>${a.headline}</h3>
              <p class="summary">${a.summary || ''}</p>
            </a>
          </div>
        `;
      }).join('');
      html('[data-archive-list]', itemsHtml || '<p style="text-align:center;color:#888;padding:40px">기사가 없습니다.</p>');
    }
    showList('전체');

    if (filterEl) {
      filterEl.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON') return;
        filterEl.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        showList(e.target.dataset.filter);
      });
    }
  }

  // ============================================================
  // 페이지 분기
  // ============================================================
  if (page === '' || page === 'index.html') renderHome();
  else if (page === 'article.html') renderArticle();
  else if (page === 'archive.html') renderArchive();

})();
