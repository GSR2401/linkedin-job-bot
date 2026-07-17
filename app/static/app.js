(function () {
  "use strict";

  const ICONS = {
    chevron: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 6l4 4 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    trash: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 4.5h10M6.5 4.5V3a1 1 0 011-1h1a1 1 0 011 1v1.5M5 4.5l.5 9a1 1 0 001 1h3a1 1 0 001-1l.5-9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    externalLink: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M6 4H4a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1v-2M9 3h4v4M13 3L7 9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    checkmark: '<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 8.5l3 3 7-7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  const DATE_FILTERS = [
    { key: "all", label: "All time" },
    { key: "today", label: "Today" },
    { key: "yesterday", label: "Yesterday" },
    { key: "7d", label: "Last 7 days" },
    { key: "custom", label: "Custom range" },
  ];

  const state = {
    jobs: [],
    loading: true,
    sortDesc: true,
    dateFilter: "all",
    dateFilterOpen: false,
    customStart: "",
    customEnd: "",
    expandedId: null,
    swipeOpenId: null,
    removingIds: new Set(),
    toast: null, // { message, ids, removedJobs }
  };

  let removeTimer = null;
  let toastTimer = null;
  let groupIdsByKey = {};
  let currentSortedIds = [];

  function escapeHtml(str) {
    return String(str == null ? "" : str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }

  function getScoreTier(score) {
    return score >= 35 ? "high" : score >= 20 ? "mid" : "low";
  }

  function formatTime(d) {
    return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }

  function getFilteredJobs(day0) {
    const jobs = state.jobs;
    const f = state.dateFilter;
    if (!f || f === "all") return jobs;
    if (f === "today") return jobs.filter(function (j) { return sameDay(j.foundAtDate, day0); });
    if (f === "yesterday") {
      const y = new Date(day0);
      y.setDate(y.getDate() - 1);
      return jobs.filter(function (j) { return sameDay(j.foundAtDate, y); });
    }
    if (f === "7d") {
      const cutoff = new Date(day0);
      cutoff.setDate(cutoff.getDate() - 6);
      return jobs.filter(function (j) { return j.foundAtDate >= cutoff; });
    }
    if (f === "custom") {
      if (!state.customStart || !state.customEnd) return jobs;
      const s = new Date(state.customStart + "T00:00:00");
      const e = new Date(state.customEnd + "T23:59:59");
      return jobs.filter(function (j) { return j.foundAtDate >= s && j.foundAtDate <= e; });
    }
    return jobs;
  }

  // ── Fetch ──────────────────────────────────────────────────
  async function fetchJobs() {
    state.loading = true;
    render();
    const res = await fetch("/api/jobs");
    const data = await res.json();
    state.jobs = data.jobs.map(function (j) {
      return Object.assign({}, j, { foundAtDate: new Date(j.foundAt) });
    });
    state.loading = false;
    render();
  }

  // ── Delete / Undo ────────────────────────────────────────────
  function removeJobs(ids, message) {
    if (!ids.length) return;
    ids.forEach(function (id) { state.removingIds.add(id); });
    render();

    clearTimeout(removeTimer);
    removeTimer = setTimeout(function () {
      const removedJobs = state.jobs.filter(function (j) { return ids.includes(j.id); });
      state.jobs = state.jobs.filter(function (j) { return !ids.includes(j.id); });
      ids.forEach(function (id) {
        state.removingIds.delete(id);
        if (state.expandedId === id) state.expandedId = null;
        if (state.swipeOpenId === id) state.swipeOpenId = null;
      });

      fetch("/api/jobs/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: ids }),
      }).catch(function () {});

      showToast(message, ids, removedJobs);
    }, 220);
  }

  function deleteJob(jobId, opts) {
    opts = opts || {};
    const job = state.jobs.find(function (j) { return j.id === jobId; });
    if (!job) return;
    const message = opts.reason === "opened"
      ? 'Opened "' + job.title + '" and removed it'
      : 'Deleted "' + job.title + '"';
    removeJobs([jobId], message);
  }

  function handleOpenJob(jobId) {
    const job = state.jobs.find(function (j) { return j.id === jobId; });
    if (!job) return;
    window.open(job.linkedinUrl, "_blank", "noopener");
    deleteJob(jobId, { reason: "opened" });
  }

  function showToast(message, ids, removedJobs) {
    clearTimeout(toastTimer);
    state.toast = { message: message, ids: ids, removedJobs: removedJobs || [] };
    render();
    toastTimer = setTimeout(function () {
      state.toast = null;
      render();
    }, 5000);
  }

  async function undoToast() {
    if (!state.toast) return;
    const ids = state.toast.ids;
    const removedJobs = state.toast.removedJobs;
    clearTimeout(toastTimer);
    state.toast = null;
    render();

    try {
      const res = await fetch("/api/jobs/undo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: ids }),
      });
      const data = await res.json();
      if (data.restored && data.restored.length) {
        const restored = removedJobs.filter(function (j) { return data.restored.includes(j.id); });
        state.jobs = state.jobs.concat(restored);
      }
      if (data.tooLate && data.tooLate.length) {
        showToast("Too late — already removed", [], []);
        return;
      }
    } catch (err) {
      // network error — leave state as-is, sheet state unknown
    }
    render();
  }

  // ── Row rendering ────────────────────────────────────────────
  function buildRowHtml(job) {
    const tier = getScoreTier(job.matchScore);
    const isExpanded = state.expandedId === job.id;
    const isRemoving = state.removingIds.has(job.id);
    const isSwipeOpen = state.swipeOpenId === job.id;
    const rowTransform = isRemoving ? "translateX(-110%)" : (isSwipeOpen ? "translateX(-84px)" : "translateX(0)");
    const rowOpacity = isRemoving ? 0 : 1;
    const chevronRotate = isExpanded ? "rotate(180deg)" : "rotate(0deg)";

    const skillTokens = (job.matchedSkills || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
    const skillsHtml = skillTokens.map(function (s) {
      return '<span class="skill-pill">' + escapeHtml(s) + "</span>";
    }).join("");

    const fullDate = job.foundAtDate.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
      + " · " + formatTime(job.foundAtDate);

    const detailHtml = !isExpanded ? "" : (
      '<div class="row-detail">'
      + '<div class="detail-chips">'
      + '<span class="detail-chip">' + escapeHtml(job.experienceLevel) + "</span>"
      + '<span class="detail-chip">' + escapeHtml(job.roleCategory) + "</span>"
      + '<span class="detail-chip">Easy Apply: ' + (job.easyApply ? "Yes" : "No") + "</span>"
      + '<span class="detail-chip">' + fullDate + "</span>"
      + "</div>"
      + (skillTokens.length
        ? '<div class="skills-label">Matched skills</div><div class="skill-pills">' + skillsHtml + "</div>"
        : "")
      + '<div class="detail-actions">'
      + '<a class="btn-primary" href="' + escapeHtml(job.linkedinUrl) + '" target="_blank" rel="noopener" data-action="open-link">Open job ' + ICONS.externalLink + "</a>"
      + '<button class="btn-outline-danger" data-action="delete" type="button">Delete</button>'
      + "</div>"
      + "</div>"
    );

    return (
      '<div class="job-row-shell" data-job-id="' + escapeHtml(job.id) + '">'
      + '<div class="row-delete-backdrop"><button class="row-delete-icon-btn" data-action="delete" type="button">' + ICONS.trash + "</button></div>"
      + '<div class="job-row-content" data-row-content style="transform:' + rowTransform + ";opacity:" + rowOpacity + '">'
      + '<div class="job-row-main" data-action="open">'
      + '<div class="score-badge tier-' + tier + '">' + job.matchScore + "</div>"
      + '<div class="row-text-block">'
      + '<div class="row-title">' + escapeHtml(job.title) + "</div>"
      + '<div class="row-meta">' + escapeHtml(job.company) + " · " + escapeHtml(job.location) + "</div>"
      + "</div>"
      + '<div class="row-actions">'
      + '<button class="icon-btn delete-btn" data-action="delete" type="button">' + ICONS.trash + "</button>"
      + '<button class="icon-btn chevron-btn" data-action="toggle-expand" type="button"><span style="display:inline-flex;transform:' + chevronRotate + '">' + ICONS.chevron + "</span></button>"
      + "</div>"
      + "</div>"
      + detailHtml
      + "</div>"
      + "</div>"
    );
  }

  function attachRowTouchHandlers() {
    document.querySelectorAll(".job-row-content").forEach(function (rowEl) {
      const shell = rowEl.closest(".job-row-shell");
      const jobId = shell.dataset.jobId;
      let touchX0 = 0;
      let dragging = false;
      let lastDx = 0;

      rowEl.addEventListener("touchstart", function (e) {
        touchX0 = e.touches[0].clientX;
        lastDx = state.swipeOpenId === jobId ? -84 : 0;
        dragging = true;
      }, { passive: true });

      rowEl.addEventListener("touchmove", function (e) {
        if (!dragging) return;
        const base = state.swipeOpenId === jobId ? -84 : 0;
        let next = base + (e.touches[0].clientX - touchX0);
        if (next > 0) next = 0;
        if (next < -110) next = -110;
        lastDx = next;
        rowEl.style.transform = "translateX(" + next + "px)";
      }, { passive: true });

      rowEl.addEventListener("touchend", function () {
        if (!dragging) return;
        dragging = false;
        const shouldOpen = lastDx <= -42;
        rowEl.style.transform = "";
        state.swipeOpenId = shouldOpen ? jobId : null;
        render();
      });
    });
  }

  // ── Date filter popover ──────────────────────────────────────
  function renderDateFilterPopover(shownCount) {
    const chip = document.getElementById("dateFilterChip");
    const label = document.getElementById("dateFilterLabel");
    const popover = document.getElementById("dateFilterPopover");
    const overlay = document.getElementById("popoverOverlay");
    const optionsEl = document.getElementById("dateFilterOptions");
    const customRangeEl = document.getElementById("customRange");
    const clearWrap = document.getElementById("clearFilteredWrap");
    const clearBtn = document.getElementById("clearFilteredBtn");
    const startInput = document.getElementById("customStart");
    const endInput = document.getElementById("customEnd");

    const filterActive = state.dateFilter !== "all";
    chip.classList.toggle("active", filterActive);

    const activeDef = DATE_FILTERS.find(function (d) { return d.key === state.dateFilter; }) || DATE_FILTERS[0];
    let activeLabel = activeDef.label;
    if (state.dateFilter === "custom" && state.customStart && state.customEnd) {
      const fmt = function (s) { return new Date(s + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }); };
      activeLabel = fmt(state.customStart) + " – " + fmt(state.customEnd);
    }
    label.textContent = activeLabel;

    popover.hidden = !state.dateFilterOpen;
    overlay.hidden = !state.dateFilterOpen;

    optionsEl.innerHTML = DATE_FILTERS.map(function (o) {
      const active = state.dateFilter === o.key;
      return '<button class="date-option' + (active ? " active" : "") + '" data-filter-key="' + o.key + '" type="button">'
        + (active ? ICONS.checkmark + " " : "") + o.label + "</button>";
    }).join("");

    customRangeEl.hidden = state.dateFilter !== "custom";
    startInput.value = state.customStart;
    endInput.value = state.customEnd;

    const canClear = filterActive && shownCount > 0;
    clearWrap.hidden = !canClear;
    if (canClear) {
      clearBtn.textContent = "Delete " + shownCount + " job" + (shownCount > 1 ? "s" : "") + " from " + activeLabel;
      clearBtn.onclick = function () {
        state.dateFilterOpen = false;
        removeJobs(currentSortedIds.slice(), "Deleted " + shownCount + " job" + (shownCount > 1 ? "s" : "") + " from " + activeLabel);
      };
    }
  }

  function renderSortLabel() {
    document.getElementById("sortLabel").textContent = "Score: " + (state.sortDesc ? "High → Low" : "Low → High");
  }

  function renderToast() {
    const toastEl = document.getElementById("toast");
    const msgEl = document.getElementById("toastMessage");
    toastEl.hidden = !state.toast;
    if (state.toast) msgEl.textContent = state.toast.message;
  }

  // ── Main render ──────────────────────────────────────────────
  function render() {
    const jobListEl = document.getElementById("jobList");
    const emptyQueueEl = document.getElementById("emptyQueue");
    const emptyFilteredEl = document.getElementById("emptyFiltered");
    const counterEl = document.getElementById("counter");

    if (state.loading) {
      jobListEl.hidden = true;
      emptyQueueEl.hidden = true;
      emptyFilteredEl.hidden = true;
      counterEl.textContent = "";
      return;
    }

    const now = new Date();
    const day0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yest0 = new Date(day0);
    yest0.setDate(yest0.getDate() - 1);

    const filtered = getFilteredJobs(day0);
    const sorted = filtered.slice().sort(function (a, b) {
      return state.sortDesc ? b.matchScore - a.matchScore : a.matchScore - b.matchScore;
    });
    currentSortedIds = sorted.map(function (j) { return j.id; });

    counterEl.textContent = sorted.length + " of " + state.jobs.length + " jobs";

    const isQueueEmpty = state.jobs.length === 0;
    const isFilterEmpty = state.jobs.length > 0 && sorted.length === 0;

    emptyQueueEl.hidden = !isQueueEmpty;
    emptyFilteredEl.hidden = !isFilterEmpty;
    jobListEl.hidden = isQueueEmpty || isFilterEmpty;

    groupIdsByKey = {};

    if (!isQueueEmpty && !isFilterEmpty) {
      const groupMap = new Map();
      sorted.forEach(function (j) {
        const key = j.foundAtDate.toDateString();
        if (!groupMap.has(key)) groupMap.set(key, []);
        groupMap.get(key).push(j);
      });
      const groupKeys = Array.from(groupMap.keys()).sort(function (a, b) { return new Date(b) - new Date(a); });

      jobListEl.innerHTML = groupKeys.map(function (key) {
        const jobsInGroup = groupMap.get(key);
        groupIdsByKey[key] = jobsInGroup.map(function (j) { return j.id; });
        const d = jobsInGroup[0].foundAtDate;
        const d0 = new Date(d.getFullYear(), d.getMonth(), d.getDate());
        let label;
        if (d0.getTime() === day0.getTime()) label = "Today";
        else if (d0.getTime() === yest0.getTime()) label = "Yesterday";
        else label = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

        return (
          '<div class="date-group" data-group-key="' + escapeHtml(key) + '">'
          + '<div class="date-group-header">'
          + '<div class="date-group-label">' + label + " · " + jobsInGroup.length + "</div>"
          + '<button class="clear-day-btn" data-action="clear-day" data-group-key="' + escapeHtml(key) + '" type="button">' + ICONS.trash + " Clear day</button>"
          + "</div>"
          + jobsInGroup.map(buildRowHtml).join("")
          + "</div>"
        );
      }).join("");

      attachRowTouchHandlers();
    }

    renderDateFilterPopover(sorted.length);
    renderSortLabel();
    renderToast();
  }

  // ── Event wiring ─────────────────────────────────────────────
  document.getElementById("sortToggle").addEventListener("click", function () {
    state.sortDesc = !state.sortDesc;
    render();
  });

  document.getElementById("dateFilterChip").addEventListener("click", function () {
    state.dateFilterOpen = !state.dateFilterOpen;
    render();
  });

  document.getElementById("popoverOverlay").addEventListener("click", function () {
    state.dateFilterOpen = false;
    render();
  });

  document.getElementById("dateFilterOptions").addEventListener("click", function (e) {
    const btn = e.target.closest(".date-option");
    if (!btn) return;
    const key = btn.dataset.filterKey;
    state.dateFilter = key;
    state.dateFilterOpen = key === "custom";
    render();
  });

  document.getElementById("customStart").addEventListener("change", function (e) {
    state.customStart = e.target.value;
    render();
  });
  document.getElementById("customEnd").addEventListener("change", function (e) {
    state.customEnd = e.target.value;
    render();
  });

  document.getElementById("resetFilterBtn").addEventListener("click", function () {
    state.dateFilter = "all";
    render();
  });

  document.getElementById("toastUndo").addEventListener("click", undoToast);

  document.getElementById("jobList").addEventListener("click", function (e) {
    const actionEl = e.target.closest("[data-action]");
    if (!actionEl) return;
    const action = actionEl.dataset.action;

    if (action === "clear-day") {
      e.stopPropagation();
      const key = actionEl.dataset.groupKey;
      const ids = groupIdsByKey[key] || [];
      const group = actionEl.closest(".date-group");
      const labelText = group.querySelector(".date-group-label").textContent.split(" · ")[0];
      removeJobs(ids, "Deleted " + ids.length + " job" + (ids.length > 1 ? "s" : "") + " from " + labelText);
      return;
    }

    const shell = e.target.closest(".job-row-shell");
    if (!shell) return;
    const jobId = shell.dataset.jobId;

    if (action === "toggle-expand") {
      e.stopPropagation();
      state.expandedId = state.expandedId === jobId ? null : jobId;
      render();
      return;
    }
    if (action === "delete") {
      e.stopPropagation();
      deleteJob(jobId);
      return;
    }
    if (action === "open-link") {
      deleteJob(jobId, { reason: "opened" });
      return;
    }
    if (action === "open") {
      if (state.swipeOpenId) {
        state.swipeOpenId = null;
        render();
        return;
      }
      handleOpenJob(jobId);
    }
  });

  fetchJobs();
})();
