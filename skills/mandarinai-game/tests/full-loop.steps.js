// play-check steps for the starter story: title -> intro -> river wall -> ferry -> words -> gate -> end.
// Logic-only frames (G.upd) keep it fast; one rendered frame at the end for the screenshot.
// Also a worked example of driving a game through the G hooks.
const st = () => G.state();
const keysOff = () => ['KeyA', 'KeyD', 'KeyW', 'KeyS'].forEach((k) => G.hold(k, false));
const walkTo = (x, z, max = 600) => {
  for (let i = 0; i < max; i++) {
    const [px, pz] = st().pos; const dx = x - px, dz = z - pz; keysOff();
    if (Math.hypot(dx, dz) < 0.3 || st().mode !== 'play') break;
    if (dx < -0.2) G.hold('KeyA'); if (dx > 0.2) G.hold('KeyD'); if (dz < -0.2) G.hold('KeyW'); if (dz > 0.2) G.hold('KeyS');
    G.upd(1);
  }
  keysOff(); G.upd(10);
};
const out = {};
G.upd(5); G.start(); G.upd(5); out.intro = st().mode;
G.advance(); G.upd(5); out.afterIntro = st().mode;
walkTo(0, -5, 200); out.riverWallZ = st().pos[1];
walkTo(3, 7.2); G.press('KeyE'); G.upd(2); out.ferryTalk = st().dialogue;
for (let i = 0; i < 3; i++) { G.advance(); G.upd(2); }
out.cut = st().mode; for (let i = 0; i < 900 && st().mode === 'cut'; i++) G.upd(1); out.crossed = st().crossed;
walkTo(-4, -6); walkTo(4, -9); walkTo(0, -12.5); out.words = st().words.join('');
walkTo(0, -15.5); G.upd(5); G.advance(); G.upd(5); out.end = st().mode;
G.step(1);
return out;
