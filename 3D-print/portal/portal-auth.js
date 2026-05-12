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

  var LESSON_COUNTS = { 1: 7, 2: 7, 3: 7, 4: 8, 5: 7, 6: 7 };
  var TOTAL_LESSONS = 43;

  var CALENDLY_URL = 'https://calendly.com/ajayadesign/30min';

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

  /* ── Helpers for auth error messages ── */
  function authErrorMessage(code) {
    var messages = {
      'auth/email-already-in-use': 'An account with this email already exists. Try signing in instead.',
      'auth/invalid-email': 'Please enter a valid email address.',
      'auth/weak-password': 'Password must be at least 6 characters.',
      'auth/user-not-found': 'No account found with this email. Try signing up instead.',
      'auth/wrong-password': 'Incorrect password. Try again or reset your password.',
      'auth/invalid-credential': 'Incorrect email or password. Try again or reset your password.',
      'auth/too-many-requests': 'Too many attempts. Please wait a moment and try again.',
      'auth/popup-blocked': 'Popup was blocked. Trying redirect sign-in instead...',
      'auth/popup-closed-by-user': 'Sign-in popup was closed. Please try again.',
      'auth/cancelled-popup-request': 'Sign-in was cancelled. Please try again.',
      'auth/operation-not-allowed': 'This sign-in method is not enabled. Please contact support.',
      'auth/network-request-failed': 'Network error. Please check your connection and try again.',
      'auth/unauthorized-domain': 'This domain is not authorized for sign-in. Please contact support.',
      'auth/internal-error': 'An internal error occurred. Please try again.',
      'auth/user-disabled': 'This account has been disabled. Please contact support.',
    };
    return messages[code] || 'Sign-in failed (' + code + '). Please try again.';
  }

  function showError($el, msg) {
    if (!$el) return;
    $el.textContent = msg;
    $el.classList.remove('hidden');
  }

  function hideError($el) {
    if (!$el) return;
    $el.textContent = '';
    $el.classList.add('hidden');
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

    // Handle ?success=true from Stripe redirect
    var urlParams = new URLSearchParams(window.location.search);
    var isPostPayment = urlParams.get('success') === 'true';
    var $successBanner = document.getElementById('payment-success-banner');
    if (isPostPayment && $successBanner) {
      $successBanner.classList.remove('hidden');
    }

    // Google sign-in: popup first, fallback to redirect
    var $googleBtn = document.getElementById('google-signin');
    if ($googleBtn) {
      $googleBtn.addEventListener('click', function () {
        hideError($error);
        var provider = new firebase.auth.GoogleAuthProvider();
        // Try popup first on ALL devices, fall back to redirect if blocked
        auth.signInWithPopup(provider).then(function(result) {
          console.log('Popup sign-in successful:', result.user.email);
        }).catch(function (err) {
          console.error('Google sign-in error:', err.code, err.message);
          var dbg = document.getElementById('auth-debug');
          if (dbg) { dbg.textContent = 'POPUP ERROR: ' + err.code + ' — trying redirect...'; dbg.style.color = '#FFD700'; }
          if (err.code === 'auth/popup-blocked' || err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
            auth.signInWithRedirect(provider);
          } else {
            showError($error, authErrorMessage(err.code));
          }
        });
      });
    }

    // Handle redirect result (for mobile fallback)
    auth.getRedirectResult().then(function(result) {
      if (result && result.user) {
        console.log('Redirect sign-in successful:', result.user.email);
      }
      var dbg = document.getElementById('auth-debug');
      if (dbg) dbg.textContent = 'Redirect result: ' + (result && result.user ? result.user.email : 'no user returned') + ' | credential: ' + (result && result.credential ? 'yes' : 'none');
    }).catch(function (err) {
      console.error('Redirect sign-in error:', err.code, err.message, err);
      var dbg = document.getElementById('auth-debug');
      if (dbg) { dbg.textContent = 'REDIRECT ERROR: ' + err.code + ' — ' + err.message; dbg.style.color = '#FF6B6B'; }
      if (err.code && err.code !== 'auth/popup-closed-by-user') {
        showError($error, authErrorMessage(err.code));
      }
    });

    // Email/password sign-in
    var $emailForm = document.getElementById('email-auth-form');
    var $emailInput = document.getElementById('email-input');
    var $passwordInput = document.getElementById('password-input');
    var $emailSubmit = document.getElementById('email-submit');
    var $emailToggle = document.getElementById('email-toggle');
    var $emailError = document.getElementById('email-error');
    var $forgotPassword = document.getElementById('forgot-password');
    var isSignUp = false;

    if ($emailToggle) {
      $emailToggle.addEventListener('click', function (e) {
        e.preventDefault();
        isSignUp = !isSignUp;
        $emailSubmit.textContent = isSignUp ? 'Create Account' : 'Sign In';
        $emailToggle.textContent = isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up";
        if ($forgotPassword) $forgotPassword.classList.toggle('hidden', isSignUp);
        hideError($emailError);
      });
    }

    if ($emailForm) {
      $emailForm.addEventListener('submit', function (e) {
        e.preventDefault();
        hideError($emailError);
        var email = ($emailInput.value || '').trim();
        var password = ($passwordInput.value || '').trim();
        if (!email || !password) {
          showError($emailError, 'Please enter both email and password.');
          return;
        }

        if (isSignUp) {
          auth.createUserWithEmailAndPassword(email, password).then(function (cred) {
            // Send verification email
            if (cred.user) {
              cred.user.sendEmailVerification().catch(function () { /* best effort */ });
            }
          }).catch(function (err) {
            showError($emailError, authErrorMessage(err.code));
          });
        } else {
          auth.signInWithEmailAndPassword(email, password).catch(function (err) {
            showError($emailError, authErrorMessage(err.code));
          });
        }
      });
    }

    // Forgot password
    if ($forgotPassword) {
      $forgotPassword.addEventListener('click', function (e) {
        e.preventDefault();
        var email = ($emailInput.value || '').trim();
        if (!email) {
          showError($emailError, 'Enter your email above, then click "Forgot password?"');
          return;
        }
        auth.sendPasswordResetEmail(email).then(function () {
          showError($emailError, ''); // clear
          $emailError.classList.remove('hidden');
          $emailError.innerHTML = '<span class="text-neon-green">Password reset email sent! Check your inbox.</span>';
        }).catch(function (err) {
          showError($emailError, authErrorMessage(err.code));
        });
      });
    }

    $signout.addEventListener('click', function () {
      auth.signOut();
    });

    auth.onAuthStateChanged(function (user) {
      console.log('AUTH STATE CHANGED:', user ? user.email : 'NO USER', user ? user.uid : '');
      if (!user) {
        console.log('No user — showing login screen');
        $login.classList.remove('hidden');
        $dash.classList.add('hidden');
        if ($pending) $pending.classList.add('hidden');
        $signout.classList.add('hidden');
        return;
      }

      console.log('User signed in:', user.email, 'isAdmin:', isAdmin(user.email));

      // Admin bypass — full access + command center
      if (isAdmin(user.email)) {
        showDashboard(user, { tier: 'admin', progress: {} });
        initAdminCommandCenter();
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

        // Not approved yet — check pre_approved by email (covers Stripe pre-pay + manual approvals)
        db.ref('pre_approved').orderByChild('email').equalTo(user.email).once('value').then(function(preSnap) {
          var preData = preSnap.val();
          if (preData) {
            // Found a pre_approved entry — auto-approve now
            var preKey = Object.keys(preData)[0];
            var pre = preData[preKey];
            db.ref('approved_users/' + user.uid).set({
              email: user.email,
              name: user.displayName || '',
              tier: pre.tier || 'course',
              approved_at: firebase.database.ServerValue.TIMESTAMP,
              stripe_session: pre.stripe_session || '',
              manual: !!pre.manual,
              sessions_remaining: pre.sessions_remaining !== undefined ? pre.sessions_remaining : (pre.tier === 'bundle' ? 2 : pre.tier === 'session' ? 1 : 0)
            }).then(function() {
              db.ref('pre_approved/' + preKey).remove();
              db.ref('pending_users/' + user.uid).remove();
              db.ref('courses/' + user.uid + '/progress').once('value').then(function(progSnap) {
                showDashboard(user, { tier: pre.tier || 'course', progress: progSnap.val() || {} });
              });
            }).catch(function(err) {
              // approved_users write denied (expected — only admin can write)
              // Fall through to pending registration
              console.warn('Auto-approve write failed (expected if not admin):', err.code);
              registerPending(user);
              showPending(user);
            });
            return;
          }

          // No pre_approved match — register as pending and wait
          registerPending(user);
          showPending(user);

          // Listen for admin approval
          db.ref('approved_users/' + user.uid).on('value', function (liveSnap) {
            var liveData = liveSnap.val();
            if (liveData && liveData.tier) {
              db.ref('approved_users/' + user.uid).off('value');
              db.ref('courses/' + user.uid + '/progress').once('value').then(function (progSnap) {
                liveData.progress = progSnap.val() || {};
                showDashboard(user, liveData);
              });
            }
          });
        }).catch(function(err) {
          // pre_approved read denied (RTDB rules only allow admin to read pre_approved)
          // Fall through gracefully to pending registration
          console.warn('pre_approved query denied (expected for non-admin):', err.code);
          registerPending(user);
          showPending(user);

          // Listen for admin approval
          db.ref('approved_users/' + user.uid).on('value', function (liveSnap) {
            var liveData = liveSnap.val();
            if (liveData && liveData.tier) {
              db.ref('approved_users/' + user.uid).off('value');
              db.ref('courses/' + user.uid + '/progress').once('value').then(function (progSnap) {
                liveData.progress = progSnap.val() || {};
                showDashboard(user, liveData);
              });
            }
          });
        });
      }).catch(function(err) {
        // approved_users read failed — show error to user
        console.error('Failed to check approval status:', err);
        showError($error, 'Unable to verify your account. Please try again or contact support.');
      });
    });

    function initCalendlyEmbed(user, $container, $btn) {
      if (!$container) return;
      // Smooth-show the embed area
      $container.style.minHeight = '660px';
      if ($btn) {
        $btn.addEventListener('click', function(e) {
          e.preventDefault();
          $container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      }
      // Prefill name + email from Firebase user
      var prefill = '';
      if (user.email) prefill += '&email=' + encodeURIComponent(user.email);
      if (user.displayName) prefill += '&name=' + encodeURIComponent(user.displayName);
      $container.innerHTML = '<iframe src="' + CALENDLY_URL + '?embed_type=Inline&embed_domain=' + location.hostname + prefill
        + '" width="100%" height="660" frameborder="0" title="Schedule your 1-on-1 session" style="border-radius:12px"></iframe>';
    }

    function showDashboard(user, data) {
      $login.classList.add('hidden');
      if ($pending) $pending.classList.add('hidden');
      $dash.classList.remove('hidden');
      $signout.classList.remove('hidden');
      $userName.textContent = user.displayName ? user.displayName.split(' ')[0] : (user.email ? user.email.split('@')[0] : 'Student');
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
      var lessonsDone = 0;
      Object.keys(progress).forEach(function(k) {
        if (k.indexOf('lesson-') === 0 && progress[k]) lessonsDone++;
      });
      if ($progressBar) $progressBar.style.width = Math.round((completed / 6) * 100) + '%';
      if ($progressText) $progressText.textContent = completed + ' / 6 modules' + (lessonsDone > 0 ? ' \u00B7 ' + lessonsDone + '/' + TOTAL_LESSONS + ' lessons' : '');

      // Certificate of completion — show when all 6 modules done
      if (completed === 6) {
        showCertificate(user, data);
      }

      // Per-module lesson progress on cards
      for (var m = 1; m <= 6; m++) {
        var card = document.getElementById('mod-' + m);
        if (!card) continue;
        var mLessons = LESSON_COUNTS[m] || 7;
        var mDone = 0;
        for (var l = 1; l <= mLessons; l++) {
          if (progress['lesson-' + m + '-' + l]) mDone++;
        }
        if (mDone > 0) {
          var sub = card.querySelector('.text-gray-500.text-xs');
          if (sub) sub.textContent += ' \u00B7 ' + mDone + '/' + mLessons + ' lessons';
        }
      }

      // Show booking section for session/bundle tiers
      var $booking = document.getElementById('booking-section');
      if ($booking && (data.tier === 'session' || data.tier === 'bundle' || data.tier === 'admin')) {
        $booking.classList.remove('hidden');
        // Show session status
        var sessRemain = data.sessions_remaining;
        var sessBooked = data.session_booked;
        var sessCompleted = data.session_completed;
        var sessDate = data.session_date;
        var $bookingTitle = $booking.querySelector('h2');
        var $bookingDesc = $booking.querySelector('p');
        var $bookingBtn = document.getElementById('booking-btn');
        var $calendlyEmbed = document.getElementById('calendly-embed');
        if (sessCompleted && (!sessRemain || sessRemain <= 0)) {
          if ($bookingTitle) $bookingTitle.textContent = '1-on-1 Session Complete \u2713';
          if ($bookingDesc) $bookingDesc.textContent = 'Session completed' + (sessDate ? ' on ' + sessDate : '') + '. All sessions used.';
          if ($bookingBtn) { $bookingBtn.textContent = 'All Done!'; $bookingBtn.classList.add('opacity-50', 'pointer-events-none'); }
          $booking.querySelector('.rounded-2xl').classList.remove('border-electric-blue/30'); $booking.querySelector('.rounded-2xl').classList.add('border-neon-green/30');
        } else if (sessBooked && sessDate) {
          if ($bookingTitle) $bookingTitle.textContent = '\uD83D\uDCC5 Session Scheduled';
          if ($bookingDesc) $bookingDesc.textContent = 'Your session is booked for ' + sessDate + '. You\u2019ll receive a calendar invite with the meeting link.' + (sessRemain > 0 ? ' ' + sessRemain + ' session(s) remaining after this.' : '');
          if ($bookingBtn) { $bookingBtn.textContent = 'Scheduled \u2713'; $bookingBtn.classList.add('opacity-50', 'pointer-events-none'); }
        } else {
          // Show Calendly inline embed
          initCalendlyEmbed(user, $calendlyEmbed, $bookingBtn);
        }
      }
    }

    function showPending(user) {
      $login.classList.add('hidden');
      $dash.classList.add('hidden');
      $signout.classList.remove('hidden');
      if ($pending) {
        $pending.classList.remove('hidden');
        var $pendingEmail = document.getElementById('pending-email');
        if ($pendingEmail) $pendingEmail.textContent = user.email;

        // Show email verification notice for email/password users
        var $verifyNotice = document.getElementById('verify-email-notice');
        if ($verifyNotice && !user.emailVerified && user.providerData && user.providerData[0] && user.providerData[0].providerId === 'password') {
          $verifyNotice.classList.remove('hidden');
        }
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
        var updates = {};
        updates[moduleId] = true;
        var mNum = moduleId.replace('module-', '');
        var lessonContainer = document.querySelector('.space-y-8.mb-12');
        if (lessonContainer) {
          for (var j = 1; j <= lessonContainer.children.length; j++) {
            updates['lesson-' + mNum + '-' + j] = true;
          }
        }
        db.ref('courses/' + u.uid + '/progress').update(updates).then(function () {
          document.getElementById('complete-icon').textContent = '\u2713';
          $markBtn.classList.add('opacity-50');
          var allChecks = document.querySelectorAll('.lesson-check');
          for (var k = 0; k < allChecks.length; k++) {
            allChecks[k].textContent = '\u2713';
            allChecks[k].style.color = '#39FF14';
          }
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
    // Initialize per-lesson tracking and video players on module pages
    if (/^module-[1-6]$/.test(moduleId)) {
      initLessonTracking(moduleId, data.progress || {});
      initVideoPlayers(moduleId);
      initSTLViewers();
    }
    // Populate download links on the downloads page
    if (moduleId === 'downloads') {
      initDownloadLinks();
    }
  }

  /* ── Fetch STL config from Firebase and init 3D viewers + download links ── */
  function initSTLViewers() {
    db.ref('course_content/stl/lessons').once('value').then(function(snap) {
      var lessons = snap.val() || {};
      var driveUrl = function(id) { return 'https://drive.google.com/uc?export=download&id=' + id; };

      // Populate download links on module pages (e.g. #dl-lesson-2-2)
      Object.keys(lessons).forEach(function(k) {
        var l = lessons[k];
        if (!l || !l.driveId) return;
        var el = document.getElementById('dl-' + k);
        if (el) {
          el.href = driveUrl(l.driveId);
          el.target = '_blank';
          el.rel = 'noopener';
        }
      });

      // Init 3D viewers if any .stl-viewer elements exist
      var viewers = document.querySelectorAll('.stl-viewer[data-lesson]');
      if (viewers.length === 0) return;

      // Build config object for stl-viewer.js
      window.STL_CONFIG = { lessons: {}, driveUrl: driveUrl };
      Object.keys(lessons).forEach(function(k) {
        var l = lessons[k];
        window.STL_CONFIG.lessons[k] = {
          file: l.file,
          label: l.label,
          desc: l.desc,
          driveId: l.driveId,
          localPath: driveUrl(l.driveId),
        };
      });
      // Trigger stl-viewer.js init if it's loaded
      if (window.STLViewer && window.STLViewer.init) {
        window.STLViewer.init();
      }
    });
  }

  /* ── Populate download links from Firebase (no hardcoded URLs in HTML) ── */
  function initDownloadLinks() {
    db.ref('course_content/stl').once('value').then(function(snap) {
      var stl = snap.val() || {};
      var driveUrl = function(id) { return 'https://drive.google.com/uc?export=download&id=' + id; };

      // ZIP bundle links
      if (stl.bundles) {
        var babyZip = document.getElementById('dl-baby-zip');
        var generalZip = document.getElementById('dl-general-zip');
        if (babyZip && stl.bundles['baby-milestone-frames-zip']) babyZip.href = driveUrl(stl.bundles['baby-milestone-frames-zip'].driveId);
        if (generalZip && stl.bundles['general-magnet-frames-zip']) generalZip.href = driveUrl(stl.bundles['general-magnet-frames-zip'].driveId);
      }

      // Individual file links — populate containers
      var containers = {
        'dl-lessons': stl.lessons || {},
        'dl-general': stl.generalFrames || {},
        'dl-baby': stl.babyMilestones || {},
        'dl-thingiverse': {},
      };

      // Separate thingiverse from general
      if (stl.generalFrames) {
        Object.keys(stl.generalFrames).forEach(function(k) {
          if (k.indexOf('thingiverse') === 0) {
            containers['dl-thingiverse'][k] = stl.generalFrames[k];
            delete containers['dl-general'][k];
          }
        });
      }

      Object.keys(containers).forEach(function(containerId) {
        var el = document.getElementById(containerId);
        if (!el) return;
        var items = containers[containerId];
        var html = '';
        Object.keys(items).forEach(function(k) {
          var item = items[k];
          if (!item || !item.driveId) return;
          html += '<a href="' + driveUrl(item.driveId) + '" target="_blank" rel="noopener" '
            + 'class="p-3 bg-surface-card/50 border border-border-dim/50 rounded-lg hover:border-electric-blue/40 transition-colors group">'
            + '<p class="text-white font-mono text-xs">' + escapeHtml(item.label || k) + '</p>'
            + '<p class="text-gray-600 text-[10px]">' + escapeHtml(item.desc || k) + ' <span class="text-electric-blue opacity-0 group-hover:opacity-100 transition-opacity">\u2b07</span></p>'
            + '</a>';
        });
        el.innerHTML = html;
      });

      // Show the details section
      var details = document.getElementById('dl-details');
      if (details) details.open = true;
    });
  }

  /* ── Per-Lesson Progress Tracking ── */
  function initLessonTracking(moduleId, progress) {
    var moduleNum = parseInt(moduleId.replace('module-', ''), 10);
    var container = document.querySelector('.space-y-8.mb-12');
    if (!container) return;
    var cards = container.children;
    var totalLessons = cards.length;

    for (var i = 0; i < cards.length; i++) {
      var lessonNum = i + 1;
      var lessonId = 'lesson-' + moduleNum + '-' + lessonNum;
      cards[i].setAttribute('data-lesson-id', lessonId);

      var h3 = cards[i].querySelector('h3');
      if (h3) {
        var check = document.createElement('span');
        check.className = 'lesson-check ml-auto cursor-pointer text-lg transition-colors flex-shrink-0';
        check.setAttribute('data-lesson', lessonId);
        if (progress[lessonId]) {
          check.textContent = '\u2713';
          check.style.color = '#39FF14';
        } else {
          check.textContent = '\u2610';
          check.style.color = '#4b5563';
        }
        h3.appendChild(check);
      }
    }

    // Event delegation for lesson checkboxes
    container.addEventListener('click', function(e) {
      var target = e.target.closest('.lesson-check');
      if (!target) return;
      var lid = target.getAttribute('data-lesson');
      if (!lid || target.textContent === '\u2713') return;
      var u = auth.currentUser;
      if (!u) return;
      db.ref('courses/' + u.uid + '/progress/' + lid).set(true).then(function() {
        target.textContent = '\u2713';
        target.style.color = '#39FF14';
        // Auto-complete module when all lessons done
        var allDone = true;
        for (var n = 1; n <= totalLessons; n++) {
          var c = document.querySelector('[data-lesson="lesson-' + moduleNum + '-' + n + '"]');
          if (!c || c.textContent !== '\u2713') { allDone = false; break; }
        }
        if (allDone) {
          db.ref('courses/' + u.uid + '/progress/' + moduleId).set(true);
          var icon = document.getElementById('complete-icon');
          var btn = document.getElementById('mark-complete');
          if (icon) icon.textContent = '\u2713';
          if (btn) btn.classList.add('opacity-50');
        }
      });
    });
  }

  /* ── YouTube Video Player Initialization ── */
  function initVideoPlayers(moduleId) {
    var moduleNum = parseInt(moduleId.replace('module-', ''), 10);
    // Fetch video config from Firebase (auth-gated) instead of static JS
    db.ref('course_content/videos').once('value').then(function(snap) {
      var config = snap.val() || {};
      var placeholders = document.querySelectorAll('.video-placeholder');
      for (var i = 0; i < placeholders.length; i++) {
        var lessonId = 'lesson-' + moduleNum + '-' + (i + 1);
        var videoId = config[lessonId];
        if (videoId && /^[\w-]{11}$/.test(videoId)) {
          var iframe = document.createElement('iframe');
          iframe.className = 'w-full h-full rounded-b-2xl';
          iframe.src = 'https://www.youtube-nocookie.com/embed/' + videoId + '?rel=0&modestbranding=1';
          iframe.setAttribute('frameborder', '0');
          iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture');
          iframe.setAttribute('allowfullscreen', '');
          iframe.setAttribute('loading', 'lazy');
          placeholders[i].innerHTML = '';
          placeholders[i].appendChild(iframe);
          placeholders[i].style.border = 'none';
        }
      }
    });
  }

  /* ── Certificate of Completion ── */
  function showCertificate(user, data) {
    var $cert = document.getElementById('certificate-section');
    if (!$cert) {
      // Create certificate section dynamically after progress bar
      var $progressWrap = document.querySelector('#progress-bar').closest('.mb-10');
      if (!$progressWrap) return;
      $cert = document.createElement('div');
      $cert.id = 'certificate-section';
      $cert.className = 'mb-10';
      $progressWrap.parentNode.insertBefore($cert, $progressWrap.nextSibling);
    }
    var name = user.displayName || 'Student';
    var date = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    $cert.innerHTML = '<div class="p-6 rounded-2xl border-2 border-neon-green/40 bg-gradient-to-br from-neon-green/5 to-surface-card text-center">'
      + '<p class="text-neon-green font-mono text-xs font-bold tracking-widest mb-2">CERTIFICATE OF COMPLETION</p>'
      + '<h2 class="font-mono text-white text-2xl font-bold mb-1">\uD83C\uDF93 Congratulations, ' + escapeHtml(name.split(' ')[0]) + '!</h2>'
      + '<p class="text-gray-400 text-sm mb-4">You completed all 6 modules of the 3D Print Academy.</p>'
      + '<div class="inline-block p-6 rounded-xl bg-surface border border-border-dim mb-4" id="cert-card">'
      + '<p class="font-mono text-gray-500 text-xs mb-3">This certifies that</p>'
      + '<p class="font-mono text-white text-xl font-bold mb-1">' + escapeHtml(name) + '</p>'
      + '<p class="text-gray-400 text-sm mb-3">has successfully completed the</p>'
      + '<p class="font-mono text-electric-blue text-lg font-bold mb-3">3D Print Academy</p>'
      + '<p class="text-gray-500 text-xs">All 6 Modules \u2022 ' + TOTAL_LESSONS + ' Lessons \u2022 Magnet Frame Design & Business</p>'
      + '<div class="border-t border-border-dim mt-4 pt-4 flex justify-between items-center">'
      + '<div class="text-left"><p class="text-gray-500 text-xs">' + escapeHtml(date) + '</p></div>'
      + '<div class="text-right"><p class="font-mono text-amd-red-text text-xs font-bold">AjayaDesign</p></div>'
      + '</div></div>'
      + '<button onclick="window.print()" class="px-5 py-2 bg-neon-green/20 text-neon-green border border-neon-green/30 rounded-lg font-mono text-sm font-semibold hover:bg-neon-green/30 transition-colors">\uD83D\uDDA8\uFE0F Print Certificate</button>'
      + '</div>';
  }

  /* ── Admin Command Center (portal dashboard, admin-only) ── */
  function initAdminCommandCenter() {
    var $cc = document.getElementById('admin-command-center');
    if (!$cc) return;
    $cc.classList.remove('hidden');
    var $content = document.getElementById('admin-cc-content');
    if (!$content) return;

    // Load all data in parallel
    Promise.all([
      db.ref('approved_users').once('value'),
      db.ref('pending_users').once('value'),
      db.ref('pre_approved').once('value'),
      db.ref('courses').once('value'),
      db.ref('email_queue').once('value')
    ]).then(function(snaps) {
      var approved = snaps[0].val() || {};
      var pending = snaps[1].val() || {};
      var preApproved = snaps[2].val() || {};
      var allCourses = snaps[3].val() || {};
      var emailQueue = snaps[4].val() || {};

      renderAdminCommandCenter($content, approved, pending, preApproved, allCourses, emailQueue);
    }).catch(function(err) {
      console.error('Command center error:', err);
      $content.innerHTML = '<p class="text-amd-red-text text-sm font-mono">Failed to load analytics: ' + escapeHtml(err.message || 'Unknown error') + '</p>';
    });
  }

  function renderAdminCommandCenter($cc, approved, pending, preApproved, allCourses, emailQueue) {
    var approvedArr = Object.keys(approved).map(function(uid) { return { uid: uid, data: approved[uid] }; });
    var pendingArr = Object.keys(pending).map(function(uid) { return { uid: uid, data: pending[uid] }; });
    var preArr = Object.keys(preApproved).map(function(k) { return { key: k, data: preApproved[k] }; });

    // ── Revenue & Tier Stats ──
    var tierCounts = { stl: 0, course: 0, session: 0, bundle: 0 };
    var tierPrices = { stl: 29, course: 97, session: 149, bundle: 349 };
    var totalRevenue = 0;
    approvedArr.forEach(function(u) {
      var t = u.data.tier;
      if (tierCounts[t] !== undefined) tierCounts[t]++;
      if (!u.data.manual) totalRevenue += tierPrices[t] || 0;
    });

    // ── Session Tracking ──
    var sessionUsers = approvedArr.filter(function(u) {
      return u.data.tier === 'session' || u.data.tier === 'bundle';
    });
    var sessionsNotBooked = sessionUsers.filter(function(u) { return !u.data.session_booked; });
    var sessionsBooked = sessionUsers.filter(function(u) { return u.data.session_booked && !u.data.session_completed; });
    var sessionsCompleted = sessionUsers.filter(function(u) { return !!u.data.session_completed; });

    // ── Progress Stats ──
    var progressStats = [];
    approvedArr.forEach(function(u) {
      var prog = (allCourses[u.uid] && allCourses[u.uid].progress) || {};
      var modules = 0; var lessons = 0;
      for (var k in prog) {
        if (prog[k] && k.indexOf('module-') === 0) modules++;
        if (prog[k] && k.indexOf('lesson-') === 0) lessons++;
      }
      progressStats.push({ uid: u.uid, name: u.data.name || u.data.email, email: u.data.email, tier: u.data.tier, modules: modules, lessons: lessons, approved_at: u.data.approved_at });
    });

    // ── Email Stats ──
    var emailQueueArr = Object.keys(emailQueue).map(function(k) { return emailQueue[k]; });
    var emailsSent = emailQueueArr.filter(function(e) { return e.sent; }).length;
    var emailsPending = emailQueueArr.filter(function(e) { return !e.sent; }).length;

    // ── At-Risk Students (approved 7+ days ago, <2 modules) ──
    var sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    var atRisk = progressStats.filter(function(s) {
      return s.approved_at && s.approved_at < sevenDaysAgo && s.modules < 2 && (s.tier === 'course' || s.tier === 'bundle');
    });

    var html = '';

    // ── KPI Cards Row ──
    html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">';
    html += kpiCard('$' + totalRevenue.toLocaleString(), 'Total Revenue', 'text-neon-green');
    html += kpiCard(approvedArr.length, 'Active Students', 'text-electric-blue');
    html += kpiCard(pendingArr.length, 'Pending Approval', 'text-yellow-400');
    html += kpiCard(preArr.length, 'Paid Not Logged In', 'text-amd-red-text');
    html += '</div>';

    // ── Tier Breakdown ──
    html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">';
    html += kpiCard(tierCounts.stl, 'STL ($29)', 'text-gray-400');
    html += kpiCard(tierCounts.course, 'Course ($97)', 'text-electric-blue');
    html += kpiCard(tierCounts.session, 'Session ($149)', 'text-amd-red-text');
    html += kpiCard(tierCounts.bundle, 'Bundle ($349)', 'text-neon-green');
    html += '</div>';

    // ── 1-on-1 SESSION MANAGEMENT ──
    html += '<div class="mb-8">';
    html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\uD83D\uDCC5</span>1-on-1 Session Management</h3>';

    if (sessionsNotBooked.length) {
      html += '<p class="font-mono text-yellow-400 text-xs mb-3 font-bold">NEEDS BOOKING (' + sessionsNotBooked.length + ')</p>';
      sessionsNotBooked.forEach(function(u) {
        html += sessionCard(u, 'not-booked');
      });
    }
    if (sessionsBooked.length) {
      html += '<p class="font-mono text-electric-blue text-xs mb-3 mt-4 font-bold">SCHEDULED (' + sessionsBooked.length + ')</p>';
      sessionsBooked.forEach(function(u) {
        html += sessionCard(u, 'booked');
      });
    }
    if (sessionsCompleted.length) {
      html += '<p class="font-mono text-neon-green text-xs mb-3 mt-4 font-bold">COMPLETED (' + sessionsCompleted.length + ')</p>';
      sessionsCompleted.forEach(function(u) {
        html += sessionCard(u, 'completed');
      });
    }
    if (!sessionUsers.length) {
      html += '<p class="text-gray-500 text-sm font-mono">No session/bundle students yet.</p>';
    }
    html += '</div>';

    // ── AT-RISK STUDENTS ──
    if (atRisk.length) {
      html += '<div class="mb-8">';
      html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\u26A0\uFE0F</span>At-Risk Students <span class="text-amd-red-text text-sm">(' + atRisk.length + ')</span></h3>';
      html += '<p class="text-gray-500 text-xs mb-3">Approved 7+ days ago, fewer than 2 modules completed</p>';
      atRisk.forEach(function(s) {
        html += '<div class="flex items-center justify-between p-3 rounded-lg bg-amd-red/5 border border-amd-red/20 mb-2">'
          + '<div><p class="font-mono text-white text-sm">' + escapeHtml(s.name) + '</p>'
          + '<p class="text-gray-500 text-xs">' + escapeHtml(s.email) + ' \u2022 ' + s.modules + '/6 modules \u2022 ' + s.lessons + '/' + TOTAL_LESSONS + ' lessons</p></div>'
          + '<span class="text-amd-red-text text-xs font-mono">' + daysSince(s.approved_at) + 'd ago</span></div>';
      });
      html += '</div>';
    }

    // ── COMPLETION DISTRIBUTION CHART ──
    if (progressStats.length) {
      var buckets = [0,0,0,0,0,0,0]; // 0, 1, 2, 3, 4, 5, 6 modules
      progressStats.forEach(function(s) { buckets[Math.min(s.modules, 6)]++; });
      var maxBucket = Math.max.apply(null, buckets) || 1;
      var bucketLabels = ['0', '1', '2', '3', '4', '5', '6\u2713'];
      var bucketColors = ['#4b5563', '#EF4444', '#F59E0B', '#F59E0B', '#3B82F6', '#3B82F6', '#39FF14'];
      html += '<div class="mb-8">';
      html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\uD83D\uDCC8</span>Completion Distribution</h3>';
      html += '<div class="flex items-end gap-2" style="height:120px">';
      for (var b = 0; b < 7; b++) {
        var pct = Math.round((buckets[b] / maxBucket) * 100);
        html += '<div class="flex-1 flex flex-col items-center gap-1">'
          + '<span class="font-mono text-xs" style="color:' + bucketColors[b] + '">' + buckets[b] + '</span>'
          + '<div class="w-full rounded-t" style="height:' + Math.max(pct, 4) + '%;background:' + bucketColors[b] + ';min-height:4px"></div>'
          + '<span class="font-mono text-gray-500 text-[10px]">' + bucketLabels[b] + '</span>'
          + '</div>';
      }
      html += '</div>';
      html += '<p class="text-gray-600 text-[10px] font-mono mt-2 text-center">Modules completed \u2192</p>';
      html += '</div>';
    }

    // ── STUDENT PROGRESS TABLE ──
    html += '<div class="mb-8">';
    html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\uD83D\uDCCA</span>Student Progress</h3>';
    if (progressStats.length) {
      html += '<div class="overflow-x-auto"><table class="w-full text-left">';
      html += '<thead><tr class="border-b border-border-dim">'
        + '<th class="p-2 font-mono text-gray-500 text-xs">Student</th>'
        + '<th class="p-2 font-mono text-gray-500 text-xs">Tier</th>'
        + '<th class="p-2 font-mono text-gray-500 text-xs">Modules</th>'
        + '<th class="p-2 font-mono text-gray-500 text-xs">Lessons</th>'
        + '<th class="p-2 font-mono text-gray-500 text-xs">Progress</th>'
        + '<th class="p-2 font-mono text-gray-500 text-xs">Since</th>'
        + '</tr></thead><tbody>';
      progressStats.sort(function(a,b) { return b.lessons - a.lessons; });
      progressStats.forEach(function(s) {
        var pct = Math.round((s.lessons / TOTAL_LESSONS) * 100);
        var tierColor = s.tier === 'bundle' ? 'text-neon-green' : s.tier === 'course' ? 'text-electric-blue' : s.tier === 'session' ? 'text-amd-red-text' : 'text-gray-400';
        html += '<tr class="border-b border-border-dim/50">'
          + '<td class="p-2"><p class="font-mono text-white text-sm">' + escapeHtml(s.name) + '</p><p class="text-gray-600 text-xs">' + escapeHtml(s.email) + '</p></td>'
          + '<td class="p-2 font-mono text-xs ' + tierColor + '">' + escapeHtml(s.tier) + '</td>'
          + '<td class="p-2 font-mono text-white text-sm">' + s.modules + '/6</td>'
          + '<td class="p-2 font-mono text-white text-sm">' + s.lessons + '/' + TOTAL_LESSONS + '</td>'
          + '<td class="p-2"><div class="flex items-center gap-2"><div class="w-16 h-1.5 bg-surface rounded-full overflow-hidden"><div class="h-full bg-gradient-to-r from-amd-red to-neon-green rounded-full" style="width:' + pct + '%"></div></div><span class="font-mono text-xs text-gray-400">' + pct + '%</span></div></td>'
          + '<td class="p-2 font-mono text-gray-500 text-xs">' + daysSince(s.approved_at) + 'd</td>'
          + '</tr>';
      });
      html += '</tbody></table></div>';
    } else {
      html += '<p class="text-gray-500 text-sm font-mono">No students yet.</p>';
    }
    html += '</div>';

    // ── PRE-APPROVED (Paid but haven't logged in) ──
    if (preArr.length) {
      html += '<div class="mb-8">';
      html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\uD83D\uDCB3</span>Paid — Not Logged In Yet <span class="text-yellow-400 text-sm">(' + preArr.length + ')</span></h3>';
      preArr.forEach(function(p) {
        html += '<div class="flex items-center justify-between p-3 rounded-lg bg-surface border border-border-dim mb-2">'
          + '<div><p class="font-mono text-white text-sm">' + escapeHtml(p.data.email) + '</p>'
          + '<p class="text-gray-500 text-xs">Tier: ' + escapeHtml(p.data.tier) + ' \u2022 Stripe: ' + escapeHtml(p.data.stripe_session || '—') + '</p></div>'
          + '<span class="text-yellow-400 text-xs font-mono">' + daysSince(p.data.approved_at) + 'd ago</span></div>';
      });
      html += '</div>';
    }

    // ── EMAIL AUTOMATION STATS ──
    html += '<div class="mb-8">';
    html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\u2709\uFE0F</span>Email Automation</h3>';
    html += '<div class="grid grid-cols-2 gap-3">';
    html += kpiCard(emailsSent, 'Emails Sent', 'text-neon-green');
    html += kpiCard(emailsPending, 'Queued', 'text-yellow-400');
    html += '</div>';
    html += '</div>';

    // ── PENDING APPROVAL ──
    html += '<div class="mb-8">';
    html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\u23F3</span>Pending Approval <span class="text-yellow-400 text-sm">(' + pendingArr.length + ')</span></h3>';
    html += '<div id="admin-pending-list">';
    if (!pendingArr.length) {
      html += '<p class="text-gray-500 text-sm font-mono">No pending requests.</p>';
    }
    pendingArr.forEach(function(p) {
      var safeUid = escapeAttr(p.uid);
      var date = p.data.requested_at ? new Date(p.data.requested_at).toLocaleDateString() : '\u2014';
      html += '<div class="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl bg-surface border border-border-dim mb-3 gap-3">'
        + '<div class="flex items-center gap-3">'
        + (p.data.photo ? '<img src="' + escapeAttr(p.data.photo) + '" class="w-10 h-10 rounded-full" alt="" />' : '<div class="w-10 h-10 rounded-full bg-surface-card flex items-center justify-center text-gray-500">?</div>')
        + '<div>'
        + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(p.data.name || 'Unknown') + '</p>'
        + '<p class="text-gray-500 text-xs">' + escapeHtml(p.data.email) + ' \u2022 ' + escapeHtml(date) + '</p>'
        + '</div></div>'
        + '<div class="flex items-center gap-2 flex-wrap">'
        + '<select data-uid="' + safeUid + '" class="admin-tier bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim">'
        + '<option value="stl">STL</option><option value="course" selected>Course</option><option value="session">Session</option><option value="bundle">Bundle</option></select>'
        + '<input data-uid="' + safeUid + '" class="admin-payref bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim w-24" placeholder="Pay ref" />'
        + '<button data-uid="' + safeUid + '" data-action="approve" class="admin-action px-3 py-1 bg-neon-green/20 text-neon-green text-xs font-mono font-bold rounded hover:bg-neon-green/30">Approve</button>'
        + '<button data-uid="' + safeUid + '" data-action="deny" class="admin-action px-3 py-1 bg-amd-red/20 text-amd-red-text text-xs font-mono font-bold rounded hover:bg-amd-red/30">Deny</button>'
        + '</div></div>';
    });
    html += '</div></div>';

    // ── APPROVED USERS QUICK LIST ──
    html += '<div class="mb-8">';
    html += '<h3 class="font-mono text-white text-lg font-bold mb-4 flex items-center gap-2"><span class="text-xl">\u2705</span>Approved Students <span class="text-neon-green text-sm">(' + approvedArr.length + ')</span></h3>';
    html += '<div id="admin-approved-list">';
    if (!approvedArr.length) {
      html += '<p class="text-gray-500 text-sm font-mono">No approved users yet.</p>';
    }
    approvedArr.forEach(function(u) {
      var safeUid = escapeAttr(u.uid);
      var date = u.data.approved_at ? new Date(u.data.approved_at).toLocaleDateString() : '\u2014';
      var tierColor = u.data.tier === 'bundle' ? 'text-neon-green' : u.data.tier === 'course' ? 'text-electric-blue' : u.data.tier === 'session' ? 'text-amd-red-text' : 'text-gray-400';
      html += '<div class="flex items-center justify-between p-3 rounded-lg bg-surface border border-border-dim mb-2">'
        + '<div>'
        + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(u.data.name || u.data.email) + '</p>'
        + '<p class="text-gray-500 text-xs">' + escapeHtml(u.data.email) + ' \u2022 <span class="' + tierColor + '">' + escapeHtml(u.data.tier) + '</span> \u2022 ' + escapeHtml(date) + (u.data.payment_ref ? ' \u2022 ' + escapeHtml(u.data.payment_ref) : '') + '</p>'
        + '</div>'
        + '<button data-uid="' + safeUid + '" data-action="revoke" class="admin-action px-3 py-1 bg-amd-red/20 text-amd-red-text text-xs font-mono font-bold rounded hover:bg-amd-red/30">Revoke</button>'
        + '</div>';
    });
    html += '</div></div>';

    $cc.innerHTML = html;
  }

  function kpiCard(value, label, colorClass) {
    return '<div class="p-4 rounded-xl bg-surface-card border border-border-dim text-center">'
      + '<p class="font-mono text-2xl font-bold ' + (colorClass || 'text-white') + '">' + value + '</p>'
      + '<p class="text-gray-500 text-xs font-mono mt-1">' + label + '</p></div>';
  }

  function sessionCard(u, status) {
    var safeUid = escapeAttr(u.uid);
    var borderClass = status === 'completed' ? 'border-neon-green/20' : status === 'booked' ? 'border-electric-blue/20' : 'border-yellow-500/20';
    var bgClass = status === 'completed' ? 'bg-neon-green/5' : status === 'booked' ? 'bg-electric-blue/5' : 'bg-yellow-500/5';
    var sessRemain = u.data.sessions_remaining !== undefined ? u.data.sessions_remaining : (u.data.tier === 'bundle' ? 2 : 1);

    var html = '<div class="p-4 rounded-xl ' + bgClass + ' border ' + borderClass + ' mb-3">'
      + '<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">'
      + '<div>'
      + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(u.data.name || u.data.email) + '</p>'
      + '<p class="text-gray-500 text-xs">' + escapeHtml(u.data.email) + ' \u2022 ' + escapeHtml(u.data.tier) + ' \u2022 ' + sessRemain + ' session(s) remaining</p>';
    if (u.data.session_date) {
      html += '<p class="text-gray-400 text-xs mt-1">\uD83D\uDCC5 ' + escapeHtml(u.data.session_date) + '</p>';
    }
    if (u.data.session_notes) {
      html += '<p class="text-gray-500 text-xs mt-1 italic">\uD83D\uDCDD ' + escapeHtml(u.data.session_notes) + '</p>';
    }
    html += '</div><div class="flex items-center gap-2 flex-wrap">';

    if (status === 'not-booked') {
      html += '<input data-uid="' + safeUid + '" class="session-date bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim w-32" type="date" placeholder="Date" />'
        + '<button data-uid="' + safeUid + '" data-action="book-session" class="admin-action px-3 py-1 bg-electric-blue/20 text-electric-blue text-xs font-mono font-bold rounded hover:bg-electric-blue/30">\uD83D\uDCC5 Book</button>';
    } else if (status === 'booked') {
      html += '<input data-uid="' + safeUid + '" class="session-notes bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim w-32" placeholder="Notes..." />'
        + '<button data-uid="' + safeUid + '" data-action="complete-session" class="admin-action px-3 py-1 bg-neon-green/20 text-neon-green text-xs font-mono font-bold rounded hover:bg-neon-green/30">\u2713 Done</button>';
    } else {
      html += '<span class="text-neon-green text-xs font-mono">\u2713 Complete</span>';
    }

    html += '</div></div></div>';
    return html;
  }

  function daysSince(ts) {
    if (!ts) return '?';
    return Math.floor((Date.now() - ts) / (24 * 60 * 60 * 1000));
  }

  /* ── Session Management Actions ── */
  function bookSession(uid) {
    var dateEl = document.querySelector('.session-date[data-uid="' + uid + '"]');
    if (!dateEl || !dateEl.value) { alert('Select a date first'); return; }
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;

    db.ref('approved_users/' + uid).once('value').then(function(snap) {
      var data = snap.val();
      if (!data) return;
      var remaining = data.sessions_remaining !== undefined ? data.sessions_remaining : (data.tier === 'bundle' ? 2 : 1);
      var updates = {
        session_booked: firebase.database.ServerValue.TIMESTAMP,
        session_date: dateEl.value,
        sessions_remaining: remaining
      };
      db.ref('approved_users/' + uid).update(updates).then(function() {
        initAdminCommandCenter(); // Refresh
      }).catch(function(err) {
        alert('Failed to book session: ' + err.message);
      });
    }).catch(function(err) {
      alert('Error reading user: ' + err.message);
    });
  }

  function completeSession(uid) {
    var notesEl = document.querySelector('.session-notes[data-uid="' + uid + '"]');
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;

    db.ref('approved_users/' + uid).once('value').then(function(snap) {
      var data = snap.val();
      if (!data) return;
      var remaining = data.sessions_remaining !== undefined ? data.sessions_remaining : (data.tier === 'bundle' ? 2 : 1);
      remaining = Math.max(0, remaining - 1);
      var updates = {
        session_completed: firebase.database.ServerValue.TIMESTAMP,
        sessions_remaining: remaining
      };
      if (notesEl && notesEl.value.trim()) {
        updates.session_notes = notesEl.value.trim();
      }
      // If sessions remain, clear booked state so they can book again
      if (remaining > 0) {
        updates.session_booked = null;
        updates.session_date = null;
        updates.session_completed = null;
        updates.session_notes = (data.session_notes ? data.session_notes + ' | ' : '') + (notesEl && notesEl.value.trim() ? notesEl.value.trim() : 'Session completed');
        updates.sessions_remaining = remaining;
      }
      db.ref('approved_users/' + uid).update(updates).then(function() {
        initAdminCommandCenter(); // Refresh
      }).catch(function(err) {
        alert('Failed to complete session: ' + err.message);
      });
    }).catch(function(err) {
      alert('Error reading user: ' + err.message);
    });
  }

  /* ── Register user as pending (write-once to /pending_users/{uid}) ── */
  function registerPending(user) {
    // Atomic write — RTDB rule (!data.exists()) prevents overwrites server-side.
    db.ref('pending_users/' + user.uid).set({
      email: user.email,
      name: user.displayName || user.email.split('@')[0],
      photo: user.photoURL || '',
      provider: user.providerData && user.providerData[0] ? user.providerData[0].providerId : 'unknown',
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
      loadSessionUsers();
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
    }, function(err) {
      console.error('Pending users error:', err);
      $list.innerHTML = '<p class="text-amd-red-text text-sm font-mono">Failed to load: ' + escapeHtml(err.message || 'Permission denied') + '</p>';
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
        var tierColor = u.tier === 'bundle' ? 'text-neon-green' : u.tier === 'course' ? 'text-electric-blue' : u.tier === 'session' ? 'text-amd-red-text' : 'text-gray-400';
        html += '<div class="flex items-center justify-between p-4 rounded-xl bg-surface border border-border-dim mb-3">'
          + '<div>'
          + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(u.name || u.email) + '</p>'
          + '<p class="text-gray-500 text-xs">' + escapeHtml(u.email) + ' &bull; Tier: <span class="' + tierColor + '">' + escapeHtml(u.tier) + '</span> &bull; Approved: ' + escapeHtml(date) + (u.payment_ref ? ' &bull; Ref: ' + escapeHtml(u.payment_ref) : '') + '</p>'
          + '</div>'
          + '<button data-uid="' + safeUid + '" data-action="revoke" class="admin-action px-3 py-1 bg-amd-red/20 text-amd-red-text text-xs font-mono font-bold rounded hover:bg-amd-red/30 transition-colors">Revoke</button>'
          + '</div>';
      });
      $list.innerHTML = html;
    }, function(err) {
      console.error('Approved users error:', err);
      $list.innerHTML = '<p class="text-amd-red-text text-sm font-mono">Failed to load: ' + escapeHtml(err.message || 'Permission denied') + '</p>';
    });
  }

  function loadSessionUsers() {
    var $list = document.getElementById('session-list');
    if (!$list) return;
    db.ref('approved_users').on('value', function (snap) {
      var data = snap.val();
      if (!data) { $list.innerHTML = '<p class="text-gray-500 text-sm font-mono">No users yet.</p>'; return; }
      var sessionUsers = [];
      Object.keys(data).forEach(function(uid) {
        var u = data[uid];
        if (u.tier === 'session' || u.tier === 'bundle') { sessionUsers.push({ uid: uid, data: u }); }
      });
      if (!sessionUsers.length) { $list.innerHTML = '<p class="text-gray-500 text-sm font-mono">No session/bundle students yet.</p>'; return; }

      var html = '';
      // Not booked
      var notBooked = sessionUsers.filter(function(u) { return !u.data.session_booked; });
      var booked = sessionUsers.filter(function(u) { return u.data.session_booked && !u.data.session_completed; });
      var completed = sessionUsers.filter(function(u) { return !!u.data.session_completed; });

      if (notBooked.length) {
        html += '<p class="font-mono text-yellow-400 text-xs mb-2 font-bold">NEEDS BOOKING (' + notBooked.length + ')</p>';
        notBooked.forEach(function(u) { html += adminSessionRow(u, 'not-booked'); });
      }
      if (booked.length) {
        html += '<p class="font-mono text-electric-blue text-xs mb-2 mt-4 font-bold">SCHEDULED (' + booked.length + ')</p>';
        booked.forEach(function(u) { html += adminSessionRow(u, 'booked'); });
      }
      if (completed.length) {
        html += '<p class="font-mono text-neon-green text-xs mb-2 mt-4 font-bold">COMPLETED (' + completed.length + ')</p>';
        completed.forEach(function(u) { html += adminSessionRow(u, 'completed'); });
      }
      $list.innerHTML = html;
    }, function(err) {
      console.error('Session users error:', err);
      $list.innerHTML = '<p class="text-amd-red-text text-sm font-mono">Failed to load: ' + escapeHtml(err.message || 'Permission denied') + '</p>';
    });
  }

  function adminSessionRow(u, status) {
    var safeUid = escapeAttr(u.uid);
    var remain = u.data.sessions_remaining !== undefined ? u.data.sessions_remaining : (u.data.tier === 'bundle' ? 2 : 1);
    var html = '<div class="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl bg-surface border border-border-dim mb-3 gap-3">'
      + '<div>'
      + '<p class="font-mono text-white text-sm font-semibold">' + escapeHtml(u.data.name || u.data.email) + '</p>'
      + '<p class="text-gray-500 text-xs">' + escapeHtml(u.data.email) + ' &bull; ' + escapeHtml(u.data.tier) + ' &bull; ' + remain + ' session(s) left</p>';
    if (u.data.session_date) html += '<p class="text-gray-400 text-xs mt-1">\uD83D\uDCC5 ' + escapeHtml(u.data.session_date) + '</p>';
    if (u.data.session_notes) html += '<p class="text-gray-500 text-xs mt-1 italic">\uD83D\uDCDD ' + escapeHtml(u.data.session_notes) + '</p>';
    html += '</div><div class="flex items-center gap-2 flex-wrap">';
    if (status === 'not-booked') {
      html += '<input data-uid="' + safeUid + '" class="session-date bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim w-32" type="date" />'
        + '<button data-uid="' + safeUid + '" data-action="book-session" class="admin-action px-3 py-1 bg-electric-blue/20 text-electric-blue text-xs font-mono font-bold rounded hover:bg-electric-blue/30">\uD83D\uDCC5 Book</button>';
    } else if (status === 'booked') {
      html += '<input data-uid="' + safeUid + '" class="session-notes bg-surface-card text-white text-xs font-mono rounded px-2 py-1 border border-border-dim w-32" placeholder="Notes..." />'
        + '<button data-uid="' + safeUid + '" data-action="complete-session" class="admin-action px-3 py-1 bg-neon-green/20 text-neon-green text-xs font-mono font-bold rounded hover:bg-neon-green/30">\u2713 Done</button>';
    } else {
      html += '<span class="text-neon-green text-xs font-mono">\u2713 Complete</span>';
    }
    html += '</div></div>';
    return html;
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
        payment_ref: payRef || '',
        sessions_remaining: tier === 'bundle' ? 2 : tier === 'session' ? 1 : 0
      }).then(function () {
        db.ref('pending_users/' + uid).remove();
      }).catch(function(err) {
        alert('Failed to approve: ' + err.message);
      });
    }).catch(function(err) {
      alert('Error reading user: ' + err.message);
    });
  }

  function denyUser(uid) {
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;
    db.ref('pending_users/' + uid).remove().catch(function(err) {
      alert('Failed to deny: ' + err.message);
    });
  }

  function revokeUser(uid) {
    var user = auth.currentUser;
    if (!user || !isAdmin(user.email)) return;
    if (!confirm('Revoke access for this user?')) return;
    db.ref('approved_users/' + uid).remove().catch(function(err) {
      alert('Failed to revoke: ' + err.message);
    });
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
    else if (action === 'book-session') bookSession(uid);
    else if (action === 'complete-session') completeSession(uid);
  });

  /* ── Public API ── */
  window.PortalAuth = {
    initDashboard: initDashboard,
    initModule: initModule,
    initAdmin: initAdmin
  };
})();

// Debug banner (outside IIFE — uses global firebase)
(function() {
  var $dbg = document.getElementById('auth-debug');
  if ($dbg && window.firebase) {
    firebase.auth().onAuthStateChanged(function(u) {
      $dbg.textContent = u ? 'Auth: ' + u.email + ' (uid: ' + u.uid.substring(0,8) + '...)' : 'Auth: not signed in';
      $dbg.style.color = u ? '#39FF14' : '#FF6B6B';
    });
  }
})();
