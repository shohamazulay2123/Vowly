/* ════════════════════════════════════════════════════════════════════════
   Vowly 2.0 — client interactions
   - Discover: swipe deck, vendor sheet, liked strip, chip counts
   - Plan: progress rings, accordion, search + status filters
   - Onboarding: 2-step wizard
   - Profile: language auto-submit, distance slider
   ════════════════════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  // Auto-hide flash messages
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  initSwipeDeck();
  initDiscoverLiveSearch();
  initPlan();
  initWizard();
  initSettings();
  initVenueDialog();
});

function i18n(key, fallback) {
  return (window.VOWLY_I18N && window.VOWLY_I18N[key]) || fallback;
}

/* ════════════════════════════════════════════════════════════════════════
   Swipe deck (Discover)
   ════════════════════════════════════════════════════════════════════════ */
function initSwipeDeck() {
  const stage = document.getElementById("swipe-stage");
  const deck  = document.getElementById("swipe-deck");
  if (!stage) return;
  if (!deck) {
    initVendorSheet();
    return;
  }

  const categoryId = stage.dataset.categoryId;
  const sort       = stage.dataset.sort || "recommended";
  const skipBtn    = document.getElementById("btn-skip");
  const likeBtn    = document.getElementById("btn-like");
  const infoBtn    = document.getElementById("btn-info");
  const emptyEl    = document.getElementById("swipe-empty");
  const actionsEl  = document.getElementById("swipe-actions");

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
    const empty = cards.length === 0;
    if (empty) {
      if (emptyEl) emptyEl.hidden = false;
      if (actionsEl) actionsEl.style.display = "none";
      deck.style.display = "none";
      const hint = document.querySelector(".swipe-hint");
      if (hint) hint.style.display = "none";
    }
    if (skipBtn) skipBtn.disabled = empty;
    if (likeBtn) likeBtn.disabled = empty;
    if (infoBtn) infoBtn.disabled = empty;
  }

  function postAction(vendorId, action) {
    const url = `/swipe/${categoryId}/${vendorId}/${action}?sort=${encodeURIComponent(sort)}`;
    return fetch(url, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }).catch(() => { /* network errors: still let UI advance */ });
  }

  function decrementChipCount() {
    const count = document.querySelector(".chip.is-active .chip-count");
    if (!count) return;
    const n = Math.max(0, parseInt(count.textContent || "0", 10) - 1);
    count.textContent = String(n);
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
    decrementChipCount();
    if (action === "Like") addToLikedStrip(card);

    setTimeout(() => {
      card.remove();
      refreshDepths();
    }, 420);
  }

  // ---------- Liked strip + nav badges ----------
  function bumpBadges() {
    // desktop topnav badge
    const navLink = document.querySelector('.topnav-link[href*="favorites"], .topnav-link[href*="liked"]');
    let navBadge = navLink ? navLink.querySelector(".nav-badge") : null;
    if (navLink && !navBadge) {
      navBadge = document.createElement("span");
      navBadge.className = "nav-badge";
      navBadge.textContent = "0";
      navLink.appendChild(navBadge);
    }
    if (navBadge) navBadge.textContent = String(parseInt(navBadge.textContent || "0", 10) + 1);

    // mobile tabbar badge
    const tabIcon = document.querySelector('.tabbar .tab[href*="favorites"] .tab-ico, .tabbar .tab[href*="liked"] .tab-ico');
    let tabBadge = tabIcon ? tabIcon.querySelector(".tab-badge") : null;
    if (tabIcon && !tabBadge) {
      tabBadge = document.createElement("span");
      tabBadge.className = "tab-badge";
      tabBadge.textContent = "0";
      tabIcon.appendChild(tabBadge);
    }
    if (tabBadge) tabBadge.textContent = String(parseInt(tabBadge.textContent || "0", 10) + 1);
  }

  function addToLikedStrip(card) {
    const strip  = document.getElementById("liked-strip-swipe");
    const scroll = document.getElementById("liked-scroll-swipe");
    const countEl = document.getElementById("liked-swipe-count");
    bumpBadges();
    if (!strip || !scroll) return;

    const name    = card.dataset.vendorName  || "Vendor";
    const city    = card.dataset.vendorCity  || "";
    const rating  = card.dataset.vendorRating || "";
    const photo   = card.dataset.vendorPhoto || "";
    const url     = card.dataset.vendorUrl   || "#";
    const vid     = card.dataset.vendorId    || "";

    if (scroll.querySelector(`[data-vendor-id="${vid}"]`)) return;

    const starSvg = rating
      ? `<span class="liked-card-rating"><svg width="12" height="12" viewBox="0 0 24 24" fill="#B58A33" aria-hidden="true"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>${rating}</span>`
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

    if (countEl) countEl.textContent = String(parseInt(countEl.textContent || "0", 10) + 1);
  }

  // ---------- Drag handling ----------
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
        card.style.transition = `transform .35s ${EASE}`;
        card.style.transform  = "";
      }
    }

    card.addEventListener("pointerdown", onPointerDown);
    card.addEventListener("pointermove", onPointerMove);
    card.addEventListener("pointerup",   onPointerUp);
    card.addEventListener("pointercancel", onPointerUp);
  }

  window.commitSwipeCard = commit;
  deck.querySelectorAll(".swipe-card").forEach(bindCard);
  if (skipBtn) skipBtn.addEventListener("click", () => commit(topCard(), "left"));
  if (likeBtn) likeBtn.addEventListener("click", () => commit(topCard(), "right"));

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
    if (e.key === "ArrowLeft")  commit(topCard(), "left");
    if (e.key === "ArrowRight") commit(topCard(), "right");
    if (e.key === "Escape" && window.closeSheet) window.closeSheet();
  });

  refreshDepths();
  initVendorSheet();
}

/* ── Vendor profile sheet — opens on tap of the top card or ⓘ ─────────── */
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

  const sheetLabels = document.documentElement.lang === "he"
    ? {
        price: "טווח מחיר",
        rating: "דירוג",
        reviews: "ביקורות",
        city: "עיר",
        address: "כתובת",
        phone: "טלפון",
        email: "אימייל",
        website: "אתר",
        instagram: "Instagram",
        noDescription: "אין עדיין תיאור מפורט לספק הזה."
      }
    : {
        price: "Price range",
        rating: "Rating",
        reviews: "Reviews",
        city: "City",
        address: "Address",
        phone: "Phone",
        email: "Email",
        website: "Website",
        instagram: "Instagram",
        noDescription: "No detailed description is available for this vendor yet."
      };

  function addDetail(parent, label, value, options = {}) {
    if (!value) return;
    const item = document.createElement(options.href ? "a" : "div");
    item.className = "vsheet-detail-item";
    if (options.href) {
      item.href = options.href;
      if (options.external) {
        item.target = "_blank";
        item.rel = "noopener noreferrer";
      }
    }
    if (options.icon) {
      const iconEl = document.createElement("span");
      iconEl.className = "vsheet-detail-icon";
      iconEl.setAttribute("aria-hidden", "true");
      iconEl.textContent = options.icon;
      item.appendChild(iconEl);
    }
    const labelEl = document.createElement("span");
    labelEl.className = "vsheet-detail-label";
    labelEl.textContent = label;
    const valueEl = document.createElement("strong");
    valueEl.className = "vsheet-detail-value";
    valueEl.textContent = value;
    item.append(labelEl, valueEl);
    parent.appendChild(item);
  }

  function openSheet(card) {
    currentCard = card;
    const d = card.dataset;

    photo.style.backgroundImage = d.vendorPhoto ? `url('${d.vendorPhoto}')` : "";
    badge.textContent  = d.vendorCat  || "";
    name.textContent   = d.vendorName || "";
    city.textContent   = d.vendorCity ? "📍 " + d.vendorCity : "";
    desc.textContent   = d.vendorDesc || sheetLabels.noDescription;
    link.href          = d.vendorUrl  || "#";

    if (d.vendorRating) {
      rating.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="#B58A33" aria-hidden="true"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg> ${d.vendorRating}`;
    } else {
      rating.textContent = "";
    }

    details.innerHTML = "";
    const mapQuery = [d.vendorAddress, d.vendorCity].filter(Boolean).join(", ");
    addDetail(details, sheetLabels.price, d.vendorPrice, { icon: "₪" });
    addDetail(details, sheetLabels.rating, d.vendorRating ? `${d.vendorRating} / 5` : "", { icon: "★" });
    addDetail(details, sheetLabels.reviews, d.vendorReviewCount ? d.vendorReviewCount : "0", { icon: "◎" });
    addDetail(details, sheetLabels.city, d.vendorCity, { icon: "⌖" });
    addDetail(details, sheetLabels.address, d.vendorAddress, {
      icon: "⌖",
      href: mapQuery ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}` : "",
      external: true
    });
    addDetail(details, sheetLabels.phone, d.vendorPhone, { icon: "☎", href: d.vendorPhone ? `tel:${d.vendorPhone}` : "" });
    addDetail(details, sheetLabels.email, d.vendorEmail, { icon: "@", href: d.vendorEmail ? `mailto:${d.vendorEmail}` : "" });
    addDetail(details, sheetLabels.website, d.vendorWebsite, { icon: "↗", href: d.vendorWebsite, external: true });
    addDetail(details, sheetLabels.instagram, d.vendorInstagram, { icon: "◎", href: d.vendorInstagram, external: true });

    backdrop.hidden = false;
    sheet.hidden    = false;
    requestAnimationFrame(() => {
      backdrop.classList.add("is-open");
      sheet.classList.add("is-open");
    });
    document.body.style.overflow = "hidden";
    sheet.scrollTop = 0;
  }
  window.openVendorSheetCard = openSheet;

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
  window.closeSheet = closeSheet;

  backdrop.addEventListener("click", closeSheet);
  sheet.addEventListener("click", (e) => e.stopPropagation());

  const infoBtn = document.getElementById("btn-info");
  if (infoBtn) {
    infoBtn.addEventListener("click", () => {
      const deckEl = document.getElementById("swipe-deck");
      if (!deckEl) return;
      const card = deckEl.querySelector(".swipe-card.is-top:not(.is-leaving)");
      if (card) openSheet(card);
    });
  }

  if (skipBtn2) skipBtn2.addEventListener("click", () => {
    const card = currentCard;
    closeSheet();
    setTimeout(() => window.commitSwipeCard && window.commitSwipeCard(card, "left"), 80);
  });
  if (likeBtn2) likeBtn2.addEventListener("click", () => {
    const card = currentCard;
    closeSheet();
    setTimeout(() => window.commitSwipeCard && window.commitSwipeCard(card, "right"), 80);
  });

  // Tap detection — click events are suppressed after a real drag
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

/* ════════════════════════════════════════════════════════════════════════
   Discover live Google supplier search
   ════════════════════════════════════════════════════════════════════════ */
function initDiscoverLiveSearch() {
  const form = document.getElementById("disc-search-form");
  const input = form ? form.querySelector('input[type="search"]') : null;
  const resultsEl = document.getElementById("disc-live-results");
  const stage = document.getElementById("swipe-stage");
  if (!form || !input || !resultsEl || !stage) return;

  const categoryId = form.dataset.categoryId || stage.dataset.categoryId || "";
  let activeController = null;
  let debounceId = null;
  let latestQuery = "";

  const labels = document.documentElement.lang === "he"
    ? {
        searching: "מחפשים ב-Google...",
        noResults: "לא נמצאו ספקים מתאימים",
        unavailable: "חיפוש Google לא זמין כרגע",
        select: "בחירה"
      }
    : {
        searching: "Searching Google...",
        noResults: "No matching suppliers found",
        unavailable: "Google search is unavailable",
        select: "Select"
      };

  function setExpanded(on) {
    input.setAttribute("aria-expanded", on ? "true" : "false");
    resultsEl.hidden = !on;
  }

  function clearResults() {
    resultsEl.innerHTML = "";
    setExpanded(false);
  }

  function renderStatus(text) {
    resultsEl.innerHTML = "";
    const item = document.createElement("div");
    item.className = "disc-live-status";
    item.textContent = text;
    resultsEl.appendChild(item);
    setExpanded(true);
  }

  function createVendorCard(vendor) {
    const card = document.createElement("article");
    card.className = "swipe-card live-search-card is-top";
    card.dataset.vendorId = vendor.vendorId || "";
    card.dataset.vendorName = vendor.name || "";
    card.dataset.vendorCity = vendor.city || "";
    card.dataset.vendorRating = vendor.rating || "";
    card.dataset.vendorPhoto = vendor.photo || "";
    card.dataset.vendorUrl = vendor.url || "#";
    card.dataset.vendorDesc = vendor.desc || "";
    card.dataset.vendorPrice = vendor.price || "";
    card.dataset.vendorAddress = vendor.address || "";
    card.dataset.vendorPhone = vendor.phone || "";
    card.dataset.vendorEmail = vendor.email || "";
    card.dataset.vendorWebsite = vendor.website || "";
    card.dataset.vendorInstagram = vendor.instagram || "";
    card.dataset.vendorCat = vendor.categoryName || "";
    card.dataset.vendorReviewCount = vendor.reviewCount || "0";
    card.style.setProperty("--depth", "0");
    return card;
  }

  async function selectResult(placeId) {
    renderStatus(labels.searching);
    try {
      const response = await fetch("/api/google-vendors/select", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ place_id: placeId, category_id: categoryId })
      });
      if (!response.ok) throw new Error("select failed");
      const payload = await response.json();
      clearResults();
      input.blur();
      if (payload.vendor && window.openVendorSheetCard) {
        window.openVendorSheetCard(createVendorCard(payload.vendor));
      }
    } catch (_) {
      renderStatus(labels.unavailable);
    }
  }

  function renderResults(results) {
    resultsEl.innerHTML = "";
    if (!results.length) {
      renderStatus(labels.noResults);
      return;
    }

    results.forEach((result) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "disc-live-item";
      button.setAttribute("role", "option");

      const thumb = document.createElement("span");
      thumb.className = "disc-live-thumb";
      if (result.photo) thumb.style.backgroundImage = `url('${result.photo}')`;

      const body = document.createElement("span");
      body.className = "disc-live-body";

      const name = document.createElement("strong");
      name.textContent = result.name || "";

      const meta = document.createElement("span");
      meta.className = "disc-live-meta";
      meta.textContent = [result.category, result.city, result.rating ? `★ ${result.rating}` : ""]
        .filter(Boolean)
        .join(" · ");

      const address = document.createElement("span");
      address.className = "disc-live-address";
      address.textContent = result.address || "";

      const cta = document.createElement("span");
      cta.className = "disc-live-cta";
      cta.textContent = labels.select;

      body.append(name, meta, address);
      button.append(thumb, body, cta);
      button.addEventListener("mousedown", (event) => event.preventDefault());
      button.addEventListener("click", () => selectResult(result.placeId));
      resultsEl.appendChild(button);
    });
    setExpanded(true);
  }

  async function runSearch(query) {
    latestQuery = query;
    if (activeController) activeController.abort();
    activeController = new AbortController();
    renderStatus(labels.searching);

    try {
      const params = new URLSearchParams({ q: query, category_id: categoryId });
      const response = await fetch(`/api/google-vendors/search?${params}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: activeController.signal
      });
      if (!response.ok) throw new Error("search failed");
      const payload = await response.json();
      if (query !== latestQuery) return;
      renderResults(payload.results || []);
    } catch (error) {
      if (error.name === "AbortError") return;
      renderStatus(labels.unavailable);
    }
  }

  input.addEventListener("input", () => {
    const query = input.value.trim();
    clearTimeout(debounceId);
    if (query.length < 2) {
      clearResults();
      return;
    }
    debounceId = setTimeout(() => runSearch(query), 260);
  });

  input.addEventListener("focus", () => {
    if (resultsEl.children.length) setExpanded(true);
  });

  form.addEventListener("submit", (event) => {
    if (!input.value.trim()) return;
    event.preventDefault();
    runSearch(input.value.trim());
  });

  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) clearResults();
  });
}

/* ════════════════════════════════════════════════════════════════════════
   Plan page: ring, accordion, filters
   ════════════════════════════════════════════════════════════════════════ */
function initPlan() {
  const ringWrap = document.querySelector(".ring-wrap");
  if (!ringWrap) return; // not on plan page

  const RING_CIRC = 326.7; // 2 * pi * 52

  // ---------- Hero ring animation ----------
  const ringFill = ringWrap.querySelector(".ring-fill");
  const ringNumEl = document.getElementById("ring-num");
  const ringCapEl = document.getElementById("ring-cap");

  function setRing(pct, booked, total) {
    const off = RING_CIRC - (RING_CIRC * pct / 100);
    ringFill.style.strokeDashoffset = String(off);
    const start = parseInt(ringNumEl.textContent, 10) || 0;
    const dur = 900, t0 = performance.now();
    function step(t) {
      const k = Math.min((t - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - k, 3);
      ringNumEl.textContent = Math.round(start + (pct - start) * eased);
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
    if (ringCapEl && typeof booked === "number" && typeof total === "number") {
      ringCapEl.textContent = i18n("bookedRatio", "{booked} / {total} booked")
        .replace("{booked}", booked)
        .replace("{total}", total);
    }
  }

  requestAnimationFrame(() => {
    setRing(parseInt(ringWrap.dataset.pct, 10) || 0);
  });

  // ---------- Accordion (persisted) ----------
  const STORAGE_KEY = "vowly:acc";
  let openMap = {};
  try { openMap = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch (_) { openMap = {}; }

  document.querySelectorAll(".acc-section").forEach((sec) => {
    const cat = sec.dataset.category;
    if (cat in openMap) {
      sec.classList.toggle("is-open", !!openMap[cat]);
      const head = sec.querySelector(".acc-head");
      if (head) head.setAttribute("aria-expanded", openMap[cat] ? "true" : "false");
    }
    const head = sec.querySelector(".acc-head");
    if (!head) return;
    head.addEventListener("click", () => {
      const willOpen = !sec.classList.contains("is-open");
      sec.classList.toggle("is-open", willOpen);
      head.setAttribute("aria-expanded", willOpen ? "true" : "false");
      openMap[cat] = willOpen;
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(openMap)); } catch (_) {}
    });
  });

  // ---------- Filters (search + pills + KPI tiles) ----------
  const searchInput = document.getElementById("cmd-search-input");
  const pills       = document.querySelectorAll(".cmd-pills .pill");
  const kpiTiles    = document.querySelectorAll(".kpi-tile");
  const emptyMsg    = document.querySelector(".empty-msg");
  let activeStatus  = "all";
  let searchTerm    = "";

  function applyFilters() {
    const term = searchTerm.trim();
    let anyVisible = false;
    document.querySelectorAll(".supplier-card").forEach((card) => {
      const name  = card.dataset.name || "";
      const matchesText   = !term || name.includes(term);
      const matchesStatus = (activeStatus === "all") || (card.dataset.status === activeStatus);
      const show = matchesText && matchesStatus;
      card.hidden = !show;
      if (show) anyVisible = true;
    });
    document.querySelectorAll(".acc-section").forEach((sec) => {
      const visible = sec.querySelectorAll(".supplier-card:not([hidden])").length;
      sec.style.display = visible === 0 ? "none" : "";
      // auto-open sections while filtering so results are visible
      if (visible > 0 && (term || activeStatus !== "all")) sec.classList.add("is-open");
    });
    if (emptyMsg) emptyMsg.hidden = anyVisible;
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      searchTerm = searchInput.value.toLowerCase();
      applyFilters();
    });
  }

  function setActiveStatus(value, sourceEl) {
    activeStatus = value;
    pills.forEach((p) => p.classList.toggle("pill-active", p.dataset.status === value));
    kpiTiles.forEach((t) => t.classList.toggle("is-active", t.dataset.kpiFilter === value));
    applyFilters();
  }

  pills.forEach((p) => p.addEventListener("click", () => setActiveStatus(p.dataset.status, p)));
  kpiTiles.forEach((t) => t.addEventListener("click", () => {
    const v = t.dataset.kpiFilter;
    if (activeStatus === v) setActiveStatus("all");
    else                    setActiveStatus(v, t);
  }));
}

/* ════════════════════════════════════════════════════════════════════════
   Onboarding wizard
   ════════════════════════════════════════════════════════════════════════ */
function initWizard() {
  const wizard = document.getElementById("wizard");
  if (!wizard) return;

  const steps = Array.from(wizard.querySelectorAll(".wizard-step"));
  const label = document.getElementById("wizard-step-label");
  const total = steps.length;

  function goTo(n) {
    wizard.dataset.step = String(n);
    steps.forEach((s) => {
      const active = s.dataset.step === String(n);
      s.classList.toggle("is-active", active);
      s.hidden = !active;
    });
    if (label) {
      const tpl = label.dataset.template || "Step {step} of {total}";
      label.textContent = tpl.replace("{step}", n).replace("{total}", total);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  wizard.querySelectorAll("[data-wizard-next]").forEach((btn) =>
    btn.addEventListener("click", () => goTo(Math.min(total, parseInt(wizard.dataset.step, 10) + 1))));
  wizard.querySelectorAll("[data-wizard-back]").forEach((btn) =>
    btn.addEventListener("click", () => goTo(Math.max(1, parseInt(wizard.dataset.step, 10) - 1))));

  // Enter inside step-1 fields advances instead of submitting
  wizard.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const inStep1 = e.target.closest('.wizard-step[data-step="1"]');
    if (inStep1 && !/textarea/i.test(e.target.tagName)) {
      e.preventDefault();
      goTo(2);
    }
  });
}

/* ════════════════════════════════════════════════════════════════════════
   Profile / settings
   ════════════════════════════════════════════════════════════════════════ */
function initSettings() {
  const form = document.querySelector(".settings-form");
  if (!form) return;

  form.querySelectorAll("[data-autosubmit-settings]").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) form.requestSubmit();
    });
  });

  const slider = form.querySelector("[data-distance-slider]");
  const output = document.getElementById("distance-output");
  if (!slider || !output) return;

  const template = slider.dataset.distanceTemplate || "{value} km";
  const sync = () => {
    output.textContent = template.replace("{value}", slider.value);
  };
  slider.addEventListener("input", sync);
  sync();
}

/* ════════════════════════════════════════════════════════════════════════
   Venue selection dialog
   ════════════════════════════════════════════════════════════════════════ */
function initVenueDialog() {
  const dlg    = document.getElementById("venue-select-dialog");
  const frm    = document.getElementById("venue-select-form");
  const nameEl = document.getElementById("venue-dialog-name");
  const cancelBtn = document.getElementById("venue-dialog-cancel");
  if (!dlg) return;

  document.querySelectorAll("[data-venue-select]").forEach((btn) => {
    btn.addEventListener("click", () => {
      frm.action = btn.dataset.venueSelect;
      if (nameEl) nameEl.textContent = btn.dataset.venueName || "";
      frm.querySelector("[name=price_per_meal]").value = "";
      frm.querySelector("[name=guest_count]").value = "";
      dlg.showModal();
    });
  });

  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => dlg.close());
  }

  dlg.addEventListener("click", (e) => {
    if (e.target === dlg) dlg.close();
  });
}
