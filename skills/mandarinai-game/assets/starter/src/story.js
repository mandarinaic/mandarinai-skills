// Everything story-specific lives here: cast, lines, words, objectives.
// The sample adapts 十二生肖 (the Zodiac Race, a public-domain folk tale) with the
// MandarinAi zodiac cast. Replace it with the adapted story; keep the shape.
//
// Line format: { who, zh, py, en }. `py` has exactly one syllable per hanzi in `zh`,
// lowercase, tone marks, 一/不 written as pronounced (see references/learning-layer.md).
// dialogue.js refuses to annotate a line whose counts disagree and records it in G.errors.

export const story = {
  id: 'zodiac-race',
  title: { zh: '生肖赛跑', en: 'The Zodiac Race' },
  source: '十二生肖的传说 (folk tale, public domain)',
  gateText: '天门',   // the plaque on the finish gate
  // Role -> MandarinAi character id (assets/cast/<id>.glb). Set to null to use a stand-in.
  cast: { player: 'rat', ferry: 'ox' },
  names: { rat: 'Rui · 小老鼠', ox: 'Bo · 老牛', narrator: '' },
  scale: { ferry: 1.4 },   // the ox carries the rat, so it must read bigger; models all ship at ~1.1 m

  lines: {
    intro: [
      { who: 'narrator', zh: '玉帝说：谁先到，谁就排第一。', py: 'yù dì shuō shéi xiān dào shéi jiù pái dì yī', en: 'The Jade Emperor said: whoever arrives first will be ranked first.' },
    ],
    ferry: [
      { who: 'ox', zh: '小老鼠，你要过河吗？', py: 'xiǎo lǎo shǔ nǐ yào guò hé ma', en: 'Little rat, do you want to cross the river?' },
      { who: 'rat', zh: '要！可是我不会游泳。', py: 'yào kě shì wǒ bú huì yóu yǒng', en: "Yes! But I can't swim." },
      { who: 'ox', zh: '上来吧，我带你过河。', py: 'shàng lái ba wǒ dài nǐ guò hé', en: "Climb on. I'll carry you across." },
    ],
    gateLocked: [
      { who: 'rat', zh: '我还要找三个字。', py: 'wǒ hái yào zhǎo sān gè zì', en: 'I still need to find three characters.' },
    ],
    finish: [
      { who: 'rat', zh: '我到了！我是第一名！', py: 'wǒ dào le wǒ shì dì yī míng', en: "I made it! I'm number one!" },
    ],
  },

  // Collectible words: the learning layer. Keep them in the story's own vocabulary.
  words: [
    { zh: '河', py: 'hé', en: 'river', at: [-4, -6] },
    { zh: '快', py: 'kuài', en: 'fast', at: [4, -9] },
    { zh: '到', py: 'dào', en: 'to arrive', at: [0, -12.5] },
  ],

  // World layout in meters. +Z points toward the camera; the gate is far up-screen.
  world: { start: [0, 13], ferry: [3, 5.5], river: [-2.2, 2.2], farBank: [0, -4], gate: [0, -17], halfWidth: 12, near: 18, far: -21 },
};
