/**
 * 3D Print Academy — Portal Auth v2 (Admin-Approved Access)
 *
 * Security model:
 *   1. User signs in with Google OAuth
 *   2. JS checks /approved_users/{uid} in Firebase RTDB
 *   3. If approved → grant access (show dashboard / module content)
 *   4. If NOT approved → auto-register in /pending_users/{uid}, show "pending" screen
 *   5. Admin (ajayadesign@gmail.com) approves via /3D-print/portal/admin.html
 *
 * RTDB Security Rules enforce:
 *   - Only admin can write to /approved_users/
 *   - Users can write to /pending_users/{own_uid} ONCE (no self-elevation)
 *   - Users can only read their own records
 *   - Progress tracking is scoped to own uid
 *
 * See FIREBASE_RULES.md for the rules JSON to deploy.
 */
(function () {
  'use strict';

  var ADMIN_EMAIL = 'ajayadesign@gmail.com';

  // Tier → allowed content map (what each pricing tier can access)
  var TIER_ACCESS = {
    admin:   { modules: [1,2,3,4,5,6], downloads: true },
    bundle:  { modules: [1,2,3,4,5,6], downloads: true },
    course:  { modules: [1,2,3,4,5,6], downloads: true },
    session: { modules: [],             downloads: false },
    stl:     { modules: [],             downloads: true }
  };

  var app = firebase.initializeApp(window.__firebaseConfig);
  var auth = firebase.auth();
  var db = firebase.database();

  function isAdmin(email) {
    return email === ADMIN_EMAIL;
  }

  /** Check if a tier grants access to a specific module/page */
  function tierAllows(tier, moduleId) {
    var access = TIER_ACCESS[tier] || TIER_ACCESS['stl'];
    if (moduleId === 'downloads') return access.downloads;
    var num = parseInt(moduleId.replace('module-', ''), 10);
    return access.modules.indexOf(num) !== -1;
  }

  /* ── Portal Dashboard (index.html) ── */
  function initDashboard() {
    var $login = document.getElementById('login-screen');
    var $dash = document.getElementById('dashboard');
    var $pending = document.getElementById('pending-screen');
    var $error = document.getElementById('login-error');
    var $signout = document.getElementById('signout-btn');
    var $userName = document.getElementById('user-name');
    var $userTier = document.getElementById('user-tier');
    var $progressBar = document.getElementById('progress-bar');
    var $progressText = document.getElementById('progress-text');

    document.getElementById('google-signin').addEventListener('click', function () {
      auth.signInWithPopup(new firebase.auth.GoogleAuthProvider());
    });

    $signout.addEventListener('click', function () {
      auth.signOut();
    });

    auth.onAuthStateChanged(function (user) {
      if (!user) {
        $login.classList.remove('hidden');
        $dash.classList.add('hidden');
        if ($pending) $pending.classList.add('hidden');
        $signout.classList.add('hidden');
        return;
      }

      // Admin bypass — full access
      if (isAdmin(user.email)) {
        showDashboard(user, { tier: 'admin', progress: {} });
        return;
      }

      // Check if user is approved
      db.ref('approved_users/' + user.uid).once('value').then(function (snap) {
        var data = snap.val();
        if (data && data.tier) {
          // Approved student — load progress and show dashboard
          db.ref('courses/' + user.uid + '/progress').once('value').then(function (progSnap) {
            data.progress = progSnap.val() || {};
            showDashboard(user, data);
          });
          return;
        }

        // Not approved — register as pending and show waiting screen
        registerPending(user);
        showPending(user);
      });
    });

    function showDashboard(user, data) {
      $login.classList.add('hidden');
      if ($pending) $pending.classList.add('hidden');
      $dash.classList.remove('hidden');
      $signout.classList.remove('hidden');
      $userName.textContent = user.displayName ? user.displayName.split(' ')[0] : 'Student';
      $userTier.textContent = data.tier;

      var progress = data.progress || {};
      var completed = 0;
      for (var i = 1; i <= 6; i++) {
        if (progress['module-' + i]) {
          completed++;
          var check = document.getElementById('check-' + i);
          if (check) check.classList.remove('hidden');
        }
      }
      if ($progressBar) $progressBar.style.width = Math.round((completed / 6) * 100) + '%';
      if ($progressText) $progressText.textContent = completed + ' / 6 modules';
    }

    function showPending(user) {
      $login.classList.add('hidden');
      $dash.classList.add('hidden');
      $signout.classList.remove('hidden');
      if ($pending) {
        $pending.classList.remove('hidden');
        var $pendingEmail = document.getElementById('pending-email');
        if ($pendingEmail) $pendingEmail.textContent = user.email;
      }
    }
  }

  /* ── Module Pages (module-1..6) ── */
  function initModule(moduleId) {
    auth.onAuthStateChanged(function (u) {
      if (!u) return window.location.href = '/3D-print/portal/';

      // Admin bypass
      if (isAdmin(u.email)) {
        grantAccess(moduleId, { progress: {} });
        return;
      }

      // Check approval + tier-based access
      db.ref('approved_users/' + u.uid).once('value').then(function (s) {
        var d = s.val();
        if (!d || !d.tier) return window.location.href = '/3D-print/portal/';

        // Tier gate: check if this tier can access this module
        if (!tierAllows(d.tier, moduleId)) {
          return window.location.href = '/3D-print/portal/?upgrade=true';
        }

        // Load progress
        db.ref('courses/' + u.uid + '/progress').once('value').then(function (ps) {
          var prog = ps.val() || {};
          grantAccess(moduleId, { progress: prog });
        });
      });
    });

    // Mark-complete only for valid module IDs (not downloads)
    var $markBtn = document.getElementById('mark-complete');
    if ($markBtn && /^module-[1-6]$/.test(moduleId)) {
      $markBtn.addEventListener('click', function () {
        var u = auth.currentUser;
        if (!u) return;
        db.ref('courses/' + u.uid + '/progress/' + moduleId).set(true).then(function () {
          document.getElementById('complete-icon').textContent = '✓';
          $markBtn.classList.add('opacity-50');
        });
      });
    } else if ($markBtn) {
      // Hide mark-complete on non-module pages (downloads)
      $markBtn.style.display = 'none';
    }
  }

  function grantAccess(moduleId, data) {
    document.getElementById('auth-gate').classList.add('hidden');
    document.getElementById('module-content').classList.remove('hidden');
    if (data.progress && data.progress[moduleId]) {
      document.getElementById('complete-icon').textContent = '✓';
      document.getElementById('mark-complete').classList.add('opacity-50');
    }
  }

  /* ── Register user as pending (write-once to /pending_users/{uid}) ── */
  function registerPending(user) {
    // Atomic write — RTDB rule (!data.exists()) prevents overwrites server-side.
    // No read-then-write race: just attempt the set; if the record exists, the rule rejects it.
    db.ref('pending_users/' + user.uid).set({
      email: user.email,
      name: user.displayName || '',
      photo: user.photoURL || '',
      requested_at: firebase.database.ServerValue.TIMESTAMP
    }).catch(function () {
      // Expected: PERMISSION_DENIED if record already exists (write-once rule)
    });
  }

  /* ── Admin Panel ── */
  function initAdmin() {
    auth.onAuthStateChanged(function (user) {
      if (!user || !isAdmin(user.email)) {
        document.getElementById('admin-gate').innerHTML =
          '<p class="text-amd-red-text font-mono text-sm">Access denied. Admin only.</p>';
        return;
      }
      document.getElementById('admin-gate').classList.add('hidden');
      document.getElementById('admin-panel').classList.remove('hidden');
      document.getElementById('admin-signout').classList.remove('hidden');

      document.getElementById('admin-signout').addEventListener('click', function () {
        auth.signOut().then(function () { window.location.reload(); });
      });

      loadPendingUsers();
      loadApprovedUsers();
    });
  }

  function loadPendingUsers() {
    var $list = document.getElementById('pending-list');
    db.ref('pending_users').on('value', function (snap) {
      var data = snap.val();
      if (!data) {
        $list.innerHTML = '<p class="text-gray-500 text-sm font-mono">No pending requests.</p>';
        return;
      }
      var html = '';
      Object.keys(data).forEach(function (uid) {
        var u = data[uid];
        var safeUid = escapeAttr(uid);
        var date = u.requested_at ? new Date(u.requested_at).toLocaleDateString() : '—';
        html += '<div class="flex items-center justify-between p-4 rounded-xl bg-surface border border-border-dim mb-3">'
          + '<div class="flex items-center gap-3">'
          + (u.photo ? '<img src="' + escapeAttr(u.photo) + '" class="w-10 h-10 rounded-full" alt="" />' : '<div class="w-10 h-10 rounded-full bg-surface-card flex items-center justify-center text-gray-500">?</div>')
          + '<div>'
          + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(u.name || 'Unknown') + '</p>'
          + '<p class="text-gray-500 text-xs">' + escapeHtml(u.email) + ' &bull; Requested: ' + escapeHtml(date) + '</p>'
          + '</div></div>'
          + '<div class="flex items-center gap-2">'
          + '<select data-uid="' + safeUid + '" class="admin-tier bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim">'
          + '<option value="stl">STL Pack</option>'
          + '<option value="course" selected>Full Course</option>'
          + '<option value="session">1-on-1 Session</option>'
          + '<option value="bundle">Complete Bundle</option>'
          + '</select>'
          + '<input data-uid="' + safeUid + '" class="admin-payref bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim w-28" placeholder="Payment ref" />'
          + '<button data-uid="' + safeUid + '" data-action="approve" class="admin-action px-3 py-1 bg-neon-green/20 text-neon-green text-xs font-mono font-bold rounded hover:bg-neon-green/30 transition-colors">Approve</button>'
          + '<button data-uid="' + safeUid + '" data-action="deny" class="admin-action px-3 py-1 bg-amd-red/20 text-amd-red-text text-xs font-mono font-bold rounded hover:bg-amd-red/30 transition-colors">Deny</button>'
          + '</div></div>';
      });
      $list.innerHTML = html;
    });
  }

  function loadApprovedUsers() {
    var $list = document.getElementById('approved-list');
    db.ref('approved_users').on('value', function (snap) {
      var data = snap.val();
      if (!data) {
        $list.innerHTML = '<p class="text-gray-500 text-sm font-mono">No approved users yet.</p>';
        return;
      }
      var html = '';
      Object.keys(data).forEach(function (uid) {
        var u = data[uid];
        var safeUid = escapeAttr(uid);
        var date = u.approved_at ? new Date(u.approved_at).toLocaleDateString() : '—';
        html += '<div class="flex items-center justify-between p-4 rounded-xl bg-surface border border-border-dim mb-3">'
          + '<div>'
          + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(u.name || u.email) + '</p>'
          + '<p class="text-gray-500 text-xs">' + escapeHtml(u.email) + ' &bull; Tier: <span class="text-neon-green">' + escapeHtml(u.tier) + '</span> &bull; Approved: ' + escapeHtml(date) + (u.payment_ref ? ' &bull; Ref: ' + escapeHtml(u.payment_ref) : '') + '</p>'
          + '</div>'
          + '<button data-uid="' + safeUid + '" data-action="revoke" class="admin-action px-3 py-1 bg-amd-red/20 text-amd-red-text text-xs font-mono font-bold rounded hover:bg-amd-red/30 transition-colors">Revoke</button>'
          + '</div>';
      });
      $list.innerHTML = html;
    });
  }

  function approveUser(uid) {
    var tierEl = document.querySelector('.admin-tier[data-uid="' + uid + '"]');
    var payEl = document.querySelector('.admin-payref[data-uid="' + uid + '"]');
    if (!tierEl || !payEl) return;
    var tier = tierEl.value;
    var payRef = payEl.value.trim();
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;

    // Read pending data first
    db.ref('pending_users/' + uid).once('value').then(function (snap) {
      var pending = snap.val();
      if (!pending) return;

      // Write to approved_users
      db.ref('approved_users/' + uid).set({
        email: pending.email,
        name: pending.name || '',
        tier: tier,
        approved_at: firebase.database.ServerValue.TIMESTAMP,
        approved_by: user.uid,
        payment_ref: payRef || ''
      }).then(function () {
        // Remove from pending
        db.ref('pending_users/' + uid).remove();
      });
    });
  }

  function denyUser(uid) {
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;
    db.ref('pending_users/' + uid).remove();
  }

  function revokeUser(uid) {
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;
    if (!confirm('Revoke access for this user?')) return;
    db.ref('approved_users/' + uid).remove();
  }

  /* ── Helpers ── */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ── Event delegation for admin panel (no inline onclick — prevents XSS) ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.admin-action');
    if (!btn) return;
    var uid = btn.getAttribute('data-uid');
    var action = btn.getAttribute('data-action');
    if (!uid || !action) return;
    if (action === 'approve') approveUser(uid);
    else if (action === 'deny') denyUser(uid);
    else if (action === 'revoke') revokeUser(uid);
  });

  /* ── Public API ── */
  window.PortalAuth = {
    initDashboard: initDashboard,
    initModule: initModule,
    initAdmin: initAdmin
  };
})();
