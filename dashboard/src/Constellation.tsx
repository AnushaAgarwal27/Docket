import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { Activity } from "./data";
import { actionLabel, time } from "./data";

// The live 3D view for the Tracks tab. The Convex student file sits at the center, the four Fetch.ai
// agents orbit it, and the outside services sit further out. Every activity row an agent writes sends a
// pulse of light from that agent into the file, so the motion on screen is the system's real activity.
// On load it replays the most recent actions so the scene is alive when someone walks up.

type NodeDef = { id: string; label: string; color: number; ring: "agent" | "outer"; angle: number; link?: string };
const NODES: NodeDef[] = [
  { id: "coordinator", label: "Coordinator", color: 0xa9b6ff, ring: "agent", angle: 0 },
  { id: "ledger", label: "Ledger", color: 0x74ddb0, ring: "agent", angle: Math.PI / 2 },
  { id: "tax", label: "Rules", color: 0xf0b860, ring: "agent", angle: Math.PI },
  { id: "caseworker", label: "Caseworker", color: 0xff8a80, ring: "agent", angle: (3 * Math.PI) / 2 },
  { id: "asi", label: "ASI:One", color: 0x8d96a8, ring: "outer", angle: 0.35, link: "coordinator" },
  { id: "nessie", label: "Capital One Nessie", color: 0x8d96a8, ring: "outer", angle: Math.PI / 2 + 0.35, link: "ledger" },
  { id: "voice", label: "Cartesia voice", color: 0xff8a80, ring: "outer", angle: (3 * Math.PI) / 2 + 0.35, link: "caseworker" },
];
const AGENT_R = 3.2, OUTER_R = 5.0, ORBIT_SPEED = 0.05;
const from = (agent: string) => (NODES.some((n) => n.id === agent) ? agent : null); // setup rows (seed) have no node

function glowTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d")!;
  const r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, "rgba(255,255,255,1)");
  r.addColorStop(0.25, "rgba(255,255,255,0.55)");
  r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r;
  g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function Constellation({ feed }: { feed: Activity[] | undefined }) {
  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<Record<string, HTMLDivElement | null>>({});
  const queue = useRef<{ agent: string; row: Activity }[]>([]);
  const seen = useRef<Set<string>>(new Set());
  const [ticker, setTicker] = useState<{ text: string; live: boolean } | null>(null);
  const reduce = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

  // New rows become pulses. The first batch is a replay of recent history, labelled as such.
  useEffect(() => {
    if (!feed) return;
    const fresh = feed.filter((r) => !seen.current.has(r._id));
    if (!fresh.length) return;
    const replay = seen.current.size === 0;
    fresh.forEach((r) => seen.current.add(r._id));
    const chronological = (replay ? fresh.slice(0, 14) : fresh).slice().reverse();
    for (const row of chronological) {
      const agent = from(row.agent);
      if (agent) queue.current.push({ agent, row });
    }
    setTicker({ text: replay ? "Replaying the latest actions" : "Live", live: !replay });
  }, [feed]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 4.2, 12.5);
    camera.lookAt(0, -0.4, 0);
    const world = new THREE.Group();
    world.rotation.x = 0.32;
    scene.add(world);
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const key = new THREE.PointLight(0xa9b6ff, 40, 30);
    key.position.set(0, 4, 6);
    scene.add(key);
    const glow = glowTexture();

    // Core: the shared student file.
    const coreMat = new THREE.MeshStandardMaterial({ color: 0x2a3160, emissive: 0x5a66d6, emissiveIntensity: 0.6, roughness: 0.35, metalness: 0.2, flatShading: true });
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.05, 1), coreMat);
    const coreWire = new THREE.LineSegments(new THREE.EdgesGeometry(core.geometry), new THREE.LineBasicMaterial({ color: 0xc9d1ff, transparent: true, opacity: 0.55 }));
    core.add(coreWire);
    const coreGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: 0x8c98ff, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }));
    coreGlow.scale.setScalar(5.2);
    world.add(core, coreGlow);

    // Orbit rings.
    for (const r of [AGENT_R, OUTER_R]) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(r, 0.006, 6, 160), new THREE.MeshBasicMaterial({ color: 0x5d6678, transparent: true, opacity: r === AGENT_R ? 0.6 : 0.3 }));
      ring.rotation.x = Math.PI / 2;
      world.add(ring);
    }

    // Nodes, their glows and the links that carry pulses.
    const nodes: Record<string, { mesh: THREE.Mesh; halo: THREE.Sprite; def: NodeDef; pos: THREE.Vector3; flash: number }> = {};
    for (const def of NODES) {
      const size = def.ring === "agent" ? 0.26 : 0.17;
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(size, 24, 16), new THREE.MeshStandardMaterial({ color: def.color, emissive: def.color, emissiveIntensity: def.ring === "agent" ? 0.9 : 0.35, roughness: 0.4 }));
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: def.color, transparent: true, opacity: def.ring === "agent" ? 0.45 : 0.2, blending: THREE.AdditiveBlending, depthWrite: false }));
      halo.scale.setScalar(size * 7);
      world.add(mesh, halo);
      nodes[def.id] = { mesh, halo, def, pos: new THREE.Vector3(), flash: 0 };
    }
    const linkPairs = NODES.map((d) => [d.id, d.link ?? "core"] as const);
    const linkGeo = new THREE.BufferGeometry();
    linkGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(linkPairs.length * 6), 3));
    const links = new THREE.LineSegments(linkGeo, new THREE.LineBasicMaterial({ color: 0x8d96a8, transparent: true, opacity: 0.28 }));
    world.add(links);

    // Distant dust for depth.
    const dustGeo = new THREE.BufferGeometry();
    const dust = new Float32Array(900);
    for (let i = 0; i < 300; i++) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(9 + Math.random() * 9);
      dust.set([v.x, v.y, v.z], i * 3);
    }
    dustGeo.setAttribute("position", new THREE.BufferAttribute(dust, 3));
    const dustPts = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0x8d96a8, size: 0.04, transparent: true, opacity: 0.5 }));
    scene.add(dustPts);

    // Pulses and ripples.
    type Pulse = { sprite: THREE.Sprite; path: THREE.Vector3[]; t: number; agent: string };
    const pulses: Pulse[] = [];
    const ripples: { mesh: THREE.Mesh; t: number }[] = [];
    let coreFlash = 0;
    const spawn = (agent: string) => {
      const n = nodes[agent];
      if (!n) return;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: n.def.color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
      sprite.scale.setScalar(0.55);
      world.add(sprite);
      const path = n.def.link ? [nodes[n.def.link].pos, new THREE.Vector3()] : [new THREE.Vector3()];
      pulses.push({ sprite, path, t: 0, agent });
      n.flash = 1;
    };

    // Drag to rotate.
    let dragging = false, lastX = 0, lastY = 0, yaw = 0, pitch = 0.22, idle = 0;
    const down = (e: PointerEvent) => { dragging = true; lastX = e.clientX; lastY = e.clientY; el.setPointerCapture(e.pointerId); };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      yaw += (e.clientX - lastX) * 0.006;
      pitch = Math.max(-0.2, Math.min(1.1, pitch + (e.clientY - lastY) * 0.004));
      lastX = e.clientX; lastY = e.clientY; idle = 0;
    };
    const up = () => { dragging = false; };
    el.addEventListener("pointerdown", down);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", up);
    el.addEventListener("pointerleave", up);

    const size = () => {
      const w = el.clientWidth, h = el.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.position.set(0, 4.2, w < 600 ? 17 : 10.8);
      camera.lookAt(0, -0.4, 0);
      camera.updateProjectionMatrix();
    };
    size();
    const ro = new ResizeObserver(size);
    ro.observe(el);

    const clock = new THREE.Clock();
    const tmp = new THREE.Vector3();
    let spawnWait = 0, frame = 0, running = true;
    const tick = () => {
      if (!running) return;
      const dt = Math.min(clock.getDelta(), 0.05);
      const t = clock.elapsedTime;
      const motion = reduce ? 0 : 1;
      idle += dt;
      if (!dragging && idle > 2) yaw += dt * 0.04 * motion;
      world.rotation.y = yaw;
      world.rotation.x = pitch;
      core.rotation.y += dt * 0.25 * motion;
      core.rotation.x += dt * 0.08 * motion;
      dustPts.rotation.y += dt * 0.01 * motion;

      for (const id in nodes) {
        const n = nodes[id];
        const r = n.def.ring === "agent" ? AGENT_R : OUTER_R;
        const a = n.def.angle + (n.def.ring === "agent" ? t * ORBIT_SPEED * motion : t * ORBIT_SPEED * 0.5 * motion);
        n.pos.set(Math.cos(a) * r, n.def.ring === "agent" ? Math.sin(t * 0.6 + n.def.angle) * 0.18 * motion : 0, Math.sin(a) * r);
        n.mesh.position.copy(n.pos);
        n.halo.position.copy(n.pos);
        n.flash = Math.max(0, n.flash - dt * 1.5);
        n.halo.scale.setScalar((n.def.ring === "agent" ? 1.8 : 1.2) * (1 + n.flash * 1.2));
      }
      const pos = linkGeo.attributes.position as THREE.BufferAttribute;
      linkPairs.forEach(([a, b], i) => {
        const p = nodes[a].pos, q = b === "core" ? tmp.set(0, 0, 0) : nodes[b].pos;
        pos.setXYZ(i * 2, p.x, p.y, p.z);
        pos.setXYZ(i * 2 + 1, q.x, q.y, q.z);
      });
      pos.needsUpdate = true;

      // Release queued activity as pulses, one at a time so each is visible.
      spawnWait -= dt;
      if (!reduce && spawnWait <= 0 && queue.current.length) {
        const next = queue.current.shift()!;
        spawn(next.agent);
        setTicker((cur) => ({ text: `${labelFor(next.row.agent)} · ${actionLabel(next.row.action)} · ${time(next.row.at)}`, live: cur?.live ?? false }));
        spawnWait = queue.current.length > 6 ? 0.35 : 0.7;
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.t += dt / 1.1;
        const start = nodes[p.agent].pos;
        const pts = [start, ...p.path];
        const seg = Math.min(pts.length - 2, Math.floor(p.t * (pts.length - 1)));
        const local = p.t * (pts.length - 1) - seg;
        const e = local < 0.5 ? 2 * local * local : 1 - Math.pow(-2 * local + 2, 2) / 2;
        p.sprite.position.lerpVectors(pts[seg], pts[seg + 1], Math.min(1, e));
        if (p.t >= 1) {
          world.remove(p.sprite);
          (p.sprite.material as THREE.SpriteMaterial).dispose();
          pulses.splice(i, 1);
          coreFlash = 1;
          const ripple = new THREE.Mesh(new THREE.RingGeometry(1.1, 1.16, 64), new THREE.MeshBasicMaterial({ color: nodes[p.agent].def.color, transparent: true, side: THREE.DoubleSide }));
          ripple.rotation.x = Math.PI / 2;
          world.add(ripple);
          ripples.push({ mesh: ripple, t: 0 });
        }
      }
      for (let i = ripples.length - 1; i >= 0; i--) {
        const r = ripples[i];
        r.t += dt / 1.4;
        r.mesh.scale.setScalar(1 + r.t * 1.8);
        (r.mesh.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.7 * (1 - r.t));
        if (r.t >= 1) { world.remove(r.mesh); r.mesh.geometry.dispose(); (r.mesh.material as THREE.Material).dispose(); ripples.splice(i, 1); }
      }
      coreFlash = Math.max(0, coreFlash - dt * 1.6);
      coreMat.emissiveIntensity = 0.6 + coreFlash * 1.1;
      coreGlow.scale.setScalar(5.2 + coreFlash * 1.6);

      renderer.render(scene, camera);

      // Labels follow their nodes on screen.
      if (frame++ % 2 === 0) {
        const w = el.clientWidth, h = el.clientHeight;
        for (const id in nodes) {
          const lab = labels.current[id];
          if (!lab) continue;
          nodes[id].mesh.getWorldPosition(tmp).project(camera);
          lab.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h + 16}px) translateX(-50%)`;
          lab.style.opacity = tmp.z < 1 ? "1" : "0";
        }
        const coreLab = labels.current.core;
        if (coreLab) {
          core.getWorldPosition(tmp).project(camera);
          coreLab.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h + 64}px) translateX(-50%)`;
        }
      }
      if (!reduce) requestAnimationFrame(tick);
    };
    tick();
    if (reduce) renderer.render(scene, camera);

    return () => {
      running = false;
      ro.disconnect();
      el.removeEventListener("pointerdown", down);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", up);
      el.removeEventListener("pointerleave", up);
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        m.geometry?.dispose?.();
        const mat = m.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose?.();
      });
      glow.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [reduce]);

  return (
    <section className="panel constellation" aria-label="Live 3D view of the agents writing to the shared student file">
      <div className="cs-stage" ref={host}>
        {NODES.map((n) => (
          <div key={n.id} className={`cs-label ${n.ring}`} ref={(d) => { labels.current[n.id] = d; }}>{n.label}</div>
        ))}
        <div className="cs-label core" ref={(d) => { labels.current.core = d; }}>Convex · shared student file</div>
      </div>
      <div className="cs-caption">
        <span className={`cs-live ${ticker?.live ? "on" : ""}`}><i />{ticker?.live ? "Live" : "Replay"}</span>
        <span className="cs-text num">{ticker?.text ?? "Waiting for the first action"}</span>
        <span className="cs-hint">Each pulse is one row an agent wrote. Drag to rotate.</span>
      </div>
    </section>
  );
}

const labelFor = (agent: string) =>
  ({ coordinator: "Coordinator", ledger: "Ledger", tax: "Rules", caseworker: "Caseworker", voice: "Cartesia voice" } as Record<string, string>)[agent] ?? agent;
