/* Admin panel logic */
(function () {
  "use strict";

  var TOKEN_KEY = "nima_admin_token";
  // localStorage: stay logged in across tabs and browser restarts
  // (server expires sessions after 30 days or on password change)
  var token = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || "";
  sessionStorage.removeItem(TOKEN_KEY);   // migrate away from old per-tab storage

  var loginView = document.getElementById("login-view");
  var panelView = document.getElementById("panel-view");

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function api(path, opts) {
    opts = opts || {};
    opts.headers = Object.assign({}, opts.headers, {
      "Authorization": "Bearer " + token
    });
    if (opts.body && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(path, opts).then(function (r) {
      if (r.status === 401) {
        logout();
        var errEl = document.getElementById("login-err");
        if (errEl) errEl.textContent = "Your session expired — please log in again.";
        throw new Error("session expired — log in again");
      }
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || "error"); });
      return r.json();
    });
  }

  function closeModals() {
    var m = document.getElementById("modal");
    var bm = document.getElementById("brand-modal");
    var lm = document.getElementById("lead-modal");
    if (m) m.hidden = true;
    if (bm) bm.hidden = true;
    if (lm) lm.hidden = true;
  }

  function show(view) {
    loginView.hidden = view !== "login";
    panelView.hidden = view !== "panel";
    if (view === "login") closeModals();   // never leave a modal over the login screen
  }

  function logout() {
    token = "";
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    show("login");
  }

  // Escape always closes any open modal
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeModals();
  });

  /* ---------------- login ---------------- */
  document.getElementById("login-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var errEl = document.getElementById("login-err");
    errEl.textContent = "";
    fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("l-user").value.trim(),
        password: document.getElementById("l-pass").value
      })
    })
      .then(function (r) {
        if (r.status === 429) throw new Error("Too many attempts — wait 15 minutes and try again.");
        if (!r.ok) throw new Error("Invalid username or password.");
        return r.json();
      })
      .then(function (d) {
        token = d.token;
        localStorage.setItem(TOKEN_KEY, token);
        enterPanel();
      })
      .catch(function (err) { errEl.textContent = err.message || "Login failed."; });
  });

  document.getElementById("logout-btn").addEventListener("click", function () {
    api("/api/admin/logout", { method: "POST" }).catch(function () {});
    logout();
  });

  /* ---------------- tabs ---------------- */
  var currentTab = "stats";
  document.getElementById("sidebar-nav").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-tab]");
    if (!btn) return;
    switchTab(btn.getAttribute("data-tab"));
  });

  function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".sidebar-nav button").forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-tab") === tab);
    });
    document.querySelectorAll(".tab").forEach(function (s) {
      s.hidden = s.id !== "tab-" + tab;
    });
    loaders[tab] && loaders[tab]();
  }

  /* ---------------- stats ---------------- */
  function loadStats() {
    api("/api/admin/stats").then(function (d) {
      // security: warn loudly while the default password is still in use
      var warn = document.getElementById("pw-warning");
      if (d.default_password && !warn) {
        warn = document.createElement("div");
        warn.id = "pw-warning";
        warn.className = "pw-warning";
        warn.innerHTML = "<strong>Security warning:</strong> the admin password is still the default " +
          "(<code>admin123</code>). Change it now in <em>Settings &rarr; Change Password</em>.";
        var tab = document.getElementById("tab-stats");
        tab.insertBefore(warn, tab.children[1]);
      } else if (!d.default_password && warn) {
        warn.remove();
      }
      document.getElementById("st-total").textContent = d.total;
      document.getElementById("st-today").textContent = d.today;
      document.getElementById("st-week").textContent = d.week;
      document.getElementById("st-unread").textContent = d.unread_messages;

      var pill = document.getElementById("msg-pill");
      pill.hidden = d.unread_messages === 0;
      pill.textContent = d.unread_messages;

      var chart = document.getElementById("chart-days");
      if (!d.by_day.length) {
        chart.innerHTML = '<p class="chart-empty">No visits recorded yet.</p>';
      } else {
        var max = Math.max.apply(null, d.by_day.map(function (r) { return r.c; }));
        chart.innerHTML = d.by_day.map(function (r) {
          var h = Math.max(4, Math.round((r.c / max) * 100));
          return '<div class="bar" style="height:' + h + '%" data-tip="' + esc(r.d) + ": " + r.c + '"></div>';
        }).join("");
      }

      var langs = document.getElementById("lang-rows");
      if (!d.by_lang.length) {
        langs.innerHTML = '<p class="chart-empty">No data yet.</p>';
      } else {
        var lmax = Math.max.apply(null, d.by_lang.map(function (r) { return r.c; }));
        langs.innerHTML = d.by_lang.map(function (r) {
          var w = Math.max(3, Math.round((r.c / lmax) * 100));
          return '<div class="lang-row"><span class="lang-name">' + esc(r.lang) + '</span>' +
            '<div class="lang-bar-wrap"><div class="lang-bar" style="width:' + w + '%"></div></div>' +
            '<span class="lang-count">' + r.c + "</span></div>";
        }).join("");
      }
    }).catch(function () {});
  }

  /* ---------------- items (apps / websites) ---------------- */
  var ICONS = {
    edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.8 2.8 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>',
    del: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/></svg>',
    wa: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.5 8.5 0 01-12.6 7.4L3 20.5l1.7-5.3A8.5 8.5 0 1121 11.5z"/><path d="M8.8 9c.4 2.6 3.6 5.8 6.2 6.2l1-1.4 1.8.8-.4 1.6c-2.9.6-7.9-3-9.4-7l1.6-.5.8 1.8L8.8 9z"/></svg>',
    ig: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1"/></svg>'
  };

  function loadItems(table) {
    api("/api/admin/items/" + table).then(function (rows) {
      var el = document.getElementById("table-" + table);
      var hasBuyable = table === "apps" || table === "bots" || table === "games";
      var hasUrl = table !== "apps" || true;        // every table has a link now
      var hasPrice = table !== "opensource";
      var head = "<tr><th>Image</th><th>Title</th>" + (hasPrice ? "<th>Price</th>" : "") +
        (hasBuyable ? "<th>Buyable</th>" : "") + (hasUrl ? "<th>URL</th>" : "") +
        "<th>Status</th><th>Sort</th><th>Actions</th></tr>";
      el.innerHTML = head + rows.map(function (r) {
        return "<tr data-id='" + r.id + "'>" +
          "<td>" + (r.image ? '<img class="row-img" src="' + esc(r.image) + '" alt="">' : '<span class="row-img"></span>') + "</td>" +
          "<td><strong>" + esc(r.title_en) + "</strong><br><span style='color:var(--muted);font-size:.8rem'>" + esc(r.title_fa) + "</span></td>" +
          (hasPrice ? "<td>" + r.price + " " + esc(r.currency) + "</td>" : "") +
          (hasBuyable
            ? "<td>" + (r.buyable ? '<span class="tag">Yes</span>' : '<span class="tag off">No</span>') + "</td>" : "") +
          (hasUrl
            ? "<td style='max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>" + esc(r.url || "—") + "</td>" : "") +
          "<td>" + (r.active ? '<span class="tag">Active</span>' : '<span class="tag off">Hidden</span>') + "</td>" +
          "<td>" + r.sort + "</td>" +
          '<td><div class="row-actions">' +
            '<button class="icon-btn" data-act="edit" title="Edit">' + ICONS.edit + "</button>" +
            '<button class="icon-btn danger" data-act="del" title="Delete">' + ICONS.del + "</button>" +
          "</div></td></tr>";
      }).join("");
      el._rows = rows;
      if (!rows.length) {
        el.innerHTML = head + '<tr><td colspan="9" class="tbl-empty">Nothing here yet' +
          " — press <strong>+ Add</strong> above.</td></tr>";
      }
    }).catch(function (err) {
      // An empty table and a failed request looked identical, which turned a
      // deploy problem ("the server is still running last week's code") into
      // "this section is empty". Say which one it actually is.
      var el = document.getElementById("table-" + table);
      var msg = (err && err.message) || "";
      el.innerHTML = '<tr><td class="tbl-error">' +
        (/not found|404/i.test(msg)
          ? "This section is missing from the running server. The files are " +
            "deployed, but the web app has not been reloaded — press " +
            "<strong>Reload</strong> on the PythonAnywhere Web tab."
          : "Could not load: " + esc(msg || "unknown error")) +
        "</td></tr>";
    });
  }

  ["apps", "bots", "games", "websites", "opensource"].forEach(function (table) {
    document.getElementById("table-" + table).addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-act]");
      if (!btn) return;
      var id = Number(btn.closest("tr").getAttribute("data-id"));
      var row = (this._rows || []).find(function (r) { return r.id === id; });
      if (btn.getAttribute("data-act") === "edit") {
        openItemModal(table, row);
      } else if (confirm("Delete this item permanently?")) {
        api("/api/admin/items/" + table + "/" + id, { method: "DELETE" })
          .then(function () { loadItems(table); });
      }
    });
  });

  document.querySelectorAll("[data-add]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      openItemModal(btn.getAttribute("data-add"), null);
    });
  });

  /* ---------------- link validation ---------------- */
  function checkLink(input, errEl, label, allowLocal) {
    var v = input.value.trim();
    input.classList.remove("bad");
    if (!v) return true;
    var ok = /^https?:\/\//i.test(v);
    if (allowLocal) ok = ok || (v.indexOf("/static/") === 0 && v.indexOf("..") < 0);
    if (!ok) {
      input.classList.add("bad");
      errEl.textContent = label + " must be a real link starting with https:// " +
        (allowLocal ? "(or an uploaded /static/uploads/… path) " : "") +
        "— or leave it empty.";
      input.focus();
      return false;
    }
    return true;
  }

  /* ---------------- item modal ---------------- */
  var modal = document.getElementById("modal");
  var itemForm = document.getElementById("item-form");
  var itemErr = document.getElementById("item-err");
  var editCtx = { table: "apps", id: null };

  function openItemModal(table, row) {
    editCtx = { table: table, id: row ? row.id : null };
    var LABEL = {
      apps: "Application", bots: "Telegram Bot", games: "Game",
      websites: "Website", opensource: "Open Source Project"
    };
    document.getElementById("modal-title").textContent =
      (row ? "Edit " : "Add ") + (LABEL[table] || "Item");
    // every content table now carries its own link
    document.getElementById("url-field").style.display = "";
    document.getElementById("buyable-field").style.display =
      (table === "apps" || table === "bots" || table === "games") ? "" : "none";
    document.getElementById("demo-only-field").hidden = table !== "websites";
    // Open source projects are published, not sold — hiding price avoids
    // implying a figure the public card does not even render.
    document.getElementById("price-field").hidden = table === "opensource";
    document.getElementById("currency-field").hidden = table === "opensource";

    itemForm.reset();
    itemErr.textContent = "";
    itemForm.title_en.value = row ? row.title_en : "";
    itemForm.title_fa.value = row ? row.title_fa : "";
    itemForm.desc_en.value = row ? row.desc_en : "";
    itemForm.desc_fa.value = row ? row.desc_fa : "";
    itemForm.tech.value = row ? row.tech : "";
    itemForm.url.value = row && row.url ? row.url : "";
    itemForm.demo_url.value = row && row.demo_url ? row.demo_url : "";
    itemForm.price.value = row ? row.price : 0;
    itemForm.currency.value = row ? row.currency : "USD";
    itemForm.sort.value = row ? row.sort : 0;
    itemForm.buyable.checked = row ? !!row.buyable : true;
    itemForm.demo_only.checked = row ? !!row.demo_only : false;
    itemForm.active.checked = row ? !!row.active : true;
    itemForm.image.value = row ? row.image : "";
    updatePreview();
    modal.hidden = false;
  }

  function updatePreview() {
    var img = document.getElementById("img-preview");
    var v = itemForm.image.value.trim();
    img.hidden = !v;
    if (v) img.src = v;
  }
  itemForm.image.addEventListener("input", updatePreview);

  document.getElementById("modal-cancel").addEventListener("click", function () { modal.hidden = true; });
  modal.addEventListener("click", function (e) { if (e.target === modal) modal.hidden = true; });

  itemForm.addEventListener("submit", function (e) {
    e.preventDefault();
    itemErr.textContent = "";
    if (!checkLink(itemForm.url, itemErr, "Live URL", false)) return;
    if (!checkLink(itemForm.demo_url, itemErr, "Demo URL", true)) return;
    if (!checkLink(itemForm.image, itemErr, "Image", true)) return;
    var body = {
      title_en: itemForm.title_en.value.trim(),
      title_fa: itemForm.title_fa.value.trim(),
      desc_en: itemForm.desc_en.value.trim(),
      desc_fa: itemForm.desc_fa.value.trim(),
      tech: itemForm.tech.value.trim(),
      url: itemForm.url.value.trim(),
      demo_url: itemForm.demo_url.value.trim(),
      image: itemForm.image.value.trim(),
      price: Number(itemForm.price.value) || 0,
      currency: itemForm.currency.value,
      sort: Number(itemForm.sort.value) || 0,
      buyable: itemForm.buyable.checked ? 1 : 0,
      demo_only: itemForm.demo_only.checked ? 1 : 0,
      active: itemForm.active.checked ? 1 : 0
    };
    var p = editCtx.id
      ? api("/api/admin/items/" + editCtx.table + "/" + editCtx.id, { method: "PUT", body: body })
      : api("/api/admin/items/" + editCtx.table, { method: "POST", body: body });
    p.then(function () {
      modal.hidden = true;
      loadItems(editCtx.table);
    }).catch(function (err) { itemErr.textContent = "Save failed: " + err.message; });
  });

  function uploadFile(file, targetInput, after) {
    var fd = new FormData();
    fd.append("file", file);
    api("/api/admin/upload", { method: "POST", body: fd })
      .then(function (d) {
        targetInput.value = d.url;
        after && after();
      })
      .catch(function (err) { alert("Upload failed: " + err.message); });
  }

  document.getElementById("item-upload").addEventListener("change", function () {
    if (this.files[0]) uploadFile(this.files[0], itemForm.image, updatePreview);
  });

  /* ---------------- brands ---------------- */
  function loadBrands() {
    api("/api/admin/brands").then(function (rows) {
      var el = document.getElementById("table-brands");
      el.innerHTML = "<tr><th>Logo</th><th>Name</th><th>URL</th><th>Status</th><th>Sort</th><th>Actions</th></tr>" +
        rows.map(function (r) {
          return "<tr data-id='" + r.id + "'>" +
            "<td>" + (r.logo ? '<img class="row-img" src="' + esc(r.logo) + '" alt="" style="object-fit:contain">' : '<span class="row-img"></span>') + "</td>" +
            "<td><strong>" + esc(r.name) + "</strong></td>" +
            "<td style='max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>" + esc(r.url || "—") + "</td>" +
            "<td>" + (r.active ? '<span class="tag">Active</span>' : '<span class="tag off">Hidden</span>') + "</td>" +
            "<td>" + r.sort + "</td>" +
            '<td><div class="row-actions">' +
              '<button class="icon-btn" data-act="edit" title="Edit">' + ICONS.edit + "</button>" +
              '<button class="icon-btn danger" data-act="del" title="Delete">' + ICONS.del + "</button>" +
            "</div></td></tr>";
        }).join("");
      el._rows = rows;
    }).catch(function () {});
  }

  var brandModal = document.getElementById("brand-modal");
  var brandForm = document.getElementById("brand-form");
  var brandErr = document.getElementById("brand-err");
  var brandId = null;

  function openBrandModal(row) {
    brandId = row ? row.id : null;
    document.getElementById("brand-modal-title").textContent = row ? "Edit Brand" : "Add Brand";
    brandForm.reset();
    brandErr.textContent = "";
    brandForm.name.value = row ? row.name : "";
    brandForm.url.value = row ? row.url : "";
    brandForm.logo.value = row ? row.logo : "";
    brandForm.sort.value = row ? row.sort : 0;
    brandForm.active.checked = row ? !!row.active : true;
    brandModal.hidden = false;
  }

  document.getElementById("add-brand").addEventListener("click", function () { openBrandModal(null); });
  document.getElementById("brand-cancel").addEventListener("click", function () { brandModal.hidden = true; });
  brandModal.addEventListener("click", function (e) { if (e.target === brandModal) brandModal.hidden = true; });

  document.getElementById("table-brands").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-act]");
    if (!btn) return;
    var id = Number(btn.closest("tr").getAttribute("data-id"));
    var row = (this._rows || []).find(function (r) { return r.id === id; });
    if (btn.getAttribute("data-act") === "edit") {
      openBrandModal(row);
    } else if (confirm("Delete this brand?")) {
      api("/api/admin/brands/" + id, { method: "DELETE" }).then(loadBrands);
    }
  });

  brandForm.addEventListener("submit", function (e) {
    e.preventDefault();
    brandErr.textContent = "";
    if (!checkLink(brandForm.url, brandErr, "Website URL", true)) return;
    if (!checkLink(brandForm.logo, brandErr, "Logo", true)) return;
    var body = {
      name: brandForm.name.value.trim(),
      url: brandForm.url.value.trim(),
      logo: brandForm.logo.value.trim(),
      sort: Number(brandForm.sort.value) || 0,
      active: brandForm.active.checked ? 1 : 0
    };
    var p = brandId
      ? api("/api/admin/brands/" + brandId, { method: "PUT", body: body })
      : api("/api/admin/brands", { method: "POST", body: body });
    p.then(function () { brandModal.hidden = true; loadBrands(); })
      .catch(function (err) { brandErr.textContent = "Save failed: " + err.message; });
  });

  document.getElementById("brand-upload").addEventListener("change", function () {
    if (this.files[0]) uploadFile(this.files[0], brandForm.logo);
  });

  /* ---------------- messages ---------------- */
  function loadMessages() {
    api("/api/admin/messages").then(function (rows) {
      var el = document.getElementById("messages-list");
      if (!rows.length) {
        el.innerHTML = '<p class="chart-empty">No messages yet.</p>';
        return;
      }
      el.innerHTML = rows.map(function (m) {
        return '<div class="msg ' + (m.read ? "" : "unread") + '" data-id="' + m.id + '">' +
          '<div class="msg-head"><strong>' + esc(m.name) + "</strong>" +
          '<span class="msg-meta">' + esc(m.created_at) + " UTC</span>" +
          '<div class="row-actions">' +
            (!m.read ? '<button class="icon-btn" data-act="read" title="Mark as read"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg></button>' : "") +
            '<button class="icon-btn danger" data-act="del" title="Delete">' + ICONS.del + "</button>" +
          "</div></div>" +
          (m.subject ? '<p class="msg-subject">' + esc(m.subject) + "</p>" : "") +
          '<p class="msg-body">' + esc(m.message) + "</p>" +
          '<div class="msg-contacts">' +
            (m.email ? '<a href="mailto:' + esc(m.email) + '">' + esc(m.email) + "</a>" : "") +
            (m.phone ? '<a href="tel:' + esc(m.phone) + '">' + esc(m.phone) + "</a>" : "") +
          "</div></div>";
      }).join("");
    }).catch(function () {});
  }

  document.getElementById("messages-list").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-act]");
    if (!btn) return;
    var id = Number(btn.closest(".msg").getAttribute("data-id"));
    if (btn.getAttribute("data-act") === "read") {
      api("/api/admin/messages/" + id + "/read", { method: "PUT" }).then(function () {
        loadMessages(); loadStats();
      });
    } else if (confirm("Delete this message?")) {
      api("/api/admin/messages/" + id, { method: "DELETE" }).then(function () {
        loadMessages(); loadStats();
      });
    }
  });

  /* ---------------- settings ---------------- */
  var settingsForm = document.getElementById("settings-form");

  function loadSettings() {
    api("/api/admin/settings").then(function (s) {
      Object.keys(s).forEach(function (k) {
        if (settingsForm.elements[k]) settingsForm.elements[k].value = s[k];
      });
    }).catch(function () {});
  }

  settingsForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var status = document.getElementById("settings-status");
    var out = {};
    Array.prototype.forEach.call(settingsForm.elements, function (el) {
      if (el.name) out[el.name] = el.value;
    });
    api("/api/admin/settings", { method: "PUT", body: { settings: out } })
      .then(function () {
        status.textContent = "Saved.";
        status.className = "save-status ok";
      })
      .catch(function () {
        status.textContent = "Save failed.";
        status.className = "save-status bad";
      });
  });

  document.getElementById("password-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var f = e.target;
    var status = document.getElementById("password-status");
    api("/api/admin/password", {
      method: "PUT",
      body: { current: f.current.value, new: f.new.value }
    })
      .then(function () {
        status.textContent = "Password changed. Please log in again.";
        status.className = "save-status ok";
        setTimeout(logout, 1200);
      })
      .catch(function (err) {
        status.textContent = err.message || "Failed.";
        status.className = "save-status bad";
      });
  });

  /* ---------------- project finder ---------------- */
  /* Finds local businesses that need a website and drafts the Persian message
     that names the gap. The panel never sends anything — see app/finder.py. */
  var fdMeta = null;        // categories + statuses, fetched once
  var fdLeads = [];
  var fdPoll = null;
  var fdLead = null;        // the lead open in the modal

  function fdEl(id) { return document.getElementById(id); }

  function fdLoad() {
    return api("/api/admin/finder").then(function (d) {
      var first = !fdMeta;
      fdMeta = d;
      fdSummary(d.summary);
      if (first) fdBuildControls(d);
      fdConfig(d.config);
      fdRunCard(d.active_run, d.runs && d.runs[0]);
      if (d.active_run) fdStartPoll();
      apLoad();
      return fdLoadLeads();
    }).catch(function () {});
  }

  function fdSummary(s) {
    if (!s) return;
    fdEl("fd-total").textContent = s.total;
    fdEl("fd-hot").textContent = s.hot;
    fdEl("fd-nosite").textContent = s.no_website;
    fdEl("fd-reach").textContent = s.reachable;
    fdEl("fd-igonly").textContent = s.ig_only;
    fdEl("fd-unprofiled").textContent = s.unprofiled;
    // the sidebar pill counts what is actually waiting on you: untouched leads
    var pill = fdEl("fd-pill");
    var waiting = (s.by_status && s.by_status["new"]) || 0;
    pill.textContent = waiting;
    pill.hidden = waiting === 0;
  }

  function fdBuildControls(d) {
    fdEl("fd-cats").innerHTML = d.categories.map(function (c) {
      var on = d.default_categories.indexOf(c.key) !== -1;
      return '<label class="fd-cat"><input type="checkbox" value="' + esc(c.key) + '"' +
        (on ? " checked" : "") + '><span>' + esc(c.en) +
        '<em dir="rtl">' + esc(c.fa) + "</em></span></label>";
    }).join("");

    fdEl("fd-f-cat").innerHTML = '<option value="">All types</option>' +
      d.categories.map(function (c) {
        return '<option value="' + esc(c.key) + '">' + esc(c.en) + "</option>";
      }).join("");

    var statusOpts = d.statuses.map(function (s) {
      return '<option value="' + esc(s.key) + '">' + esc(s.key) + " — " + esc(s.fa) + "</option>";
    }).join("");
    fdEl("fd-f-status").innerHTML = '<option value="">All statuses</option>' + statusOpts;
    fdEl("lead-status").innerHTML = statusOpts;
  }

  function fdConfig(c) {
    if (!c) return;
    fdEl("fd-city").value = c.city || "";
    fdEl("fd-radius").value = c.radius_km || 20;
  }

  function fdCheckedCats() {
    return Array.prototype.filter.call(
      fdEl("fd-cats").querySelectorAll("input"), function (i) { return i.checked; }
    ).map(function (i) { return i.value; });
  }

  function fdLoadLeads() {
    var qs = "?status=" + encodeURIComponent(fdEl("fd-f-status").value) +
      "&tier=" + encodeURIComponent(fdEl("fd-f-tier").value) +
      "&category=" + encodeURIComponent(fdEl("fd-f-cat").value) +
      "&reach=" + encodeURIComponent(fdEl("fd-f-reach").value) +
      "&q=" + encodeURIComponent(fdEl("fd-f-q").value.trim());
    return api("/api/admin/finder/leads" + qs).then(function (d) {
      fdLeads = d.leads;
      fdRenderTable();
    }).catch(function () {});
  }

  function fdRenderTable() {
    var el = fdEl("table-finder");
    if (!fdLeads.length) {
      el.innerHTML = '<tr><td class="fd-empty">No leads yet — press ' +
        "<strong>Find businesses</strong> to search your city. " +
        "The first run takes a minute or two.</td></tr>";
      return;
    }
    el.innerHTML = "<tr><th>Score</th><th>Business</th><th>Why</th><th>Reach</th>" +
      "<th>Status</th><th>Actions</th></tr>" +
      fdLeads.map(function (l) {
        // Only the top three signals: the table answers "is this worth opening",
        // the modal answers "what exactly did you find".
        var tags = l.signals.slice(0, 3).map(function (s) {
          return '<span class="sig' + (s.weight < 0 ? " neg" : "") + '" dir="rtl">' +
            esc(s.fa) + "</span>";
        }).join("");
        var more = l.signals.length > 3
          ? '<span class="sig muted">+' + (l.signals.length - 3) + "</span>" : "";
        var reach = [];
        if (l.is_mobile) reach.push('<span class="reach wa">WhatsApp</span>');
        else if (l.phone_e164) reach.push('<span class="reach">Landline</span>');
        if (l.instagram) reach.push('<span class="reach ig">@' + esc(l.instagram) + "</span>");
        if (!reach.length) reach.push('<span class="reach off">—</span>');
        var statusClass = l.status === "won" ? "" :
          (l.status === "lost" || l.status === "skip" ? " off" : " neutral");
        return "<tr data-id='" + l.id + "'>" +
          '<td><span class="score-badge ' + esc(l.tier) + '">' + l.score + "</span></td>" +
          "<td><strong>" + esc(l.name) + "</strong><br>" +
            '<span class="fd-meta">' + esc(l.category_fa) +
            (l.domain ? " · " + esc(l.domain) : "") + "</span></td>" +
          '<td class="sig-cell">' + tags + more + "</td>" +
          "<td>" + reach.join(" ") + "</td>" +
          '<td><span class="tag' + statusClass + '" dir="rtl">' + esc(l.status_fa) + "</span></td>" +
          '<td><div class="row-actions">' +
            '<button class="icon-btn" data-act="open" title="Open">' + ICONS.edit + "</button>" +
            (l.is_mobile
              ? '<button class="icon-btn wa-btn" data-act="wa" title="WhatsApp">' + ICONS.wa + "</button>"
              : "") +
            (l.instagram
              ? '<button class="icon-btn ig-btn" data-act="ig" title="Copy message and open Instagram DM">' + ICONS.ig + "</button>"
              : "") +
          "</div></td></tr>";
      }).join("");
  }

  fdEl("table-finder").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-act]");
    var tr = e.target.closest("tr[data-id]");
    if (!tr) return;
    var id = +tr.getAttribute("data-id");
    var lead = fdLeads.filter(function (l) { return l.id === id; })[0];
    if (!lead) return;
    if (btn && btn.getAttribute("data-act") === "wa") {
      fdOpenWhatsApp(lead, lead.pitch);
      return;
    }
    if (btn && btn.getAttribute("data-act") === "ig") {
      fdOpenInstagram(lead, lead.pitch);
      return;
    }
    fdOpenLead(lead);
  });

  ["fd-f-status", "fd-f-tier", "fd-f-cat", "fd-f-reach"].forEach(function (id) {
    fdEl(id).addEventListener("change", fdLoadLeads);
  });
  var fdSearchTimer = null;
  fdEl("fd-f-q").addEventListener("input", function () {
    clearTimeout(fdSearchTimer);
    fdSearchTimer = setTimeout(fdLoadLeads, 300);
  });

  /* ----- runs ----- */
  function fdRunCard(active, last) {
    var card = fdEl("fd-run-card");
    var msg = fdEl("fd-run-msg");
    var spin = fdEl("fd-spinner");
    var run = active || last;
    if (!run) { card.hidden = true; return; }
    card.hidden = false;
    spin.hidden = !active;
    var parts = [];
    if (run.found) parts.push(run.found + " found");
    if (run.added) parts.push(run.added + " new");
    if (run.profiled) parts.push(run.profiled + " sites checked");
    var detail = parts.length ? " (" + parts.join(", ") + ")" : "";
    if (active) {
      msg.textContent = (run.message || "Working…") + detail;
      msg.className = "";
    } else if (run.status === "error") {
      msg.textContent = "Failed: " + (run.message || "unknown error");
      msg.className = "fd-bad";
    } else {
      msg.textContent = "Last run finished" + detail + ". " + (run.message || "");
      msg.className = "fd-ok";
    }
  }

  function fdStartPoll() {
    if (fdPoll) return;
    fdPoll = setInterval(function () {
      api("/api/admin/finder/run").then(function (d) {
        fdSummary(d.summary);
        fdRunCard(d.active, d.last);
        if (!d.active) {
          clearInterval(fdPoll);
          fdPoll = null;
          fdLoadLeads();
          apLoad();
          if (!fdEl("fd-outbox-card").hidden) apOutbox();
        }
      }).catch(function () { clearInterval(fdPoll); fdPoll = null; });
    }, 3000);
  }

  function fdBusy(on) {
    ["fd-run", "fd-profile"].forEach(function (id) { fdEl(id).disabled = on; });
  }

  function fdRunError(err) {
    fdEl("fd-run-card").hidden = false;
    fdEl("fd-run-msg").textContent = err && err.message ? err.message : "Could not start.";
    fdEl("fd-run-msg").className = "fd-bad";
    fdEl("fd-spinner").hidden = true;
  }

  fdEl("fd-run").addEventListener("click", function () {
    fdBusy(true);
    api("/api/admin/finder/discover", {
      method: "POST",
      body: {
        city: fdEl("fd-city").value.trim(),
        categories: fdCheckedCats(),
        radius_km: +fdEl("fd-radius").value || 20,
        limit: +fdEl("fd-limit").value || 400,
        profile: true
      }
    }).then(function (run) {
      fdRunCard(run, run);
      fdStartPoll();
    }).catch(fdRunError).then(function () { fdBusy(false); });
  });

  fdEl("fd-profile").addEventListener("click", function () {
    fdBusy(true);
    api("/api/admin/finder/profile", { method: "POST" })
      .then(function (run) { fdRunCard(run, run); fdStartPoll(); })
      .catch(fdRunError).then(function () { fdBusy(false); });
  });

  fdEl("fd-export").addEventListener("click", function () {
    // the CSV route needs the Bearer header, so it cannot be a plain link
    fetch("/api/admin/finder/export.csv", {
      headers: { "Authorization": "Bearer " + token }
    }).then(function (r) { return r.blob(); }).then(function (blob) {
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "leads.csv";
      a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }).catch(function () {});
  });

  /* ---------------- autopilot ---------------- */
  /* The panel is a window onto the queue, not a second place where sending
     rules live. Everything here either reads state or asks the server to
     change it — the browser never decides whether a message may go out. */
  var apTimer = null;

  function apLoad() {
    return api("/api/admin/finder/autopilot").then(apRender).catch(function () {});
  }

  function apRender(d) {
    var c = d.config;
    fdEl("fd-auto-on").checked = !!c.enabled;
    fdEl("fd-a-queued").textContent = d.queued;
    fdEl("fd-a-today").textContent = d.sent_today + " / " + c.daily_cap;
    fdEl("fd-a-sent").textContent = d.sent;
    fdEl("fd-a-failed").textContent = d.failed;
    fdEl("fd-a-unres").textContent = d.unresearched;
    // Don't fight the user while they are typing in one of these.
    [["fd-a-cap", c.daily_cap], ["fd-a-gap", c.min_gap_s], ["fd-a-score", c.min_score],
     ["fd-a-qs", c.quiet_start], ["fd-a-qe", c.quiet_end]].forEach(function (p) {
      var el = fdEl(p[0]);
      if (document.activeElement !== el) el.value = p[1];
    });
    fdEl("fd-a-key").value = d.agent_key || "";

    var state = fdEl("fd-auto-state");
    if (!c.enabled) {
      state.textContent = "Paused — the sender is handed nothing while this is off.";
      state.className = "fd-note";
    } else if (d.quiet_now) {
      state.textContent = "Running, but inside quiet hours (" + c.quiet_start +
        "–" + c.quiet_end + ") — nothing goes out until " + c.quiet_end + ".";
      state.className = "fd-note";
    } else if (d.sent_today >= c.daily_cap) {
      state.textContent = "Running — daily cap of " + c.daily_cap + " reached, resumes tomorrow.";
      state.className = "fd-note";
    } else {
      state.textContent = "Running — handing the sender one message roughly every " +
        Math.round(c.min_gap_s / 60) + " min, up to " + c.daily_cap + " a day.";
      state.className = "fd-note fd-ok";
    }
    fdEl("fd-a-next").textContent = d.next_due ? "next due " + d.next_due : "";

    // Poll while it is actually doing something; stop when it is idle.
    var busy = c.enabled && d.queued > 0;
    if (busy && !apTimer) apTimer = setInterval(apLoad, 15000);
    if (!busy && apTimer) { clearInterval(apTimer); apTimer = null; }
  }

  function apSave(extra) {
    var body = Object.assign({
      daily_cap: +fdEl("fd-a-cap").value || 25,
      min_gap_s: +fdEl("fd-a-gap").value || 140,
      min_score: +fdEl("fd-a-score").value || 0,
      quiet_start: fdEl("fd-a-qs").value.trim(),
      quiet_end: fdEl("fd-a-qe").value.trim()
    }, extra || {});
    return api("/api/admin/finder/autopilot", { method: "PUT", body: body })
      .then(apRender).catch(function () {});
  }

  fdEl("fd-auto-on").addEventListener("change", function () {
    var on = this.checked;
    if (on && !confirm(
        "Turn on automatic sending?\n\n" +
        "The sender on your PC will start messaging businesses on WhatsApp " +
        "without asking you each time. Make sure it is running on a second " +
        "number, not the one your clients use.")) {
      this.checked = false;
      return;
    }
    apSave({ enabled: on });
  });
  fdEl("fd-a-save").addEventListener("click", function () { apSave(); });

  fdEl("fd-a-copykey").addEventListener("click", function () {
    var el = fdEl("fd-a-key");
    el.select();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(el.value).then(function () {
        fdEl("fd-a-copykey").textContent = "Copied";
        setTimeout(function () { fdEl("fd-a-copykey").textContent = "Copy"; }, 1600);
      }, function () {});
    }
  });

  fdEl("fd-research").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    api("/api/admin/finder/research?limit=60", { method: "POST" })
      .then(function (run) { fdRunCard(run, run); fdStartPoll(); })
      .catch(fdRunError)
      .then(function () { btn.disabled = false; });
  });

  /* ----- outbox ----- */
  function apOutbox() {
    var f = fdEl("fd-ob-filter").value;
    return api("/api/admin/finder/outbox?limit=200&status=" + encodeURIComponent(f))
      .then(function (d) {
        var el = fdEl("table-outbox");
        if (!d.outbox.length) {
          el.innerHTML = '<tr><td class="tbl-empty">Nothing in the outbox yet — press ' +
            "<strong>Research &amp; queue messages</strong>.</td></tr>";
          return;
        }
        el.innerHTML = "<tr><th>Status</th><th>Business</th><th>Need</th>" +
          "<th>To</th><th>Due / sent</th><th>Message</th><th></th></tr>" +
          d.outbox.map(function (o) {
            return "<tr data-ob='" + o.id + "'>" +
              '<td><span class="tag ' + esc(o.status) + '">' + esc(o.status) + "</span></td>" +
              "<td><strong>" + esc(o.name) + "</strong><br>" +
                '<span class="fd-meta">score ' + o.score + "</span></td>" +
              '<td class="ob-need" dir="rtl">' + esc(o.need_fa || o.need) + "</td>" +
              '<td class="fd-meta" dir="ltr">+' + esc(o.to_addr) + "</td>" +
              '<td class="fd-meta" dir="ltr">' + esc(o.sent_at || o.due_at) + "</td>" +
              '<td class="ob-body" dir="rtl" title="' + esc(o.body) + '">' +
                esc(o.body.split("\n")[1] || o.body) + "</td>" +
              '<td><div class="row-actions">' +
                '<button class="icon-btn" data-ob-act="requeue" title="Send this one next">' + ICONS.edit + "</button>" +
                '<button class="icon-btn danger" data-ob-act="drop" title="Remove from queue">' + ICONS.del + "</button>" +
              "</div></td></tr>" +
              (o.error ? '<tr><td colspan="7" class="fd-meta fd-bad">' + esc(o.error) + "</td></tr>" : "");
          }).join("");
      }).catch(function () {});
  }

  fdEl("fd-a-outbox").addEventListener("click", function () {
    var card = fdEl("fd-outbox-card");
    card.hidden = !card.hidden;
    this.textContent = card.hidden ? "Show outbox" : "Hide outbox";
    if (!card.hidden) apOutbox();
  });
  fdEl("fd-ob-filter").addEventListener("change", apOutbox);

  fdEl("table-outbox").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-ob-act]");
    if (!btn) return;
    var id = btn.closest("tr").getAttribute("data-ob");
    var act = btn.getAttribute("data-ob-act");
    if (act === "drop" && !confirm("Remove this message from the queue?")) return;
    var req = act === "requeue"
      ? api("/api/admin/finder/outbox/" + id + "/requeue", { method: "POST" })
      : api("/api/admin/finder/outbox/" + id, { method: "DELETE" });
    req.then(function () { apOutbox(); apLoad(); }).catch(function () {});
  });

  /* ----- lead modal ----- */
  function fdOpenWhatsApp(lead, text) {
    if (!lead.is_mobile) return;
    window.open("https://wa.me/" + lead.phone_e164 + "?text=" + encodeURIComponent(text),
                "_blank", "noopener");
  }

  /* Instagram cannot pre-fill a message from a URL — no app can, it simply is
     not a feature. So the only honest flow is: put the pitch on the clipboard,
     open the DM thread, and let the paste be one deliberate keystroke. */
  function fdCopy(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(
        function () { return true; }, function () { return false; });
    }
    return Promise.resolve(false);
  }

  function fdOpenInstagram(lead, text) {
    if (!lead.ig) return;
    // Copy first, then open: a popup stealing focus can cancel a clipboard write.
    fdCopy(text).then(function (copied) {
      window.open(lead.ig, "_blank", "noopener");
      var err = fdEl("lead-err");
      if (err && !fdEl("lead-modal").hidden) {
        err.textContent = copied
          ? "Message copied — paste it into the DM with Ctrl+V."
          : "Could not copy automatically — select the message and copy it by hand.";
        err.className = "modal-err" + (copied ? " ok" : "");
      }
    });
  }

  function fdOpenLead(lead) {
    fdLead = lead;
    fdEl("lead-name").textContent = lead.name;
    fdEl("lead-sub").textContent = [lead.category_fa, lead.address, lead.city]
      .filter(Boolean).join(" · ");
    var badge = fdEl("lead-score");
    badge.textContent = lead.score;
    badge.className = "score-badge " + lead.tier;

    var c = [];
    if (lead.phone) {
      c.push('<a class="lead-chip" href="tel:+' + esc(lead.phone_e164) + '">' +
        esc(lead.phone) + (lead.is_mobile ? " (mobile)" : " (landline)") + "</a>");
    }
    if (lead.instagram) {
      c.push('<a class="lead-chip" target="_blank" rel="noopener" href="https://instagram.com/' +
        esc(lead.instagram) + '">@' + esc(lead.instagram) + "</a>");
    }
    if (lead.website) {
      c.push('<a class="lead-chip" target="_blank" rel="noopener" href="' +
        esc(lead.website) + '">' + esc(lead.domain) + "</a>");
    }
    if (lead.email) c.push('<span class="lead-chip">' + esc(lead.email) + "</span>");
    c.push('<a class="lead-chip" target="_blank" rel="noopener" href="https://www.openstreetmap.org/' +
      esc(lead.osm_id) + '">on the map</a>');
    fdEl("lead-contacts").innerHTML = c.join("");

    fdEl("lead-signals").innerHTML = lead.signals.map(function (s) {
      var body = '<span class="sig' + (s.weight < 0 ? " neg" : "") + '" dir="rtl" title="' +
        esc(s.code + (s.value ? " = " + s.value : "")) + '">' + esc(s.fa) +
        (s.value ? " · " + esc(s.value) : "") + "</span>";
      // evidence is a URL the profiler actually fetched — let it be checked
      return (s.evidence && s.evidence.indexOf("http") === 0)
        ? '<a href="' + esc(s.evidence) + '" target="_blank" rel="noopener">' + body + "</a>"
        : body;
    }).join("") || '<span class="fd-meta">No signals recorded.</span>';

    fdEl("lead-pitch").value = lead.pitch || "";
    fdEl("lead-note").value = lead.note || "";
    fdEl("lead-status").value = lead.status;
    fdEl("lead-err").textContent = "";
    fdEl("lead-err").className = "modal-err";
    fdEl("lead-wa").disabled = !lead.is_mobile;
    fdEl("lead-wa").textContent = lead.is_mobile ? "Open WhatsApp" : "No mobile number";
    // Hidden rather than disabled: a greyed-out button on every lead without an
    // account is just noise on the screen you spend the most time looking at.
    fdEl("lead-ig").hidden = !lead.ig;
    fdEl("lead-modal").hidden = false;
  }

  fdEl("lead-cancel").addEventListener("click", function () {
    fdEl("lead-modal").hidden = true;
  });

  fdEl("lead-copy").addEventListener("click", function () {
    var text = fdEl("lead-pitch").value;
    var done = function () {
      fdEl("lead-err").textContent = "Copied.";
      fdEl("lead-err").className = "modal-err ok";
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {});
    } else {
      // no clipboard API off localhost/https — select it so Ctrl+C works
      fdEl("lead-pitch").select();
      done();
    }
  });

  fdEl("lead-regen").addEventListener("click", function () {
    if (!fdLead) return;
    api("/api/admin/finder/leads/" + fdLead.id + "/regenerate", { method: "POST" })
      .then(function (d) { fdEl("lead-pitch").value = d.pitch; })
      .catch(function (err) { fdEl("lead-err").textContent = err.message || "Failed."; });
  });

  fdEl("lead-wa").addEventListener("click", function () {
    if (!fdLead) return;
    fdOpenWhatsApp(fdLead, fdEl("lead-pitch").value);
    // Opening the chat is not the same as sending it, so the status is only
    // pre-selected here — it is saved when you press Save.
    if (fdEl("lead-status").value === "new") {
      fdEl("lead-status").value = "contacted";
      fdEl("lead-err").textContent = "Marked as contacted — press Save to keep it.";
      fdEl("lead-err").className = "modal-err ok";
    }
  });

  fdEl("lead-ig").addEventListener("click", function () {
    if (!fdLead) return;
    fdOpenInstagram(fdLead, fdEl("lead-pitch").value);
    if (fdEl("lead-status").value === "new") fdEl("lead-status").value = "contacted";
  });

  fdEl("lead-save").addEventListener("click", function () {
    if (!fdLead) return;
    api("/api/admin/finder/leads/" + fdLead.id, {
      method: "PUT",
      body: {
        status: fdEl("lead-status").value,
        note: fdEl("lead-note").value,
        pitch: fdEl("lead-pitch").value
      }
    }).then(function () {
      fdEl("lead-modal").hidden = true;
      fdLoad();
    }).catch(function (err) {
      fdEl("lead-err").textContent = err.message || "Save failed.";
      fdEl("lead-err").className = "modal-err";
    });
  });

  fdEl("lead-delete").addEventListener("click", function () {
    if (!fdLead) return;
    if (!confirm("Delete this lead? Re-running discovery will find it again.")) return;
    api("/api/admin/finder/leads/" + fdLead.id, { method: "DELETE" })
      .then(function () { fdEl("lead-modal").hidden = true; fdLoad(); })
      .catch(function () {});
  });

  /* ---------------- boot ---------------- */
  var loaders = {
    stats: loadStats,
    apps: function () { loadItems("apps"); },
    bots: function () { loadItems("bots"); },
    games: function () { loadItems("games"); },
    websites: function () { loadItems("websites"); },
    opensource: function () { loadItems("opensource"); },
    brands: loadBrands,
    finder: fdLoad,
    messages: loadMessages,
    settings: loadSettings
  };

  function enterPanel() {
    show("panel");
    switchTab("stats");
  }

  if (token) {
    // validate existing session
    api("/api/admin/stats").then(enterPanel).catch(function () { show("login"); });
  } else {
    show("login");
  }
})();
