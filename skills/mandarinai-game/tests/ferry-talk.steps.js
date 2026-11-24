// play-check steps: stop on the ferry dialogue, the longest line box, so --device checks its layout.
G.start(); G.upd(5); G.advance(); G.upd(5);
G.teleport(3, 7.2); G.press('KeyE'); G.upd(2); G.step(1);
return { dialogue: G.state().dialogue };
