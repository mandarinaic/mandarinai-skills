# MandarinAi Character Universe

The MandarinAi brand has a full cast of 19 designed characters: **12 Chinese-zodiac learning companions** and **7 human learners/mentors**. Every character has a complete model sheet in `assets/characters/<name>.jpg` — turnaround (front / 3-4 / side / back), 8-expression system, 5 micro-expressions, head structure, pose variations (relaxed / tense / confident), hand actions, costume details, silhouette, and the character's own color system.

Use these characters whenever MandarinAi content needs a mascot, narrator, explainer figure, emotional beat, or recurring IP presence — WeChat article 配图, social cards, PPT section mascots, course visuals.

## Shared visual DNA

- **Palette**: every character is anchored in the MandarinAi brand blue family (deep royal `#1b46a2` / navy) + warm gold/tan accents, on ivory/off-white backgrounds. The rooster adds red; each sheet carries its exact color chips — sample from the sheet, don't invent.
- **Style**: polished 3D-rendered mascot look (Pixar-adjacent) for the zodiac animals; stylized realistic 3D for the humans. Blue costume element on every character (cape, scarf, robe, jacket, or qipao), often with gold cloud/wave embroidery and a Chinese-character medallion (学 / 忠 / 悟…).
- **Tone**: warm, encouraging, learning-positive. No snark, no menace.

## Zodiac companions (12)

| File | Name | Role | Age | Personality | Core theme |
|------|------|------|-----|-------------|------------|
| `rat.jpg` | **Rui** | Zodiac Rat · Clever Strategist | 18 | Clever, Resourceful, Agile, Observant, Loyal | Discovers smarter ways to learn, connect, and grow |
| `ox.jpg` | **Bo** | Zodiac Ox · Steady Scholar | 19 | Steady, Disciplined, Reliable, Patient, Thoughtful | Turns daily effort into lasting growth |
| `tiger.jpg` | **Kai** | Zodiac Tiger · Confident Voice | 18 | Bold, Energetic, Fearless, Expressive, Encouraging | Speak Mandarin with confidence and momentum |
| `rabbit.jpg` | **Lina** | Zodiac Rabbit · Gentle Starter | 18 | Gentle, Supportive, Patient, Encouraging, Calm | Gentle first steps into the world of Mandarin |
| `dragon.jpg` | **Wei** | Zodiac Dragon · Mastery Guide | 20 | Ambitious, Insightful, Graceful, Wise, Encouraging | Pursue mastery with patience, vision, and growth |
| `snake.jpg` | **Yu** | Zodiac Snake · Precise Architect | 19 | Precise, Analytical, Calm, Observant, Reliable | Structure, clarity, and confidence in sentence building |
| `horse.jpg` | **MaXue** | Zodiac Horse · Momentum Guide | young | Energetic, Optimistic, Driven, Curious | Keep moving, build streaks, small meaningful progress |
| `goat.jpg` | **Mei Si 美思** | Zodiac Goat · Creativity & Learning Companion | timeless | Calm, Creative, Empathetic, Imaginative, Gentle | Inspiring creativity with calm focus, growth through art |
| `monkey.jpg` | **Xiang** | Zodiac Monkey · Interaction & Curiosity Companion | young | Curious, Playful, Brave, Clever, Friendly | Curiosity, courage, and joyful discovery |
| `rooster.jpg` | **Ming** | Zodiac Rooster · Pronunciation & Tone Coach | 19 | Clear, Confident, Expressive, Precise, Encouraging | Master pronunciation, tones, and spoken Mandarin |
| `dog.jpg` | **Bao** | Zodiac Dog · Loyal Guardian | 19 | Loyal, Supportive, Dependable, Encouraging, Patient | Protects learning streaks with warmth and confidence |
| `pig.jpg` | **Xin** | Zodiac Pig · Heart Rewarder | 18 | Warm, Compassionate, Joyful, Supportive, Encouraging | Celebrates progress, turns every small win into motivation |

## Human cast (7)

| File | Name | Role | Age | Personality | Core theme |
|------|------|------|-----|-------------|------------|
| `maya.jpg` | **Maya** | Beginner Mandarin Learner | 16 | Curious, Expressive, Energetic, Friendly, Brave | Learning Mandarin feels exciting, personal, full of possibility |
| `bai.jpg` | **Bai 白** | AI Mandarin Learning Genius | 18 | Smart, Quick, Playful, AI-Native, Expressive | Fast-thinking digital-native guide; learning feels intelligent, fun, effortless |
| `yue.jpg` | **Yue** | Mandarin Learning Guide | 22 | Warm, Encouraging, Curious, Intelligent, Expressive | Makes learning Mandarin approachable and joyful |
| `amir.jpg` | **Amir** | Young Professional Mandarin Learner | 24 | Ambitious, Calm, Friendly, Global, Professional | Uses Mandarin for opportunity, connection, career growth |
| `lian.jpg` | **Lian** | Foodie & Culture Guide | 26 | Sophisticated, Witty, Elegant, Observant, Warm | Turns food, culture, conversation into memorable learning moments |
| `jin.jpg` | **Jin 金** | Grammar & Culture Mentor | 58 | Wise, Patient, Insightful, Calm, Reassuring | Makes language and culture feel deep, calm, approachable |
| `grace.jpg` | **Grace** | Lifelong Mandarin Learner | 63 | Elegant, Witty, Patient, Curious, Warm | Language study can be joyful, cultured, and enduring |

## Casting guide (which character for which content)

- Beginner content / HSK 1-2 → **Lina** (gentle start) or **Maya** (learner POV)
- Pronunciation / tones / speaking → **Ming** (coach) or **Kai** (confidence)
- Grammar / sentence structure → **Yu** (precision) or **Jin** (mentor)
- Streaks / habit / daily practice → **MaXue**, **Bao** (guardian), **Bo** (discipline)
- Rewards / milestones / celebration → **Xin**
- Culture / food / travel → **Lian**, with **Jin** for depth
- Study methods / tips / hacks → **Rui**; interactive games → **Xiang**
- Advanced / mastery / long-term vision → **Wei**, **Grace**, **Amir**
- Creative / arts / calligraphy angles → **Mei Si**
- AI features / product-led content → **Bai**
- Zodiac-year seasonal content → the matching zodiac animal, obviously

One scene = one primary character. Pair at most two (e.g. mentor + learner) and keep the learner as the emotional anchor.

## Generating on-model character images

The sheets are **reference inputs, not final art** — never crop a model sheet into content directly.

With `scripts/generate-image.mjs` (needs `OPENAI_API_KEY` or `GEMINI_API_KEY`), pass the character's sheet via `--ref`:

```bash
node scripts/generate-image.mjs \
  --ref assets/characters/dog.jpg \
  --prompt "Bao, the MandarinAi zodiac-dog companion from the reference sheet (golden puppy, blue embroidered cape, streak-flame calendar tag), sitting at a desk proudly guarding a glowing 30-day streak calendar, warm ivory background, soft studio light, 3D mascot render matching the reference style exactly. Keep the character on-model: same face, proportions, costume, and colors as the reference." \
  --ratio 3:4 --out <task-folder> --name bao-streak
```

Prompt rules for on-model results:

1. Name the character and describe it briefly (species, costume, key prop) **and** state "match the reference sheet exactly — same face, proportions, costume, colors".
2. Pick the emotion from the sheet's 8-expression vocabulary (calm / curious / nervous / surprised / afraid / sad / determined / relaxed) and the pose register (relaxed / tense / confident).
3. Keep backgrounds in the house style (`references/visual-style.md`): ivory/off-white, soft light, brand blue + gold accents.
4. Inspect output against the sheet; regenerate if the face, costume, or palette drifts off-model.

No API key → deliver the prompt plan (`PROMPTS.md`) with the `--ref` path noted, per the standard no-key fallback in SKILL.md.

## Source assets

- In-repo sheets (`assets/characters/*.jpg`) are compressed working copies (1600px JPEG). Originals: `~/Downloads/character graph/` (full-res PNG).
- **3D models**: every character also exists as a rigged 3D `.glb` in `~/Downloads/3D/final/` (same file names) — usable for video, AR, or web-3D contexts. Not vendored into this repo for size reasons.
