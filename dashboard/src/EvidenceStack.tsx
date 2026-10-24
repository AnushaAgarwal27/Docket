import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Paystub } from "./data";
import { day, usd } from "./data";

// The Overview hero: Priya's real paystubs fanned out in 3D. The Social Security and Medicare lines glow,
// and a stream of light rises from them into an orb holding the total withheld, so the money leaving each
// paycheck is visible. When the refund lands the orb turns green and the stream stops. Hover lifts a
// paystub; click selects it for the paper trail. Every sheet is drawn from the live paystub rows.

const W = 2.1, H = 2.75; // sheet size in world units
const ROW = { hours0: 0.4, hours1: 0.46, gross: 0.56, ss: 0.63, med: 0.7, net: 0.82 }; // row centers, fraction of height
const AMBER = 0xf0b860, MINT = 0x74ddb0, RED = 0xff8a80;

function money(c: number) { return usd(c); }

function drawSheet(stub: Paystub, index: number, total: number, flagged: boolean): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = 512; c.height = Math.round(512 * (H / W));
  const g = c.getContext("2d")!;
  const w = c.width, h = c.height, pad = 34;
  g.fillStyle = "#f1f3f7"; g.fillRect(0, 0, w, h);
  g.fillStyle = "#d5dae3";
  for (let x = 0; x < w; x += 14) g.fillRect(x, 0, 8, 6); // perforated top edge
  g.fillStyle = "#1a2131";
  g.font = "600 25px Georgia, 'Times New Roman', serif";
  g.fillText(stub.employer, pad, 58);
  g.font = "400 18px system-ui, -apple-system, sans-serif";
  g.fillStyle = "#5e6779";
  g.fillText(`Earnings statement · No. ${String(index + 1).padStart(2, "0")} of ${total}`, pad, 86);
  g.fillText(`${day(stub.periodStart)} – ${day(stub.periodEnd)}, ${stub.periodEnd.slice(0, 4)}`, pad, 112);
  g.fillStyle = "#1a2131"; g.fillRect(pad, 132, w - 2 * pad, 2);
  const row = (f: number, label: string, value: string, hl?: string, bold = false) => {
    const y = f * h;
    if (hl) { g.fillStyle = hl; g.beginPath(); g.roundRect(pad - 10, y - 22, w - 2 * pad + 20, 38, 7); g.fill(); }
    g.fillStyle = "#1a2131";
    g.font = `${bold ? 700 : 400} 21px system-ui, -apple-system, sans-serif`;
    g.fillText(label, pad, y + 6);
    const tw = g.measureText(value).width;
    g.fillText(value, w - pad - tw, y + 6);
  };
  stub.hoursByWeek.slice(0, 2).forEach((hrs, k) => row(k ? ROW.hours1 : ROW.hours0, `Hours, week ${k + 1}`, hrs.toFixed(2), hrs > 20 ? "#fbd1cc" : undefined));
  row(ROW.gross, "Gross pay", money(stub.grossCents), undefined, true);
  row(ROW.ss, "Social Security", `−${money(stub.ssCents)}`, flagged ? "#fbe2ab" : undefined);
  row(ROW.med, "Medicare", `−${money(stub.medicareCents)}`, flagged ? "#fbe2ab" : undefined);
  g.fillStyle = "#1a2131"; g.fillRect(pad, ROW.net * h - 30, w - 2 * pad, 2);
  row(ROW.net, "Net pay", money(stub.netCents), undefined, true);
  g.fillStyle = "#8d96a8"; g.font = "400 15px system-ui, sans-serif";
  g.fillText("Synthetic demo document", pad, h - 26);
  return c;
}

function glowTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.3, "rgba(255,255,255,0.5)"); r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

export function EvidenceStack({ stubs, flagged, recovered, totalCents, selected, onSelect }: {
  stubs: Paystub[]; flagged: boolean; recovered: boolean; totalCents: number; selected: number; onSelect: (k: number) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const orbLabel = useRef<HTMLDivElement>(null);
  const state = useRef({ selected, recovered, flagged, onSelect });
  state.current = { selected, recovered, flagged, onSelect };
  const key = stubs.map((s) => `${s._id}:${s.ssCents}:${s.medicareCents}:${s.hoursByWeek.join("+")}`).join("|") + `|${flagged}`;

  useEffect(() => {
    const el = host.current;
    if (!el || !stubs.length) return;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    const base = new THREE.Vector3(0, 0.9, 8.6);
    const target = new THREE.Vector3(0, 0.95, 0);
    scene.add(new THREE.AmbientLight(0xffffff, 1.6));
    const glow = glowTexture();

    // Fanned sheets, pivoting at the bottom like a hand of cards.
    const n = stubs.length;
    const spread = Math.min(0.85, 0.12 * n);
    const sheets = stubs.map((stub, i) => {
      const tex = new THREE.CanvasTexture(drawSheet(stub, i, n, flagged));
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide }));
      mesh.position.y = H / 2;
      const edge = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry), new THREE.LineBasicMaterial({ color: 0xa9b6ff, transparent: true, opacity: 0 }));
      mesh.add(edge);
      const pivot = new THREE.Group();
      const a = n > 1 ? -spread / 2 + (spread * i) / (n - 1) : 0;
      pivot.position.set(a * 1.4, -1.35, i * 0.012);
      pivot.rotation.z = -a;
      pivot.add(mesh);
      scene.add(pivot);
      return { pivot, mesh, edge, tex, angle: a, lift: 0, over: stub.hoursByWeek.some((h) => h > 20) };
    });

    // The orb: total withheld (amber) or recovered (mint).
    const orbMat = new THREE.MeshStandardMaterial({ color: 0x3a2c12, emissive: AMBER, emissiveIntensity: 0.9, roughness: 0.3 });
    const orb = new THREE.Mesh(new THREE.IcosahedronGeometry(0.42, 3), orbMat);
    orb.position.set(0, 2.3, 0.4);
    const orbGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: AMBER, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
    orbGlow.scale.setScalar(2.6);
    orbGlow.position.copy(orb.position);
    const halo = new THREE.Mesh(new THREE.TorusGeometry(0.75, 0.008, 6, 96), new THREE.MeshBasicMaterial({ color: AMBER, transparent: true, opacity: 0.5 }));
    halo.position.copy(orb.position);
    scene.add(orb, orbGlow, halo);

    // The stream: particles leave each sheet's withheld lines and rise into the orb.
    const COUNT = 220;
    const pts = new Float32Array(COUNT * 3);
    const life = Array.from({ length: COUNT }, (_, k) => ({ sheet: k % n, row: k % 2 ? ROW.ss : ROW.med, t: Math.random(), speed: 0.25 + Math.random() * 0.25, wobble: Math.random() * 6.28 }));
    const streamGeo = new THREE.BufferGeometry();
    streamGeo.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    const streamMat = new THREE.PointsMaterial({ map: glow, color: AMBER, size: 0.12, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false });
    const stream = new THREE.Points(streamGeo, streamMat);
    scene.add(stream);

    const ray = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-9, -9);
    const parallax = new THREE.Vector2();
    let hovered = -1;
    const pointer = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      parallax.set(mouse.x, mouse.y);
    };
    const leave = () => { mouse.set(-9, -9); parallax.set(0, 0); };
    const click = () => { if (hovered >= 0) state.current.onSelect(hovered); };
    el.addEventListener("pointermove", pointer);
    el.addEventListener("pointerleave", leave);
    el.addEventListener("click", click);

    const size = () => {
      const w = el.clientWidth, h = el.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      base.z = w < 520 ? 11 : 8.6;
      camera.updateProjectionMatrix();
    };
    size();
    const ro = new ResizeObserver(size);
    ro.observe(el);

    const clock = new THREE.Clock();
    const tmp = new THREE.Vector3(), from = new THREE.Vector3(), ctrl = new THREE.Vector3();
    let running = true, colorMix = state.current.recovered ? 1 : 0;
    const amber = new THREE.Color(AMBER), mint = new THREE.Color(MINT), mixed = new THREE.Color();
    const tick = () => {
      if (!running) return;
      const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime, m = reduce ? 0 : 1;
      const { selected: sel, recovered, flagged: fl } = state.current;

      camera.position.set(base.x + parallax.x * 0.55 * m, base.y + parallax.y * 0.3 * m, base.z);
      camera.lookAt(target);

      ray.setFromCamera(mouse, camera);
      const hit = ray.intersectObjects(sheets.map((s) => s.mesh), false)[0];
      hovered = hit ? sheets.findIndex((s) => s.mesh === hit.object) : -1;
      el.style.cursor = hovered >= 0 ? "pointer" : "default";

      sheets.forEach((s, i) => {
        const goal = i === sel ? 1 : i === hovered ? 0.6 : 0;
        s.lift += (goal - s.lift) * Math.min(1, dt * 8);
        s.pivot.position.y = -1.35 + s.lift * 0.42;
        s.pivot.position.z = i * 0.012 + s.lift * 0.35;
        s.pivot.rotation.z = -s.angle * (1 - s.lift * 0.35) + Math.sin(t * 0.7 + i) * 0.006 * m;
        (s.edge.material as THREE.LineBasicMaterial).opacity = i === sel ? 0.9 : i === hovered ? 0.45 : 0;
        (s.edge.material as THREE.LineBasicMaterial).color.set(s.over && i === sel ? RED : 0xa9b6ff);
      });

      colorMix += ((recovered ? 1 : 0) - colorMix) * Math.min(1, dt * 2);
      mixed.copy(amber).lerp(mint, colorMix);
      orbMat.emissive.copy(mixed);
      (orbGlow.material as THREE.SpriteMaterial).color.copy(mixed);
      (halo.material as THREE.MeshBasicMaterial).color.copy(mixed);
      orb.rotation.y += dt * 0.4 * m;
      halo.rotation.x = Math.PI / 2 + Math.sin(t * 0.5) * 0.25 * m;
      halo.rotation.y = t * 0.3 * m;
      const pulse = 1 + Math.sin(t * 2.2) * 0.04 * m;
      orbGlow.scale.setScalar(2.6 * pulse);

      // Stream runs while money is still withheld; it fades out once recovered.
      streamMat.opacity = fl ? 0.95 * (1 - colorMix) : 0;
      if (fl && colorMix < 0.99) {
        for (let k = 0; k < COUNT; k++) {
          const p = life[k];
          p.t += dt * p.speed * m;
          if (p.t > 1) { p.t -= 1; p.sheet = Math.floor(Math.random() * n); p.row = Math.random() < 0.5 ? ROW.ss : ROW.med; }
          const s = sheets[p.sheet];
          from.set(0.72 + (Math.random() - 0.5) * 0.25, (0.5 - p.row) * H, 0.01);
          s.mesh.localToWorld(from);
          ctrl.set(from.x * 0.4, from.y + 1.6, 0.9);
          const e = p.t, u = 1 - e;
          tmp.set(
            u * u * from.x + 2 * u * e * ctrl.x + e * e * orb.position.x + Math.sin(p.wobble + t * 3) * 0.04 * u,
            u * u * from.y + 2 * u * e * ctrl.y + e * e * orb.position.y,
            u * u * from.z + 2 * u * e * ctrl.z + e * e * orb.position.z,
          );
          pts.set([tmp.x, tmp.y, tmp.z], k * 3);
        }
        (streamGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
      }

      renderer.render(scene, camera);
      const lab = orbLabel.current;
      if (lab) {
        tmp.copy(orb.position).project(camera);
        lab.style.transform = `translate(${((tmp.x + 1) / 2) * el.clientWidth + (el.clientWidth < 520 ? -40 : 58)}px, ${((1 - tmp.y) / 2) * el.clientHeight + (el.clientWidth < 520 ? -88 : -26)}px)`;
      }
      requestAnimationFrame(tick);
    };
    // Sheets are drawn with web fonts once they load.
    document.fonts?.ready.then(() => sheets.forEach((s, i) => { s.tex.image = drawSheet(stubs[i], i, n, flagged); s.tex.needsUpdate = true; }));
    tick();

    return () => {
      running = false;
      ro.disconnect();
      el.removeEventListener("pointermove", pointer);
      el.removeEventListener("pointerleave", leave);
      el.removeEventListener("click", click);
      scene.traverse((o) => {
        const mesh = o as THREE.Mesh;
        mesh.geometry?.dispose?.();
        const mat = mesh.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose?.();
      });
      sheets.forEach((s) => s.tex.dispose());
      glow.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
    // Rebuild only when the paystub data itself changes; selection and refund state are read live.
  }, [key]);

  return (
    <div className="es-stage" ref={host} role="img" aria-label={`${stubs.length} paystubs; ${usd(totalCents)} ${recovered ? "recovered" : "withheld"}. Click a paystub to inspect it.`}>
      <div className={`es-orb ${recovered ? "ok" : ""}`} ref={orbLabel}>
        <span>{recovered ? "Recovered" : "Withheld in error"}</span>
        <b className="num">{usd(totalCents)}</b>
      </div>
    </div>
  );
}
