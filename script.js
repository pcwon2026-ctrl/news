// ============================================================
// 한국정치경제신문 · 자동 렌더링 스크립트
// 1. 날짜·호수·메뉴 자동 처리
// 2. data.js 의 NEWSPAPER 데이터를 HTML 에 그려 넣기
// ============================================================

(function () {

  // -------- 1. 날짜와 호수 자동 업데이트 --------
  const FOUNDING_DATE = new Date(2026, 0, 1); // 2026년 1월 1일 창간
  const today = new Date();
  const days = ['일', '월', '화', '수', '목', '금', '토'];

  const yyyy = today.getFullYear();
  const mm = today.getMonth() + 1;
  const dd = today.getDate();
  const day = days[today.getDay()];

  const dateStr = `${yyyy}년 ${mm}월 ${dd}일 (${day}요일)`;
  const issueNum = Math.floor((today - FOUNDING_DATE) / 86400000) + 1;
  const issueStr = `제 ${issueNum.toLocaleString()}호`;

  document.querySelectorAll('[data-today]').forEach(el => el.textContent = dateStr);
  document.querySelectorAll('[data-issue]').forEach(el => el.textContent = issueStr);
  document.title = `한국정치경제신문 · ${yyyy}년 ${mm}월 ${dd}일`;

  // -------- 2. 현재 페이지 메뉴 활성화 --------
  const currentPage = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === currentPage) a.classList.add('active');
    if (currentPage === '' && href === 'index.html') a.classList.add('active');
  });

  // -------- 3. data.js 데이터 렌더링 --------
  if (!window.NEWSPAPER) return; // data.js 가 없으면 종료

  let pageData = null;
  if (currentPage === 'index.html' || currentPage === '') pageData = window.NEWSPAPER.home;
  else if (currentPage === 'politics.html') pageData = window.NEWSPAPER.politics;
  else if (currentPage === 'economy.html') pageData = window.NEWSPAPER.economy;
  if (!pageData) return;

  // --- 헬퍼 ---
  const setText = (sel, txt) => {
    const el = document.querySelector(sel);
    if (el && txt !== undefined) el.textContent = txt;
  };
  const setHTML = (sel, html) => {
    const el = document.querySelector(sel);
    if (el) el.innerHTML = html;
  };

  // --- 톱기사 ---
  function renderLead(d) {
    if (!d) return;
    setText('[data-lead-flag]', d.flag);
    setText('[data-lead-headline]', d.headline);
    setText('[data-lead-deck]', d.deck);
    setText('[data-lead-byline]', d.byline);
    if (d.body) setHTML('[data-lead-body]', d.body.map(p => `<p>${p}</p>`).join(''));

    // 사진 처리
    const photoBox = document.querySelector('[data-lead-photo]');
    const photoImg = document.querySelector('[data-lead-photo-img]');
    const photoCap = document.querySelector('[data-lead-photo-caption]');
    if (photoBox && d.photo) {
      photoBox.style.display = 'block';
      if (photoImg) photoImg.src = d.photo;
      if (photoCap) photoCap.textContent = d.photoCaption || '';
    } else if (photoBox) {
      photoBox.style.display = 'none';
    }
  }

  // --- 일반 기사 1개 ---
  function renderArticle(art) {
    const tag = art.size === 'h4' ? 'h4' : 'h3';
    const bodyClass = art.twoCol ? 'body two-col' : 'body';
    const body = (art.body || []).map(p => `<p>${p}</p>`).join('');
    return `
      <article>
        <${tag}>${art.headline}</${tag}>
        <p class="byline">${art.byline || ''}</p>
        <div class="${bodyClass}">${body}</div>
      </article>
    `;
  }

  // --- 시세 (작은 박스) ---
  function renderMarketSmall(rows) {
    if (!rows) return;
    setHTML('[data-market-small]', rows.map(r =>
      `<tr><td>${r.name}</td><td class="${r.dir}">${r.value}</td></tr>`
    ).join(''));
  }

  // --- 시세 (경제면 3단) ---
  function renderMarketWide(d) {
    if (!d) return;
    setText('[data-market-wide-title]', d.title);
    if (d.cols) {
      setHTML('[data-market-wide-cols]', d.cols.map(col =>
        `<table>${col.map(r =>
          `<tr><td>${r.name}</td><td class="${r.dir}">${r.value}</td></tr>`
        ).join('')}</table>`
      ).join(''));
    }
  }

  // --- 시초가 후보 (1면 리스트) ---
  function renderTierList(arr) {
    if (!arr) return;
    setHTML('[data-tier-list]', arr.map(t => `
      <div class="tier-item">
        <div class="tier-row">
          <span class="tier-name">${t.name}</span>
          <span class="tier-badge">${t.tier}</span>
        </div>
        <p class="tier-note">${t.note}</p>
      </div>
    `).join(''));
  }

  // --- 시초가 후보 (경제면 카드 그리드) ---
  function renderTierGrid(arr) {
    if (!arr) return;
    setHTML('[data-tier-grid]', arr.map(t => `
      <div class="tier-card">
        <div class="tier-row">
          <span class="tier-name">${t.name}</span>
          <span class="tier-badge">${t.tier}</span>
        </div>
        <p class="tier-note">${t.note}</p>
      </div>
    `).join(''));
  }

  // --- 미국發 모멘텀 매핑 ---
  function renderMapping(arr) {
    if (!arr) return;
    setHTML('[data-mapping-rows]', arr.map(m => `
      <tr>
        <td>${m.sector}</td>
        <td class="us">${m.us}</td>
        <td class="kr">${m.kr}</td>
      </tr>
    `).join(''));
  }

  // --- 2단 섹션 (정치/경제면) ---
  function renderSections(sections) {
    if (!sections) return;
    sections.forEach((sec, i) => {
      const target = document.querySelector(`[data-section="${i}"]`);
      if (!target) return;
      target.innerHTML = `
        <div class="section-rule">
          <span class="label">${sec.label}</span>
          <span class="line"></span>
        </div>
        ${sec.articles.map(renderArticle).join('')}
      `;
    });
  }

  // --- 1면 기사 리스트 ---
  function renderArticleList(sel, arr) {
    if (!arr) return;
    setHTML(sel, arr.map(renderArticle).join(''));
  }

  // --- 사설 ---
  function renderOpinion(d) {
    if (!d) return;
    setText('[data-opinion-label]', d.label);
    setText('[data-opinion-headline]', d.headline);
    setText('[data-opinion-author]', d.author);
    if (d.body) setHTML('[data-opinion-body]', d.body.map(p => `<p>${p}</p>`).join(''));
  }

  // -------- 페이지별 실행 --------
  renderLead(pageData.lead);
  renderOpinion(pageData.opinion);

  if (currentPage === 'index.html' || currentPage === '') {
    renderArticleList('[data-politics-articles]', pageData.politicsArticles);
    renderMarketSmall(pageData.market);
    renderArticleList('[data-economy-articles]', pageData.economyArticles);
    renderTierList(pageData.tiers);
  }

  if (currentPage === 'politics.html') {
    renderSections(pageData.sections);
  }

  if (currentPage === 'economy.html') {
    renderMarketWide(pageData.marketWide);
    renderTierGrid(pageData.tiers);
    renderMapping(pageData.mapping);
    renderSections(pageData.sections);
  }

})();
