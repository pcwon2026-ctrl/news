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

    // ---- 사설 ----
    if (D.opinion) {
      set('[data-opinion-label]', D.opinion.label);
      set('[data-opinion-headline]', D.opinion.headline);
      set('[data-opinion-author]', D.opinion.author);
      if (D.opinion.body) {
        html('[data-opinion-body]', D.opinion.body.map(p => `<p>${p}</p>`).join(''));
      }

      // 칼럼 사진 처리 (본문 위 큰 사진)
      const opPhoto = $('[data-opinion-photo]');
      if (opPhoto) {
        if (D.opinion.photo) {
          opPhoto.style.display = 'block';
          const img = opPhoto.querySelector('img');
          const cap = opPhoto.querySelector('.caption');
          if (img) img.src = D.opinion.photo;
          if (cap) cap.textContent = D.opinion.photoCaption || '';
        } else {
          opPhoto.style.display = 'none';
        }
      }

      // 필자 사진 처리
      const authorRow = $('[data-opinion-author-row]');
      const authorPara = $('[data-opinion-author]');
      if (D.opinion.authorPhoto) {
        // 사진 있으면: 필자 카드 보이고, 기존 텍스트 author 숨김
        authorRow.style.display = 'flex';
        if (authorPara) authorPara.style.display = 'none';
        const img = $('[data-opinion-author-photo]');
        if (img) img.src = D.opinion.authorPhoto;
        set('[data-opinion-author-name]', D.opinion.authorName || '');
        set('[data-opinion-author-title]', D.opinion.authorTitle || D.opinion.author || '');
      } else {
        // 사진 없으면 기존 텍스트 author 만 보임
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
  // archive.html — 아카이브 페이지
  // ============================================================
  function renderArchive() {
    const all = (D.articles || []).slice().sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
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
        const r = reporterById(a.reporterId);
        return `
          <div class="archive-item">
            <a href="articles/${a.id}.html">
              <div class="row">
                <span class="dept">${deptLabel(a.dept)}부</span>
                <span class="date">${fmtDate(a.date)}${r ? ' · ' + r.name + ' 기자' : ''}</span>
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

    // 필터 클릭 이벤트
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
