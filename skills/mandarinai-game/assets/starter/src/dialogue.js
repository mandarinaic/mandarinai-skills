// Dialogue box with per-hanzi pinyin ruby and a translation line.
// P toggles pinyin, T toggles translation; Space / Enter / click advances.
const HAN = /\p{Script=Han}/u;

// Returns HTML with one <ruby> per hanzi, punctuation outside the ruby.
// Throws when the syllable count does not match the hanzi count: a misaligned line
// teaches the wrong reading, so it must never ship silently.
export function rubyHTML(zh, py) {
  const syl = py.trim().split(/\s+/);
  const chars = [...zh]; const han = chars.filter((c) => HAN.test(c)).length;
  if (syl.length !== han) throw new Error(`pinyin mismatch: "${zh}" has ${han} hanzi but ${syl.length} syllables`);
  let i = 0;
  return chars.map((c) => (HAN.test(c) ? `<ruby>${c}<rt>${syl[i++]}</rt></ruby>` : `<span class="punct">${c}</span>`)).join('');
}

export function createDialogue({ el, names, errors, onSpeak }) {
  let queue = [], done = null, showPy = true, showEn = true;
  const nameEl = el.querySelector('.who'), zhEl = el.querySelector('.zh'), enEl = el.querySelector('.en');
  function render() {
    const line = queue[0]; if (!line) return;
    nameEl.textContent = names[line.who] || ''; nameEl.hidden = !nameEl.textContent;
    try { zhEl.innerHTML = rubyHTML(line.zh, line.py); }
    catch (e) { errors.push(e.message); console.error(e.message); zhEl.textContent = line.zh; }
    zhEl.classList.toggle('no-py', !showPy);
    enEl.textContent = line.en; enEl.hidden = !showEn;
    onSpeak?.(line);
  }
  function advance() {
    if (!queue.length) return;
    queue.shift();
    if (queue.length) render(); else { el.hidden = true; const d = done; done = null; d?.(); }   // synchronous on purpose: frame-stepped tests must see the result immediately
  }
  addEventListener('keydown', (e) => {
    if (el.hidden) return;
    if (e.code === 'KeyP') { showPy = !showPy; render(); }
    else if (e.code === 'KeyT') { showEn = !showEn; render(); }
    else if (e.code === 'Space' || e.code === 'Enter') { e.preventDefault(); if (!e.repeat) advance(); }
  });
  el.addEventListener('pointerdown', advance);
  return {
    get open() { return !el.hidden; },
    play(lines, onDone) { queue = [...lines]; done = onDone; el.hidden = false; render(); },
    advance,
  };
}
