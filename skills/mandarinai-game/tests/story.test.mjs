// Unit checks for the learning layer: every starter line must annotate cleanly.
import test from 'node:test';
import assert from 'node:assert/strict';
import { rubyHTML } from '../assets/starter/src/dialogue.js';
import { story } from '../assets/starter/src/story.js';

const lines = Object.values(story.lines).flat();
const TONED = /^[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+$/;

test('rubyHTML puts one syllable over each hanzi and leaves punctuation outside', () => {
  assert.equal(rubyHTML('你好！', 'nǐ hǎo'), '<ruby>你<rt>nǐ</rt></ruby><ruby>好<rt>hǎo</rt></ruby><span class="punct">！</span>');
});

test('rubyHTML rejects a syllable count that does not match the hanzi count', () => {
  assert.throws(() => rubyHTML('你好', 'nǐ'), /pinyin mismatch/);
});

test('every starter line aligns pinyin to hanzi', () => {
  for (const l of lines) assert.doesNotThrow(() => rubyHTML(l.zh, l.py), l.zh);
});

test('starter pinyin is lowercase with tone marks, no digits, no v', () => {
  for (const l of [...lines, ...story.words]) for (const syl of l.py.split(/\s+/)) assert.match(syl, TONED, `${l.zh}: "${syl}"`);
});

test('every speaker has a display name and every line a translation', () => {
  for (const l of lines) { assert.ok(l.who in story.names, l.zh); assert.ok(l.en.trim(), l.zh); }
});
