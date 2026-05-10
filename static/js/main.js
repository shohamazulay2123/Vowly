// Vowly minor enhancements
document.addEventListener("DOMContentLoaded", () => {
  // Auto-hide flash messages after 4s
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  initSwipeDeck();
  initChecklist();
  initSupplierNotesForm();
});

/* ---------------------------------------------------------------------------
 * Swipe deck
 *
 * - Stacks vendor cards.
 * - Top card is draggable (pointer events) + supports keyboard arrows + buttons.
 * - On commit (drag distance > threshold or button), the card animates off
 *   screen with the same cubic-bezier easing as the auth tabs, then is removed
 *   from the DOM. The next card is promoted with a subtle scale/opacity tween.
 * - Like/skip is POSTed in the background; no full-page reloads.
 * ------------------------------------------------------------------------- */
function initSwipeDeck() {
  const stage = document.getElementById("swipe-stage");
  const deck  = document.getElementById("swipe-deck");
  if (!stage || !deck) return;

  const categoryId = stage.dataset.categoryId;
  const sort       = stage.dataset.sort || "recommended";
  const skipBtn    = document.getElementById("btn-skip");
  const likeBtn    = document.getElementById("btn-like");
  const emptyEl    = document.getElementById("swipe-empty");

  const SWIPE_THRESHOLD = 110;     // px drag distance required to commit
  const FLY_DISTANCE    = 800;     // px to fly off screen
  const EASE            = "cubic-bezier(.22,.61,.36,1)";

  function topCard() {
    return deck.querySelector(".swipe-card:not(.is-leaving)");
  }

  function refreshDepths() {
    const cards = deck.querySelectorAll(".swipe-card:not(.is-leaving)");
    cards.forEach((c, i) => {
      c.style.setProperty("--depth", String(i));
      c.classList.toggle("is-top", i === 0);
    });
    if (cards.length === 0 && emptyEl) {
      emptyEl.hidden = false;
      if (skipBtn) skipBtn.disabled = true;
      if (likeBtn) likeBtn.disabled = true;
    }
  }

  function postAction(vendorId, action) {
    const url = `/swipe/${categoryId}/${vendorId}/${action}?sort=${encodeURIComponent(sort)}`;
    return fetch(url, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }).catch(() => { /* network errors: still let UI advance */ });
  }

  function commit(card, direction) {
    if (!card || card.classList.contains("is-leaving")) return;
    card.classList.add("is-leaving");

    const vendorId = card.dataset.vendorId;
    const action   = direction === "right" ? "Like" : "Skip";
    const flyX     = direction === "right" ? FLY_DISTANCE : -FLY_DISTANCE;
    const rot      = direction === "right" ? 18 : -18;

    card.style.transition = `transform .42s ${EASE}, opacity .42s ${EASE}`;
    card.style.transform  = `translate(${flyX}px, -40px) rotate(${rot}deg)`;
    card.style.opacity    = "0";

    postAction(vendorId, action);

    // If liked, add to the in-page liked strip immediately
    if (action === "Like") {
      addToLikedStrip(card);
    }

    setTimeout(() => {
      card.remove();
      refreshDepths();
    }, 420);
  }

  // ---------- Liked strip (swipe page) ----------
  function addToLikedStrip(card) {
    const strip  = document.getElementById("liked-strip-swipe");
    const scroll = document.getElementById("liked-scroll-swipe");
    const countEl = document.getElementById("liked-swipe-count");
    const navBadge = document.querySelector(".nav-badge");
    if (!strip || !scroll) return;

    const name    = card.dataset.vendorName  || "Vendor";
    const city    = card.dataset.vendorCity  || "";
    const rating  = card.dataset.vendorRating || "";
    const photo   = card.dataset.vendorPhoto || "";
    const url     = card.dataset.vendorUrl   || "#";
    const vid     = card.dataset.vendorId    || "";

    // Avoid duplicates
    if (scroll.querySelector(`[data-vendor-id="${vid}"]`)) return;

    const starSvg = rating
      ? `<span class="liked-card-rating"><svg width="12" height="12" viewBox="0 0 24 24" fill="var(--gold)" aria-hidden="true"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>${rating}</span>`
      : "";
    const cityHtml = city ? `<span class="liked-card-city muted small">${city}</span>` : "";

    const el = document.createElement("a");
    el.className = "liked-card liked-card-new";
    el.href = url;
    el.dataset.vendorId = vid;
    el.innerHTML = `
      <div class="liked-card-img" style="background-image:url('${photo}')"></div>
      <div class="liked-card-body">
        <span class="liked-card-name">${name}</span>
        ${cityHtml}
        ${starSvg}
      </div>`;

    scroll.prepend(el);
    strip.style.display = "";

    // Update count
    if (countEl) countEl.textContent = String(parseInt(countEl.textContent || "0", 10) + 1);

    // Update nav badge
    if (navBadge) {
      navBadge.textContent = String(parseInt(navBadge.textContent || "0", 10) + 1);
      navBadge.style.display = "";
    } else {
      const navLink = document.querySelector(".nav-liked-link");
      if (navLink) {
        const badge = document.createElement("span");
        badge.className = "nav-badge";
        badge.textContent = "1";
        navLink.appendChild(badge);
      }
    }
  }

  function bindCard(card) {
    let startX = 0, startY = 0, currentX = 0, currentY = 0;
    let dragging = false, pointerId = null;

    function onPointerDown(e) {
      if (!card.classList.contains("is-top")) return;
      dragging  = true;
      pointerId = e.pointerId;
      startX    = e.clientX;
      startY    = e.clientY;
      currentX  = 0;
      currentY  = 0;
      card.setPointerCapture(pointerId);
      card.style.transition = "none";
      card.classList.add("is-dragging");
    }

    function onPointerMove(e) {
      if (!dragging) return;
      currentX = e.clientX - startX;
      currentY = e.clientY - startY;
      const rot = currentX / 18; // gentle tilt
      card.style.transform = `translate(${currentX}px, ${currentY}px) rotate(${rot}deg)`;

      // Show like/skip overlay tags as user drags
      const intent = currentX > 30 ? 1 : currentX < -30 ? -1 : 0;
      card.classList.toggle("intent-like", intent === 1);
      card.classList.toggle("intent-skip", intent === -1);
      const opacity = Math.min(Math.abs(currentX) / SWIPE_THRESHOLD, 1);
      card.style.setProperty("--intent-opacity", String(opacity));
    }

    function onPointerUp() {
      if (!dragging) return;
      dragging = false;
      try { card.releasePointerCapture(pointerId); } catch (_) {}
      card.classList.remove("is-dragging");
      card.style.setProperty("--intent-opacity", "0");
      card.classList.remove("intent-like", "intent-skip");

      if (currentX > SWIPE_THRESHOLD) {
        commit(card, "right");
      } else if (currentX < -SWIPE_THRESHOLD) {
        commit(card, "left");
      } else {
        // Snap back smoothly with the auth-tab easing
        card.style.transition = `transform .35s ${EASE}`;
        card.style.transform  = "";
      }
    }

    card.addEventListener("pointerdown", onPointerDown);
    card.addEventListener("pointermove", onPointerMove);
    card.addEventListener("pointerup",   onPointerUp);
    card.addEventListener("pointercancel", onPointerUp);
  }

  // Wire each card and buttons
  deck.querySelectorAll(".swipe-card").forEach(bindCard);
  if (skipBtn) skipBtn.addEventListener("click", () => commit(topCard(), "left"));
  if (likeBtn) likeBtn.addEventListener("click", () => commit(topCard(), "right"));

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
    if (e.key === "ArrowLeft")  commit(topCard(), "left");
    if (e.key === "ArrowRight") commit(topCard(), "right");
    if (e.key === "Escape") closeSheet();
  });

  refreshDepths();
  initVendorSheet();
}

/* ---------------------------------------------------------------------------
 * Vendor profile sheet — opens on tap (not drag) of a swipe card
 * ------------------------------------------------------------------------- */
function initVendorSheet() {
  const backdrop  = document.getElementById("vsheet-backdrop");
  const sheet     = document.getElementById("vsheet");
  if (!backdrop || !sheet) return;

  const photo     = document.getElementById("vsheet-photo");
  const badge     = document.getElementById("vsheet-badge");
  const rating    = document.getElementById("vsheet-rating");
  const name      = document.getElementById("vsheet-name");
  const city      = document.getElementById("vsheet-city");
  const desc      = document.getElementById("vsheet-desc");
  const details   = document.getElementById("vsheet-details");
  const link      = document.getElementById("vsheet-profile-link");
  const skipBtn2  = document.getElementById("vsheet-skip");
  const likeBtn2  = document.getElementById("vsheet-like");

  let currentCard = null;

  function openSheet(card) {
    currentCard = card;
    const d = card.dataset;

    photo.style.backgroundImage = d.vendorPhoto ? `url('${d.vendorPhoto}')` : "";
    badge.textContent  = d.vendorCat  || "";
    name.textContent   = d.vendorName || "";
    city.textContent   = d.vendorCity ? "📍 " + d.vendorCity : "";
    desc.textContent   = d.vendorDesc || "";
    link.href          = d.vendorUrl  || "#";

    // Rating
    if (d.vendorRating) {
      rating.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="var(--gold)" aria-hidden="true"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg> ${d.vendorRating}`;
    } else {
      rating.textContent = "";
    }

    // Detail chips
    details.innerHTML = "";
    if (d.vendorPrice) {
      const ch = document.createElement("span");
      ch.className = "vsheet-detail-chip";
      ch.textContent = d.vendorPrice;
      details.appendChild(ch);
    }
    if (d.vendorPhone) {
      const ch = document.createElement("a");
      ch.className = "vsheet-detail-chip";
      ch.href = "tel:" + d.vendorPhone;
      ch.textContent = "📞 " + d.vendorPhone;
      details.appendChild(ch);
    }
    if (d.vendorWebsite) {
      const ch = document.createElement("a");
      ch.className = "vsheet-detail-chip";
      ch.href = d.vendorWebsite;
      ch.target = "_blank";
      ch.rel = "noopener noreferrer";
      ch.textContent = "🌐 Website";
      details.appendChild(ch);
    }

    backdrop.hidden = false;
    sheet.hidden    = false;
    requestAnimationFrame(() => {
      backdrop.classList.add("is-open");
      sheet.classList.add("is-open");
    });
    document.body.style.overflow = "hidden";
    sheet.scrollTop = 0;
  }

  function closeSheet() {
    backdrop.classList.remove("is-open");
    sheet.classList.remove("is-open");
    document.body.style.overflow = "";
    sheet.addEventListener("transitionend", () => {
      sheet.hidden    = true;
      backdrop.hidden = true;
      currentCard = null;
    }, { once: true });
  }
  // expose so keyboard Escape works
  window.closeSheet = closeSheet;

  backdrop.addEventListener("click", closeSheet);
  sheet.addEventListener("click", (e) => e.stopPropagation());

  if (skipBtn2) skipBtn2.addEventListener("click", () => {
    const card = currentCard;
    closeSheet();
    setTimeout(() => commit(card, "left"), 80);
  });
  if (likeBtn2) likeBtn2.addEventListener("click", () => {
    const card = currentCard;
    closeSheet();
    setTimeout(() => commit(card, "right"), 80);
  });

  // Tap detection — use click event (browser suppresses it after a real drag)
  const deck = document.getElementById("swipe-deck");
  if (!deck) return;
  deck.querySelectorAll(".swipe-card").forEach((card) => {
    card.addEventListener("click", () => {
      if (!card.classList.contains("is-top")) return;
      if (card.classList.contains("is-leaving")) return;
      openSheet(card);
    });
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openSheet(card); }
    });
  });
}

/* ---------------------------------------------------------------------------
 * Checklist page
 *
 * Behaviors:
 *  - Animate the hero progress ring on load.
 *  - Accordion open/close per category section, persisted to localStorage.
 *  - Sticky search filter (supplier name).
 *  - Status pills + KPI tiles act as filters.
 *
 * Each supplier card is now a plain link to its swipe page; status is
 * derived server-side from real activity (swipes + booked vendors), so the
 * client only needs to read it from data-status to drive filters/KPIs.
 * ------------------------------------------------------------------------- */
function initChecklist() {
  const ringWrap = document.querySelector('.ring-wrap');
  if (!ringWrap) return; // not on checklist page

  const RING_CIRC = 326.7; // 2 * pi * 52

  // ---------- Hero ring animation ----------
  const ringFill = ringWrap.querySelector('.ring-fill');
  const ringNumEl = document.getElementById('ring-num');
  const ringCapEl = document.getElementById('ring-cap');

  function setRing(pct, booked, total) {
    const off = RING_CIRC - (RING_CIRC * pct / 100);
    ringFill.style.strokeDashoffset = String(off);
    // animate the number
    const start = parseInt(ringNumEl.textContent, 10) || 0;
    const dur = 900, t0 = performance.now();
    function step(t) {
      const k = Math.min((t - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - k, 3);
      ringNumEl.textContent = Math.round(start + (pct - start) * eased);
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
    if (ringCapEl && typeof booked === 'number' && typeof total === 'number') {
      ringCapEl.textContent = `${booked} / ${total} booked`;
    }
  }

  // initial reveal
  requestAnimationFrame(() => {
    setRing(parseInt(ringWrap.dataset.pct, 10) || 0);
  });

  // ---------- KPI tiles ----------
  const kpiBooked   = document.getElementById('kpi-booked');
  const kpiProgress = document.getElementById('kpi-progress');
  const kpiTodo     = document.getElementById('kpi-todo');

  function recomputeKpis() {
    const cards = Array.from(document.querySelectorAll('.supplier-card'));
    let booked = 0, prog = 0, todo = 0, total = 0;
    cards.forEach((c) => {
      const st = c.dataset.status;
      if (st === 'Not relevant') return;
      total++;
      if      (st === 'Booked')      booked++;
      else if (st === 'In progress') prog++;
      else                            todo++;
    });
    if (kpiBooked)   kpiBooked.textContent   = booked;
    if (kpiProgress) kpiProgress.textContent = prog;
    if (kpiTodo)     kpiTodo.textContent     = todo;
    const pct = total ? Math.round((booked / total) * 100) : 0;
    setRing(pct, booked, total);
    document.querySelectorAll('.acc-section').forEach(updateMiniRing);
  }

  function updateMiniRing(section) {
    const cards = section.querySelectorAll('.supplier-card');
    let total = 0, booked = 0, prog = 0;
    cards.forEach((c) => {
      const st = c.dataset.status;
      if (st === 'Not relevant') return;
      total++;
      if (st === 'Booked') booked++;
      else if (st === 'In progress') prog++;
    });
    const pct = total ? Math.round((booked / total) * 100) : 0;
    const fill = section.querySelector('.mr-fill');
    const num  = section.querySelector('.mr-num');
    const meta = section.querySelector('.acc-meta');
    if (fill) fill.style.strokeDashoffset = String(94.2 - (94.2 * pct / 100));
    if (num)  num.textContent = pct + '%';
    if (meta) meta.textContent = `${booked}/${total} booked Â· ${prog} in progress`;
  }

  // ---------- Accordion ----------
  const STORAGE_KEY = 'vowly:acc';
  let openMap = {};
  try { openMap = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch (_) { openMap = {}; }

  document.querySelectorAll('.acc-section').forEach((sec) => {
    const cat = sec.dataset.category;
    if (cat in openMap) {
      sec.classList.toggle('is-open', !!openMap[cat]);
      const head = sec.querySelector('.acc-head');
      if (head) head.setAttribute('aria-expanded', openMap[cat] ? 'true' : 'false');
    }
    const head = sec.querySelector('.acc-head');
    if (!head) return;
    head.addEventListener('click', () => {
      const willOpen = !sec.classList.contains('is-open');
      sec.classList.toggle('is-open', willOpen);
      head.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      openMap[cat] = willOpen;
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(openMap)); } catch (_) {}
    });
  });

  // ---------- Filters (search + pills + KPI tiles) ----------
  const searchInput = document.getElementById('cmd-search-input');
  const pills       = document.querySelectorAll('.cmd-pills .pill');
  const kpiTiles    = document.querySelectorAll('.kpi-tile');
  const emptyMsg    = document.querySelector('.empty-msg');
  let activeStatus  = 'all';
  let searchTerm    = '';

  function applyFilters() {
    const term = searchTerm.trim();
    let anyVisible = false;
    document.querySelectorAll('.supplier-card').forEach((card) => {
      const name  = card.dataset.name || '';
      const matchesText   = !term || name.includes(term);
      const matchesStatus = (activeStatus === 'all') || (card.dataset.status === activeStatus);
      const show = matchesText && matchesStatus;
      card.hidden = !show;
      if (show) anyVisible = true;
    });
    document.querySelectorAll('.acc-section').forEach((sec) => {
      const visible = sec.querySelectorAll('.supplier-card:not([hidden])').length;
      sec.style.display = visible === 0 ? 'none' : '';
    });
    if (emptyMsg) emptyMsg.hidden = anyVisible;
  }

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      searchTerm = searchInput.value.toLowerCase();
      applyFilters();
    });
  }

  function setActiveStatus(value, sourceEl) {
    activeStatus = value;
    pills.forEach((p) => p.classList.toggle('pill-active', p.dataset.status === value));
    kpiTiles.forEach((t) => t.classList.toggle('is-active', t.dataset.kpiFilter === value));
    if (sourceEl && sourceEl.classList.contains('kpi-tile')) {
      pills.forEach((p) => p.classList.toggle('pill-active', p.dataset.status === value));
    }
    applyFilters();
  }

  pills.forEach((p) => p.addEventListener('click', () => setActiveStatus(p.dataset.status, p)));
  kpiTiles.forEach((t) => t.addEventListener('click', () => {
    const v = t.dataset.kpiFilter;
    if (activeStatus === v) setActiveStatus('all');
    else                    setActiveStatus(v, t);
    document.getElementById('cmd-bar')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));

  // initial mini-ring sync
  document.querySelectorAll('.acc-section').forEach(updateMiniRing);
}

/* ---------------------------------------------------------------------------
 * Supplier notes/budget form on the swipe page (XHR save with toast).
 * ------------------------------------------------------------------------- */
function initSupplierNotesForm() {
  const form = document.querySelector('form.supplier-notes-form');
  if (!form) return;
  const toast = document.getElementById('toast');
  const CHECK_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5 10 17.5 19 7.5"/></svg>';
  let toastTimer = null;
  function showToast(msg, ok) {
    if (!toast) return;
    toast.innerHTML = (ok === false ? '' : CHECK_SVG) + '<span class="toast-text">' + msg + '</span>';
    toast.hidden = false;
    requestAnimationFrame(() => toast.classList.add('is-show'));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove('is-show');
      setTimeout(() => { toast.hidden = true; }, 350);
    }, 1600);
  }
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    fetch(form.action, {
      method: 'POST',
      body: fd,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    }).then((r) => r.ok ? showToast('Saved') : showToast('Couldn’t save', false))
      .catch(() => showToast('Couldn’t save', false));
  });
}
