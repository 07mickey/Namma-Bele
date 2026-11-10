/**
 * Three.js Interactive 3D Soil Cross-Section Visualizer
 * Shows organic horizon, topsoil, subsoil, parent material, surface vegetation, and root architecture.
 * Features:
 * - Subtle interaction (orbit/drag rotation)
 * - Auto-rotation with prefers-reduced-motion compliance
 * - IntersectionObserver to pause rendering when out of viewport
 * - Graceful WebGL fallback detection
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('threejs-soil-canvas-container');
    const fallback = document.getElementById('webgl-fallback');
    if (!container) return;

    // 1. WebGL Support Detection
    function isWebGLAvailable() {
      try {
        const canvas = document.createElement('canvas');
        return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
      } catch (e) {
        return false;
      }
    }

    if (typeof THREE === 'undefined' || !isWebGLAvailable()) {
      if (fallback) fallback.style.display = 'block';
      container.style.display = 'none';
      return;
    }

    // 2. Scene, Camera, and Renderer Setup
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 440;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x121d15);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 1.8, 6.2);

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.domElement.className = 'threejs-soil-canvas';
      container.appendChild(renderer.domElement);
    } catch (err) {
      if (fallback) fallback.style.display = 'block';
      container.style.display = 'none';
      return;
    }

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xfff8ea, 0.9);
    dirLight.position.set(4, 8, 5);
    dirLight.castShadow = true;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x81c784, 0.35);
    fillLight.position.set(-4, -2, -3);
    scene.add(fillLight);

    // 4. Construct 3D Soil Cross-Section Block
    const soilGroup = new THREE.Group();
    scene.add(soilGroup);

    const blockWidth = 2.8;
    const blockDepth = 2.4;

    // Horizon Dimensions & Colors (Scientific Pedology Horizons)
    const horizons = [
      { name: 'O-Horizon (Organic / Turf)', height: 0.22, color: 0x2e7d32, roughness: 0.9, y: 0.8 },
      { name: 'A-Horizon (Fertile Topsoil)', height: 0.75, color: 0x4a2e18, roughness: 0.85, y: 0.315 },
      { name: 'B-Horizon (Clay Subsoil)', height: 0.75, color: 0x7c4a27, roughness: 0.8, y: -0.435 },
      { name: 'C-Horizon (Parent Material)', height: 0.65, color: 0x93765b, roughness: 0.95, y: -1.135 }
    ];

    horizons.forEach((h) => {
      const geom = new THREE.BoxGeometry(blockWidth, h.height, blockDepth);
      const mat = new THREE.MeshStandardMaterial({
        color: h.color,
        roughness: h.roughness,
        metalness: 0.05
      });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.y = h.y;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      soilGroup.add(mesh);
    });

    // 5. Add Surface Grass & Sprout Plants
    const plantGroup = new THREE.Group();
    soilGroup.add(plantGroup);

    // Main Crop Stems & Leaves
    const stemGeom = new THREE.CylinderGeometry(0.025, 0.035, 0.55, 8);
    const stemMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.6 });
    const leafGeom = new THREE.ConeGeometry(0.12, 0.38, 4);
    const leafMat = new THREE.MeshStandardMaterial({ color: 0x16a34a, roughness: 0.5 });

    // Center Crop Plant
    const centerStem = new THREE.Mesh(stemGeom, stemMat);
    centerStem.position.set(0, 1.18, 0);
    plantGroup.add(centerStem);

    const leafLeft = new THREE.Mesh(leafGeom, leafMat);
    leafLeft.position.set(-0.16, 1.35, 0);
    leafLeft.rotation.z = Math.PI / 4;
    leafLeft.scale.set(1, 1, 0.25);
    plantGroup.add(leafLeft);

    const leafRight = new THREE.Mesh(leafGeom, leafMat);
    leafRight.position.set(0.16, 1.4, 0);
    leafRight.rotation.z = -Math.PI / 3.8;
    leafRight.scale.set(1, 1, 0.25);
    plantGroup.add(leafRight);

    // Companion Field Seedlings
    const seedlingPositions = [
      [-0.7, 0.95, -0.4],
      [0.65, 0.95, 0.5],
      [-0.55, 0.95, 0.45],
      [0.8, 0.95, -0.3]
    ];

    seedlingPositions.forEach(([x, y, z]) => {
      const s = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.024, 0.32, 6), stemMat);
      s.position.set(x, y + 0.16, z);
      plantGroup.add(s);

      const l = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.22, 4), leafMat);
      l.position.set(x + 0.06, y + 0.28, z);
      l.rotation.z = -Math.PI / 4;
      l.scale.set(1, 1, 0.25);
      plantGroup.add(l);
    });

    // 6. Root System Architecture (Descending Fibrous Taproots)
    const rootMat = new THREE.MeshStandardMaterial({ color: 0xf5f3ee, roughness: 0.5 });

    function createRootBranch(startX, startY, startZ, length, angleZ, angleX, radius = 0.02) {
      const geom = new THREE.CylinderGeometry(radius * 0.5, radius, length, 6);
      const mesh = new THREE.Mesh(geom, rootMat);
      mesh.position.set(startX, startY - length / 2, startZ);
      mesh.rotation.z = angleZ;
      mesh.rotation.x = angleX;
      return mesh;
    }

    // Taproot descending through A and B horizons
    soilGroup.add(createRootBranch(0, 0.9, 0, 0.75, 0.05, -0.04, 0.035));
    soilGroup.add(createRootBranch(0.04, 0.18, -0.03, 0.65, -0.06, 0.08, 0.025));
    soilGroup.add(createRootBranch(0.01, -0.45, 0.02, 0.55, 0.04, -0.05, 0.018));

    // Lateral roots penetrating topsoil
    soilGroup.add(createRootBranch(0.02, 0.75, 0, 0.45, -Math.PI / 6, 0.2, 0.02));
    soilGroup.add(createRootBranch(-0.02, 0.65, 0, 0.48, Math.PI / 5, -0.25, 0.02));
    soilGroup.add(createRootBranch(0.15, 0.5, 0.1, 0.35, -Math.PI / 4, 0.3, 0.015));
    soilGroup.add(createRootBranch(-0.18, 0.42, -0.1, 0.38, Math.PI / 4.2, -0.2, 0.015));

    // Fine roots reaching subsoil
    soilGroup.add(createRootBranch(0.08, -0.1, -0.05, 0.38, -Math.PI / 5, 0.15, 0.015));
    soilGroup.add(createRootBranch(-0.06, -0.2, 0.05, 0.36, Math.PI / 4.5, -0.1, 0.014));

    // 7. Interactive Drag / Orbit Rotation
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    const rotationVelocity = { x: 0, y: 0 };

    function onPointerDown(e) {
      isDragging = true;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      previousMousePosition = { x: clientX, y: clientY };
    }

    function onPointerMove(e) {
      if (!isDragging) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;

      const deltaX = clientX - previousMousePosition.x;
      const deltaY = clientY - previousMousePosition.y;

      soilGroup.rotation.y += deltaX * 0.01;
      soilGroup.rotation.x = Math.max(-0.4, Math.min(0.4, soilGroup.rotation.x + deltaY * 0.008));

      previousMousePosition = { x: clientX, y: clientY };
    }

    function onPointerUp() {
      isDragging = false;
    }

    const canvasEl = renderer.domElement;
    canvasEl.addEventListener('mousedown', onPointerDown);
    canvasEl.addEventListener('touchstart', onPointerDown, { passive: true });
    window.addEventListener('mousemove', onPointerMove);
    window.addEventListener('touchmove', onPointerMove, { passive: true });
    window.addEventListener('mouseup', onPointerUp);
    window.addEventListener('touchend', onPointerUp);

    // Initial orientation for attractive isometric view
    soilGroup.rotation.y = 0.55;
    soilGroup.rotation.x = 0.22;

    // 8. Motion Preference Check
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 9. Intersection Observer (Pause Rendering When Not Visible)
    let isVisible = true;
    let animationFrameId = null;

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          isVisible = entry.isIntersecting;
          if (isVisible && !animationFrameId) {
            animate();
          }
        });
      }, { threshold: 0.1 });
      observer.observe(container);
    }

    // 10. Animation Loop
    function animate() {
      if (!isVisible) {
        animationFrameId = null;
        return;
      }

      // Gentle auto-rotation only if not dragging and user has not requested reduced motion
      if (!isDragging && !prefersReducedMotion) {
        soilGroup.rotation.y += 0.0035;
      }

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    }

    animate();

    // 11. Responsive Canvas Resize Handler
    window.addEventListener('resize', () => {
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight || 440;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    });
  });
})();

