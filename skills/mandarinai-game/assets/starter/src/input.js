// Ported from guizang-game-skill (AGPL-3.0); arrow keys added.
// Keyboard and mouse state that survives lost key-up events, plus an F3 panel for reporting input problems.
// Usage: import { keys, pressed, mouse, endFrame, debugPanel } from './input.js';  call endFrame() once per frame.
export const keys = new Set(), pressed = new Set(), mouse = { x: 0, y: 0 };
const OPP = { KeyW: 'KeyS', KeyS: 'KeyW', KeyA: 'KeyD', KeyD: 'KeyA', ArrowUp: 'ArrowDown', ArrowDown: 'ArrowUp', ArrowLeft: 'ArrowRight', ArrowRight: 'ArrowLeft' }; let log = [];
const note = (s) => { log.push(s); log = log.slice(-8); };
addEventListener('keydown', (e) => {
  if (e.isComposing || e.keyCode === 229) return;                                   // input method is composing: not ours
  if (/^(Meta|Alt|Control)/.test(e.code)) { keys.clear(); return; }                 // shortcuts swallow key-ups: start clean
  if (e.metaKey || e.altKey || e.ctrlKey) return;
  if (!e.repeat) { note('↓' + e.code); if (OPP[e.code]) keys.delete(OPP[e.code]); } // pressing a direction drops a phantom opposite
  if (!keys.has(e.code)) pressed.add(e.code); keys.add(e.code);
  if (e.code === 'Space' || e.code === 'Tab' || e.code.startsWith('Arrow')) e.preventDefault();
});
addEventListener('keyup', (e) => { note('↑' + e.code); keys.delete(e.code); if (/^(Meta|Alt|Control)/.test(e.code)) keys.clear(); });
for (const ev of ['blur', 'focus', 'pagehide']) addEventListener(ev, () => { note('[' + ev + ']'); keys.clear(); });
document.addEventListener('visibilitychange', () => keys.clear());
addEventListener('mousemove', (e) => { if (!(e.buttons & 2)) keys.delete('RMB'); mouse.x = e.clientX / innerWidth * 2 - 1; mouse.y = -(e.clientY / innerHeight) * 2 + 1; });
addEventListener('mousedown', (e) => { if (e.button === 0) pressed.add('LMB'); if (e.button === 2) { pressed.add('RMB'); keys.add('RMB'); } });
addEventListener('mouseup', (e) => { if (e.button === 2) keys.delete('RMB'); });
addEventListener('contextmenu', (e) => e.preventDefault());
export function endFrame() { pressed.clear(); }
// Shift is deliberately not in the modifier list: games use it as a sprint key, and clearing on it would kill movement.
// Do NOT infer releases from missing auto-repeat events (the OS repeats only the most recently pressed key),
// and do not poll document.hasFocus() to clear keys (unreliable inside embedded browsers).

// F3 toggles a small panel; pass a function returning extra lines (state, speed, distance to the boundary...).
export function debugPanel(extra = () => '') {
  const d = document.createElement('div'); d.style.cssText = 'position:fixed;left:8px;top:60px;z-index:99;font:11px ui-monospace,Menlo,monospace;color:#9fe0c0;background:rgba(0,0,0,.55);padding:6px 8px;white-space:pre;display:none;pointer-events:none'; document.body.appendChild(d);
  addEventListener('keydown', (e) => { if (e.code === 'F3') { e.preventDefault(); d.style.display = d.style.display === 'none' ? 'block' : 'none'; } }, true);
  return () => { if (d.style.display !== 'none') d.textContent = `held: ${[...keys].join(' ') || '-'}\nfocus: ${document.hasFocus()}\n${extra()}\nrecent: ${log.join(' ')}`; };
}
