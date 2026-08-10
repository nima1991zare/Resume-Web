/* MORPH — scroll-driven 3D particle formation engine.
   One canvas, two layers:
   · a full-screen living starfield (drifting + twinkling, edge to edge)
   · a 3D formation that morphs as you scroll:
     0 nebula → 1 DNA helix → 2 data grid → 3 wireframe globe
     → 4 orbit rings → 5 vortex.
   Always animated. Reduced-motion users get a slower, gentler version.
   Exposes window.MORPH.setPhase(float 0..5). */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SPEED = reduced ? 0.35 : 1;   // slow everything down for reduced-motion
  var canvas = document.getElementById("morph-canvas");
  if (!canvas) return;

  var ctx = canvas.getContext("2d", { alpha: true });
  var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  var W = 0, H = 0, CX = 0, CY = 0, R = 0;
  var N = 300;
  var FOV = 640;
  var phase = 0;            // target phase (from scroll)
  var phaseS = 0;           // smoothed phase actually rendered
  var running = true;
  var time = 0;

  /* ---------------- full-screen starfield layer ---------------- */
  var stars = [];           // {x, y, vx, vy, r, tw, base}
  function spawnStars() {
    var count = Math.min(170, Math.floor((W * H) / 9000));
    stars = [];
    for (var i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.18 - 0.05,
        r: Math.random() * 1.4 + 0.4,
        tw: Math.random() * Math.PI * 2,          // twinkle phase
        base: 0.15 + Math.random() * 0.45         // base brightness
      });
    }
  }

  // per-particle stable randoms
  var rnd1 = [], rnd2 = [], rnd3 = [];
  for (var i = 0; i < 600; i++) {
    rnd1.push(Math.random());
    rnd2.push(Math.random());
    rnd3.push(Math.random());
  }

  // particle current positions (world space) — they chase targets
  var px = [], py = [], pz = [];

  /* ---------------- formation colors [r,g,b] ---------------- */
  var COLORS = [
    [74, 222, 128],   // 0 hero      — green
    [56, 189, 248],   // 1 about     — cyan
    [167, 139, 250],  // 2 apps      — violet
    [96, 165, 250],   // 3 websites  — blue
    [251, 191, 36],   // 4 brands    — amber
    [74, 222, 128]    // 5 contact   — green
  ];

  /* ---------------- formations ----------------
     Each: target(i, t, out[3]) writes x,y,z; link(i) -> j|-1 for structural line */

  // 0 · NEBULA — slow swirling cloud, stretched to fill the viewport
  function fNebula(i, t, o) {
    var a = rnd1[i] * Math.PI * 2 + t * 0.07;
    var r = Math.pow(rnd2[i], 0.6) * R * 1.35;
    var stretchX = Math.max(1, (W / Math.max(H, 1)) * 0.95);
    var y = (rnd3[i] - 0.5) * R * 2.1;
    o[0] = Math.cos(a) * r * stretchX;
    o[1] = y + Math.sin(t * 0.4 + i) * 6;
    o[2] = Math.sin(a) * r;
  }
  function lNebula() { return -1; }

  // 1 · DNA HELIX — two strands + rungs, rotating
  function fHelix(i, t, o) {
    var per = Math.floor(N * 0.42);          // per strand
    var rungs = N - per * 2;
    var rot = t * 0.5;
    var rad = R * 0.42, height = R * 2.2;
    if (i < per * 2) {
      var strand = i % 2, k = Math.floor(i / 2) / per;
      var ang = k * Math.PI * 4 + rot + strand * Math.PI;
      o[0] = Math.cos(ang) * rad;
      o[1] = (k - 0.5) * height;
      o[2] = Math.sin(ang) * rad;
    } else {
      var j = i - per * 2;
      var kk = (j / rungs);
      var seg = Math.floor(kk * 10) / 10 + 0.05;   // 10 rungs
      var across = (kk * 10) % 1;                   // position across rung
      var ang2 = seg * Math.PI * 4 + rot;
      var x1 = Math.cos(ang2) * rad, z1 = Math.sin(ang2) * rad;
      var x2 = Math.cos(ang2 + Math.PI) * rad, z2 = Math.sin(ang2 + Math.PI) * rad;
      o[0] = x1 + (x2 - x1) * across;
      o[1] = (seg - 0.5) * height;
      o[2] = z1 + (z2 - z1) * across;
    }
  }
  function lHelix(i) {
    var per = Math.floor(N * 0.42);
    if (i < per * 2 - 2) return i + 2;  // along each strand
    return -1;
  }

  // 2 · DATA GRID — undulating plane of nodes
  var gCols = 0, gRows = 0;
  function gridDims() {
    gCols = Math.ceil(Math.sqrt(N * (W / Math.max(H, 1))));
    gRows = Math.ceil(N / gCols);
  }
  function fGrid(i, t, o) {
    var cx = i % gCols, cy = Math.floor(i / gCols);
    var sx = (cx / (gCols - 1) - 0.5) * R * 2.6;
    var sz = (cy / (gRows - 1) - 0.5) * R * 2.2;
    o[0] = sx;
    o[1] = R * 0.25 + Math.sin(sx * 0.012 + t * 1.4) * Math.cos(sz * 0.012 + t) * R * 0.16;
    o[2] = sz;
  }
  function lGrid(i) {
    return (i % gCols) < gCols - 1 ? i + 1 : -1;
  }

  // 3 · GLOBE — fibonacci sphere, rotating
  var GA = Math.PI * (3 - Math.sqrt(5));
  function fGlobe(i, t, o) {
    var k = (i + 0.5) / N;
    var y = 1 - 2 * k;
    var rr = Math.sqrt(Math.max(0, 1 - y * y));
    var th = GA * i + t * 0.25;
    var rad = R * 0.85;
    o[0] = Math.cos(th) * rr * rad;
    o[1] = y * rad;
    o[2] = Math.sin(th) * rr * rad;
  }
  function lGlobe(i) { return i < N - 1 ? i + 1 : -1; }

  // 4 · ORBITS — three tilted rings + core
  function fOrbits(i, t, o) {
    var core = Math.floor(N * 0.12);
    if (i < core) {                       // core cluster
      var a = rnd1[i] * Math.PI * 2, b = rnd2[i] * Math.PI;
      var r = rnd3[i] * R * 0.16;
      o[0] = Math.sin(b) * Math.cos(a) * r;
      o[1] = Math.cos(b) * r;
      o[2] = Math.sin(b) * Math.sin(a) * r;
      return;
    }
    var j = i - core, ring = j % 3;
    var k = (Math.floor(j / 3) / ((N - core) / 3));
    var ang = k * Math.PI * 2 + t * (0.35 + ring * 0.12);
    var rad = R * (0.55 + ring * 0.22);
    var x = Math.cos(ang) * rad, z = Math.sin(ang) * rad, y = 0;
    var tilt = (ring - 1) * 0.9;
    o[0] = x;
    o[1] = y * Math.cos(tilt) - z * Math.sin(tilt) * 0.6;
    o[2] = y * Math.sin(tilt) + z * Math.cos(tilt);
  }
  function lOrbits(i) {
    var core = Math.floor(N * 0.12);
    if (i < core) return -1;
    var j = i - core;
    return (i + 3 < N) && (j % 3 === (j + 3) % 3) ? i + 3 : -1;
  }

  // 5 · VORTEX — converging spiral, breathing
  function fVortex(i, t, o) {
    var k = i / N;
    var pulse = 1 + Math.sin(t * 1.6) * 0.08;
    var ang = k * Math.PI * 7 + t * 0.6;
    var rad = (0.12 + k * 0.95) * R * pulse;
    o[0] = Math.cos(ang) * rad;
    o[1] = (k - 0.5) * R * 0.5 * Math.sin(t * 0.8 + k * 6);
    o[2] = Math.sin(ang) * rad;
  }
  function lVortex(i) { return i < N - 1 ? i + 1 : -1; }

  var FORMS = [
    { f: fNebula, l: lNebula },
    { f: fHelix,  l: lHelix  },
    { f: fGrid,   l: lGrid   },
    { f: fGlobe,  l: lGlobe  },
    { f: fOrbits, l: lOrbits },
    { f: fVortex, l: lVortex }
  ];

  /* ---------------- engine ---------------- */
  function resize() {
    W = window.innerWidth;
    H = window.innerHeight;
    CX = W / 2; CY = H / 2;
    R = Math.min(W, H) * 0.36;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    N = Math.max(160, Math.min(320, Math.floor((W * H) / 4200)));
    gridDims();
    spawnStars();
    if (px.length !== N) {
      px = []; py = []; pz = [];
      var o = [0, 0, 0];
      for (var i = 0; i < N; i++) {
        fNebula(i, 0, o);
        px.push(o[0]); py.push(o[1]); pz.push(o[2]);
      }
    }
  }

  var ta = [0, 0, 0], tb = [0, 0, 0];
  var sx = [], sy = [], sd = [];   // projected

  function smooth(a, b, f) { return a + (b - a) * f; }
  function ease(x) { return x * x * (3 - 2 * x); }

  function step(now) {
    if (!running) return;
    time = now * 0.001 * SPEED;

    // chase the scroll phase softly
    phaseS += (phase - phaseS) * 0.06;
    var pi = Math.max(0, Math.min(FORMS.length - 1, Math.floor(phaseS)));
    var pj = Math.min(FORMS.length - 1, pi + 1);
    var f = ease(Math.min(1, Math.max(0, phaseS - pi)));

    var A = FORMS[pi], B = FORMS[pj];
    var ca = COLORS[pi], cb = COLORS[pj];
    var r = Math.round(smooth(ca[0], cb[0], f));
    var g = Math.round(smooth(ca[1], cb[1], f));
    var b = Math.round(smooth(ca[2], cb[2], f));

    ctx.clearRect(0, 0, W, H);

    /* ---- layer 1: living starfield, edge to edge ---- */
    var st, twk;
    for (var si = 0; si < stars.length; si++) {
      st = stars[si];
      st.x += st.vx * SPEED;
      st.y += st.vy * SPEED;
      if (st.x < -4) st.x = W + 4; else if (st.x > W + 4) st.x = -4;
      if (st.y < -4) st.y = H + 4; else if (st.y > H + 4) st.y = -4;
      twk = st.base * (0.55 + 0.45 * Math.sin(time * 2.4 + st.tw));
      ctx.fillStyle = "rgba(" + r + "," + g + "," + b + "," + twk.toFixed(3) + ")";
      ctx.beginPath();
      ctx.arc(st.x, st.y, st.r, 0, 6.2832);
      ctx.fill();
    }

    var i, X, Y, Z, s;
    for (i = 0; i < N; i++) {
      A.f(i, time, ta);
      if (f > 0.001) {
        B.f(i, time, tb);
        ta[0] = smooth(ta[0], tb[0], f);
        ta[1] = smooth(ta[1], tb[1], f);
        ta[2] = smooth(ta[2], tb[2], f);
      }
      // chase target (gives fluid, organic morphing)
      px[i] += (ta[0] - px[i]) * 0.085;
      py[i] += (ta[1] - py[i]) * 0.085;
      pz[i] += (ta[2] - pz[i]) * 0.085;

      Z = pz[i];
      s = FOV / (FOV + Z + R * 1.6);
      X = CX + px[i] * s;
      Y = CY + py[i] * s;
      sx[i] = X; sy[i] = Y; sd[i] = s;
    }

    // structural links (O(n), cheap)
    ctx.lineWidth = 1;
    var li, lf;
    for (i = 0; i < N; i++) {
      li = A.l(i);
      if (li >= 0 && li < N) {
        lf = 0.10 * sd[i] * (1 - f * 0.6);
        ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + "," + lf.toFixed(3) + ")";
        ctx.beginPath();
        ctx.moveTo(sx[i], sy[i]);
        ctx.lineTo(sx[li], sy[li]);
        ctx.stroke();
      }
      if (f > 0.35) {
        li = B.l(i);
        if (li >= 0 && li < N) {
          lf = 0.10 * sd[i] * f;
          ctx.strokeStyle = "rgba(" + r + "," + g + "," + b + "," + lf.toFixed(3) + ")";
          ctx.beginPath();
          ctx.moveTo(sx[i], sy[i]);
          ctx.lineTo(sx[li], sy[li]);
          ctx.stroke();
        }
      }
    }

    // points
    for (i = 0; i < N; i++) {
      s = sd[i];
      var rad = (0.7 + rnd1[i] * 1.3) * s;
      var alpha = 0.22 + s * 0.5;
      ctx.fillStyle = "rgba(" + r + "," + g + "," + b + "," + Math.min(0.85, alpha).toFixed(3) + ")";
      ctx.beginPath();
      ctx.arc(sx[i], sy[i], rad, 0, 6.2832);
      ctx.fill();
    }

    requestAnimationFrame(step);
  }

  /* ---------------- public API ---------------- */
  window.MORPH = {
    setPhase: function (p) {
      phase = Math.max(0, Math.min(FORMS.length - 1, p));
    }
  };

  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", function () {
    var was = running;
    running = !document.hidden;
    if (running && !was) requestAnimationFrame(step);
  });

  resize();
  requestAnimationFrame(step);
})();
