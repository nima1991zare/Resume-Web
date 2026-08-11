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
    if (m) m.hidden = true;
    if (bm) bm.hidden = true;
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
    del: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/></svg>'
  };

  function loadItems(table) {
    api("/api/admin/items/" + table).then(function (rows) {
      var el = document.getElementById("table-" + table);
      var hasBuyable = table === "apps" || table === "games";
      var hasUrl = table === "websites" || table === "games";
      var head = "<tr><th>Image</th><th>Title</th><th>Price</th>" +
        (hasBuyable ? "<th>Buyable</th>" : "") + (hasUrl ? "<th>URL</th>" : "") +
        "<th>Status</th><th>Sort</th><th>Actions</th></tr>";
      el.innerHTML = head + rows.map(function (r) {
        return "<tr data-id='" + r.id + "'>" +
          "<td>" + (r.image ? '<img class="row-img" src="' + esc(r.image) + '" alt="">' : '<span class="row-img"></span>') + "</td>" +
          "<td><strong>" + esc(r.title_en) + "</strong><br><span style='color:var(--muted);font-size:.8rem'>" + esc(r.title_fa) + "</span></td>" +
          "<td>" + r.price + " " + esc(r.currency) + "</td>" +
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
    }).catch(function () {});
  }

  ["apps", "games", "websites"].forEach(function (table) {
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
    document.getElementById("modal-title").textContent =
      (row ? "Edit " : "Add ") +
      (table === "apps" ? "Application" : (table === "games" ? "Game" : "Website"));
    document.getElementById("url-field").style.display =
      (table === "websites" || table === "games") ? "" : "none";
    document.getElementById("buyable-field").style.display =
      (table === "apps" || table === "games") ? "" : "none";

    itemForm.reset();
    itemErr.textContent = "";
    itemForm.title_en.value = row ? row.title_en : "";
    itemForm.title_fa.value = row ? row.title_fa : "";
    itemForm.desc_en.value = row ? row.desc_en : "";
    itemForm.desc_fa.value = row ? row.desc_fa : "";
    itemForm.tech.value = row ? row.tech : "";
    itemForm.url.value = row && row.url ? row.url : "";
    itemForm.price.value = row ? row.price : 0;
    itemForm.currency.value = row ? row.currency : "USD";
    itemForm.sort.value = row ? row.sort : 0;
    itemForm.buyable.checked = row ? !!row.buyable : true;
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
    if (!checkLink(itemForm.image, itemErr, "Image", true)) return;
    var body = {
      title_en: itemForm.title_en.value.trim(),
      title_fa: itemForm.title_fa.value.trim(),
      desc_en: itemForm.desc_en.value.trim(),
      desc_fa: itemForm.desc_fa.value.trim(),
      tech: itemForm.tech.value.trim(),
      url: itemForm.url.value.trim(),
      image: itemForm.image.value.trim(),
      price: Number(itemForm.price.value) || 0,
      currency: itemForm.currency.value,
      sort: Number(itemForm.sort.value) || 0,
      buyable: itemForm.buyable.checked ? 1 : 0,
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
    if (!checkLink(brandForm.url, brandErr, "Website URL", false)) return;
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

  /* ---------------- boot ---------------- */
  var loaders = {
    stats: loadStats,
    apps: function () { loadItems("apps"); },
    games: function () { loadItems("games"); },
    websites: function () { loadItems("websites"); },
    brands: loadBrands,
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
