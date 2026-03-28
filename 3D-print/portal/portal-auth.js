/**
 * 3D Print Academy — Portal Auth & Admin Bypass
 * Shared across all portal pages (index, module-1..6)
 *
 * Admin emails bypass the course purchase check (full access to all modules).
 */
(function () {
  'use strict';

  var ADMIN_EMAILS = [
    'ajayadesign@gmail.com'
  ];

  var app = firebase.initializeApp(window.__firebaseConfig);
  var auth = firebase.auth();
  var db = firebase.database();

  function isAdmin(email) {
    return ADMIN_EMAILS.indexOf(email) !== -1;
  }

  /* ── Portal Dashboard (index.html) ── */
  function initDashboard() {
    var $login = document.getElementById('login-screen');
    var $dash = document.getElementById('dashboard');
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
        $signout.classList.add('hidden');
        return;
      }

      // Admin bypass — skip purchase check
      if (isAdmin(user.email)) {
        showDashboard(user, { tier: 'admin', progress: {} });
        return;
      }

      // Regular student — check enrollment in RTDB
      db.ref('courses/' + user.uid).once('value').then(function (snap) {
        var data = snap.val();
        if (!data || !data.tier) {
          $error.textContent = 'No active enrollment found for ' + user.email + '. Please enroll first.';
          $error.classList.remove('hidden');
          auth.signOut();
          return;
        }
        showDashboard(user, data);
      });
    });

    function showDashboard(user, data) {
      $login.classList.add('hidden');
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
      $progressBar.style.width = Math.round((completed / 6) * 100) + '%';
      $progressText.textContent = completed + ' / 6 modules';
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

      db.ref('courses/' + u.uid).once('value').then(function (s) {
        var d = s.val();
        if (!d || !d.tier) return window.location.href = '/3D-print/portal/';
        grantAccess(moduleId, d);
      });
    });

    document.getElementById('mark-complete').addEventListener('click', function () {
      var u = auth.currentUser;
      if (!u) return;
      db.ref('courses/' + u.uid + '/progress/' + moduleId).set(true).then(function () {
        document.getElementById('complete-icon').textContent = '✓';
        document.getElementById('mark-complete').classList.add('opacity-50');
      });
    });
  }

  function grantAccess(moduleId, data) {
    document.getElementById('auth-gate').classList.add('hidden');
    document.getElementById('module-content').classList.remove('hidden');
    if (data.progress && data.progress[moduleId]) {
      document.getElementById('complete-icon').textContent = '✓';
      document.getElementById('mark-complete').classList.add('opacity-50');
    }
  }

  /* ── Public API ── */
  window.PortalAuth = {
    initDashboard: initDashboard,
    initModule: initModule
  };
})();
