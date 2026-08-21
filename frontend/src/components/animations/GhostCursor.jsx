/**
 * GhostCursor.jsx
 * ---------------
 * A full-screen Three.js canvas that draws a luminous ghost-cursor trail
 * behind the mouse pointer.  The canvas sits at z-index 0 with
 * pointer-events: none, so it never blocks clicks or keyboard input.
 *
 * Props
 * -----
 * color        – hex string  default "#38bdf8"  (sky-400)
 * trailLength  – integer     default 80          number of trail points
 * inertia      – 0…1         default 0.12        lower = smoother / lazier follow
 * bloomStrength– 0…1         default 0.9         opacity of the head glow disc
 * zIndex       – integer     default 0
 */

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function GhostCursor({
  color        = '#38bdf8',
  trailLength  = 80,
  inertia      = 0.12,
  bloomStrength= 0.9,
  zIndex       = 0,
}) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // ── Renderer ─────────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);           // fully transparent background
    mount.appendChild(renderer.domElement);

    // ── Scene & Camera ────────────────────────────────────────────────────────
    const scene  = new THREE.Scene();
    // Orthographic camera maps 1:1 to CSS pixels (origin top-left)
    const camera = new THREE.OrthographicCamera(
      0, window.innerWidth,
      0, -window.innerHeight,   // flip Y so y=0 is top
      -1, 1
    );

    // ── Trail data ────────────────────────────────────────────────────────────
    const maxPts     = Math.max(trailLength, 10);
    const positions  = new Float32Array(maxPts * 3);   // x, y, z per point
    const alphas     = new Float32Array(maxPts);        // per-point opacity

    // Start all points off-screen
    for (let i = 0; i < maxPts; i++) {
      positions[i * 3]     = -9999;
      positions[i * 3 + 1] = -9999;
      positions[i * 3 + 2] = 0;
      alphas[i]            = 0;
    }

    // ── Trail geometry (Points) ───────────────────────────────────────────────
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('alpha',    new THREE.BufferAttribute(alphas,    1));

    const threeColor = new THREE.Color(color);

    // Custom shader so each point fades along the tail
    const material = new THREE.ShaderMaterial({
      uniforms: {
        uColor:     { value: threeColor },
        uPointSize: { value: 6.0 * window.devicePixelRatio },
      },
      vertexShader: /* glsl */`
        attribute float alpha;
        varying   float vAlpha;
        uniform   float uPointSize;
        void main() {
          vAlpha      = alpha;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = uPointSize * (vAlpha + 0.15);
        }
      `,
      fragmentShader: /* glsl */`
        uniform vec3  uColor;
        varying float vAlpha;
        void main() {
          // Soft circular disc
          float d = length(gl_PointCoord - 0.5) * 2.0;
          if (d > 1.0) discard;
          float alpha = vAlpha * (1.0 - smoothstep(0.3, 1.0, d));
          gl_FragColor = vec4(uColor, alpha);
        }
      `,
      transparent:  true,
      depthWrite:   false,
      blending:     THREE.AdditiveBlending,   // additive = glow / bloom look
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // ── Head glow disc (always at cursor tip) ─────────────────────────────────
    const glowGeo = new THREE.CircleGeometry(14, 32);
    const glowMat = new THREE.MeshBasicMaterial({
      color:       threeColor,
      transparent: true,
      opacity:     bloomStrength * 0.35,
      depthWrite:  false,
      blending:    THREE.AdditiveBlending,
    });
    const glowMesh = new THREE.Mesh(glowGeo, glowMat);
    scene.add(glowMesh);

    // ── State ─────────────────────────────────────────────────────────────────
    // mouse: raw CSS pixel position (updated on mousemove)
    // cursor: smoothly interpolated position (updated per frame)
    const mouse  = { x: -9999, y: -9999 };
    const cursor = { x: -9999, y: -9999 };
    const trail  = Array.from({ length: maxPts }, () => ({ x: -9999, y: -9999 }));

    const onMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    window.addEventListener('mousemove', onMouseMove);

    // ── Animation loop ────────────────────────────────────────────────────────
    let frameId;
    const animate = () => {
      frameId = requestAnimationFrame(animate);

      // Lerp cursor toward raw mouse position (inertia controls lag)
      cursor.x += (mouse.x - cursor.x) * inertia;
      cursor.y += (mouse.y - cursor.y) * inertia;

      // Shift trail: newest point at index 0
      for (let i = maxPts - 1; i > 0; i--) {
        trail[i].x = trail[i - 1].x;
        trail[i].y = trail[i - 1].y;
      }
      trail[0].x = cursor.x;
      trail[0].y = cursor.y;

      // Write trail into GPU buffer
      for (let i = 0; i < maxPts; i++) {
        const t = i / (maxPts - 1);            // 0 (head) ... 1 (tail)
        // Exponential fade: head is bright, tail fades to zero
        alphas[i]            = Math.pow(1 - t, 1.8);
        positions[i * 3]     =  trail[i].x;
        // Three.js origin is bottom-left; camera is flipped so y=0 is top
        positions[i * 3 + 1] = -trail[i].y;
        positions[i * 3 + 2] = 0;
      }

      geometry.attributes.position.needsUpdate = true;
      geometry.attributes.alpha.needsUpdate    = true;

      // Move glow head
      glowMesh.position.set(cursor.x, -cursor.y, 0);

      renderer.render(scene, camera);
    };
    animate();

    // ── Resize handler ────────────────────────────────────────────────────────
    const onResize = () => {
      renderer.setSize(window.innerWidth, window.innerHeight);
      camera.right  =  window.innerWidth;
      camera.bottom = -window.innerHeight;
      camera.updateProjectionMatrix();
    };
    window.addEventListener('resize', onResize);

    // ── Cleanup ───────────────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize',    onResize);

      // Dispose all Three.js allocations to avoid GPU/memory leaks
      geometry.dispose();
      material.dispose();
      glowGeo.dispose();
      glowMat.dispose();
      renderer.dispose();

      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  // Props that change the Three.js scene require a full re-init
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [color, trailLength, inertia, bloomStrength]);

  return (
    <div
      ref={mountRef}
      aria-hidden="true"
      style={{
        position:      'fixed',
        inset:         0,
        zIndex,
        pointerEvents: 'none',   // NEVER intercepts mouse events
        overflow:      'hidden',
      }}
    />
  );
}
