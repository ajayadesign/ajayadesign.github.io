/**
 * STL 3D Viewer — 3D Print Academy
 *
 * Renders interactive 3D previews of STL files using Three.js.
 * Auto-initializes on elements with class "stl-viewer" and data-lesson attribute.
 *
 * Usage in HTML:
 *   <div class="stl-viewer" data-lesson="2-2"></div>
 *
 * Dependencies (loaded dynamically):
 *   - Three.js r170  (three.module.min.js)
 *   - STLLoader       (from three/addons)
 *   - OrbitControls   (from three/addons)
 */
(function () {
  'use strict';

  const CDN = 'https://cdn.jsdelivr.net/npm/three@0.170.0';
  const IMPORT_MAP = {
    three:          CDN + '/build/three.module.min.js',
    STLLoader:      CDN + '/examples/jsm/loaders/STLLoader.js',
    OrbitControls:  CDN + '/examples/jsm/controls/OrbitControls.js',
  };

  /* ── Inject importmap ───────────────────────────────────────────────── */
  if (!document.querySelector('script[type="importmap"]')) {
    const im = document.createElement('script');
    im.type = 'importmap';
    im.textContent = JSON.stringify({ imports: { three: IMPORT_MAP.three, 'three/addons/': CDN + '/examples/jsm/' } });
    document.head.appendChild(im);
  }

  /* ── Lazy-load Three.js modules ─────────────────────────────────────── */
  let THREE, STLLoader, OrbitControls;
  async function loadDeps() {
    if (THREE) return;
    THREE = await import(IMPORT_MAP.three);
    const stlMod = await import(IMPORT_MAP.STLLoader);
    const orbMod = await import(IMPORT_MAP.OrbitControls);
    STLLoader = stlMod.STLLoader;
    OrbitControls = orbMod.OrbitControls;
  }

  /* ── Create a single viewer instance ────────────────────────────────── */
  function createViewer(container, stlUrl, cfg) {
    const width  = container.clientWidth || 320;
    const height = 280;

    // Canvas wrapper
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:relative;width:100%;height:' + height + 'px;border-radius:12px;overflow:hidden;background:#0d0d14;';
    container.appendChild(wrap);

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0d0d14);

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
    camera.position.set(0, 80, 180);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    wrap.appendChild(renderer.domElement);

    // Orbit controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.5;
    controls.minDistance = 40;
    controls.maxDistance = 500;

    // Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const dir1 = new THREE.DirectionalLight(0x00d4ff, 0.8);
    dir1.position.set(100, 200, 150);
    scene.add(dir1);
    const dir2 = new THREE.DirectionalLight(0xff6b6b, 0.4);
    dir2.position.set(-100, 100, -100);
    scene.add(dir2);

    // Grid floor
    const grid = new THREE.GridHelper(200, 20, 0x1e1e2a, 0x111118);
    grid.position.y = -1;
    scene.add(grid);

    // Load STL
    const loader = new STLLoader();
    loader.load(stlUrl, function (geometry) {
      geometry.computeVertexNormals();
      geometry.center();

      const material = new THREE.MeshPhongMaterial({
        color: 0x00d4ff,
        specular: 0x222244,
        shininess: 40,
        flatShading: false,
      });
      const mesh = new THREE.Mesh(geometry, material);

      // Scale to fit view
      const box = new THREE.Box3().setFromBufferAttribute(geometry.attributes.position);
      const size = new THREE.Vector3();
      box.getSize(size);
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 80 / maxDim;
      mesh.scale.set(scale, scale, scale);
      mesh.rotation.x = -Math.PI / 2; // Z-up → Y-up

      scene.add(mesh);

      // Auto-fit camera
      camera.position.set(0, 60, 120);
      controls.target.set(0, 0, 0);
      controls.update();

      // Remove spinner
      const spinner = wrap.querySelector('.stl-spinner');
      if (spinner) spinner.remove();
    }, undefined, function () {
      const err = wrap.querySelector('.stl-spinner');
      if (err) err.textContent = 'Could not load 3D model';
    });

    // Loading spinner
    const spinner = document.createElement('div');
    spinner.className = 'stl-spinner';
    spinner.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#555;font-family:monospace;font-size:12px;pointer-events:none;';
    spinner.textContent = 'Loading 3D model…';
    wrap.appendChild(spinner);

    // Toolbar
    const toolbar = document.createElement('div');
    toolbar.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap;';

    // Download button
    if (cfg && cfg.driveId) {
      const dl = document.createElement('a');
      dl.href = window.STL_CONFIG.driveUrl(cfg.driveId);
      dl.target = '_blank';
      dl.rel = 'noopener';
      dl.className = 'stl-btn';
      dl.innerHTML = '⬇ Download STL';
      toolbar.appendChild(dl);
    }

    // Wireframe toggle
    const wireBtn = document.createElement('button');
    wireBtn.className = 'stl-btn';
    wireBtn.textContent = '◇ Wireframe';
    let wireOn = false;
    wireBtn.addEventListener('click', function () {
      wireOn = !wireOn;
      scene.traverse(function (child) {
        if (child.isMesh) child.material.wireframe = wireOn;
      });
      wireBtn.textContent = wireOn ? '◆ Solid' : '◇ Wireframe';
    });
    toolbar.appendChild(wireBtn);

    // Reset view
    const resetBtn = document.createElement('button');
    resetBtn.className = 'stl-btn';
    resetBtn.textContent = '↻ Reset';
    resetBtn.addEventListener('click', function () {
      camera.position.set(0, 60, 120);
      controls.target.set(0, 0, 0);
      controls.update();
    });
    toolbar.appendChild(resetBtn);

    // Label
    if (cfg && cfg.label) {
      const lbl = document.createElement('span');
      lbl.style.cssText = 'margin-left:auto;color:#666;font-family:monospace;font-size:11px;';
      lbl.textContent = cfg.file || cfg.label;
      toolbar.appendChild(lbl);
    }

    container.appendChild(toolbar);

    // Animation loop
    let animId;
    function animate() {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    // Responsive resize
    const ro = new ResizeObserver(function () {
      const w = container.clientWidth;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    });
    ro.observe(container);
  }

  /* ── CSS injection ──────────────────────────────────────────────────── */
  function injectCSS() {
    if (document.getElementById('stl-viewer-css')) return;
    const style = document.createElement('style');
    style.id = 'stl-viewer-css';
    style.textContent = [
      '.stl-viewer canvas { border-radius: 12px; cursor: grab; }',
      '.stl-viewer canvas:active { cursor: grabbing; }',
      '.stl-btn { display:inline-flex;align-items:center;gap:4px;padding:6px 12px;',
      '  background:#16161F;border:1px solid #1e1e2a;border-radius:8px;',
      '  color:#9ca3af;font-family:"JetBrains Mono",monospace;font-size:11px;',
      '  cursor:pointer;transition:all .15s;text-decoration:none; }',
      '.stl-btn:hover { color:#00d4ff;border-color:#00d4ff33; }',
      'a.stl-btn { color:#00d4ff;border-color:#00d4ff33; }',
      'a.stl-btn:hover { background:#00d4ff11; }',
    ].join('\n');
    document.head.appendChild(style);
  }

  /* ── Auto-init all .stl-viewer elements ─────────────────────────────── */
  async function initViewers() {
    const els = document.querySelectorAll('.stl-viewer[data-lesson]');
    if (els.length === 0) return;

    const config = window.STL_CONFIG;
    if (!config || !config.lessons) return;

    injectCSS();
    await loadDeps();

    els.forEach(function (el) {
      const lessonId = 'lesson-' + el.getAttribute('data-lesson');
      const cfg = config.lessons[lessonId];
      if (!cfg || !cfg.localPath) return;
      if (el.dataset.initialized) return;
      el.dataset.initialized = '1';
      createViewer(el, cfg.localPath, cfg);
    });
  }

  /* ── Public API for downloads page ──────────────────────────────────── */
  window.STLViewer = {
    init: initViewers,
    renderFromUrl: async function (container, url, cfg) {
      injectCSS();
      await loadDeps();
      createViewer(container, url, cfg);
    },
  };

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initViewers);
  } else {
    initViewers();
  }
})();
