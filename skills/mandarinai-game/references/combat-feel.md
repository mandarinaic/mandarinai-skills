# Combat: hit feel, interaction, camera

For action-form games (`story-adaptation.md`). Goal: a fight with back-and-forth, not
mowing grass. Every item makes player and enemy actions affect each other.

## Make attacks land
- **Aim assist**: on attack, pick the nearest enemy near the aim line (distance + angle
  weighted), turn to it, slide to "just in reach". Each frame, slide by the smaller of the
  remaining slide and (distance − reach) so it never overshoots. Top-down 3D distance is hard
  to judge; without assist, swings keep brushing past.
- **Bodies have volume**: player and enemies push each other apart (except while dodging or
  airborne). The starter's ferry push-apart is the pattern.

## Hit feedback
- **Hitstop per actor, never global**: attacker and target each freeze a few frames (light
  ≈0.06–0.09 s, heavy ≈0.10–0.13 s), the target shakes (`hitstop()` in motion.js), other
  enemies keep moving. Global slow-mo makes the whole scene sticky.
- Buffer input during hitstop (next attack, dodge, counter) or presses feel eaten.
- **Tiered knockback and stagger**: light hits nudge, heavy hits shove; tough enemies only
  flinch to light hits and stagger every few.
- Sparks at the contact point, flying along the swing, not bursting from the enemy's centre.
- For learners' games keep it bloodless: ink splashes, light, paper-cut fragments.

## Block, parry, counter
- Hold to block: frontal only, drains stamina by damage, guard breaks at zero. Area attacks
  (slams, lightning, ground eruptions) cannot be blocked — they force a dodge.
- Parry: catch within ≈0.24 s of raising the guard; no stamina cost, long stagger on the
  attacker, fills a boss's break gauge.
- **After a successful block open a counter window** (≈0.85 s, longer after a parry): ring at
  the feet, key prompt, attack triggers a finisher (step in, brief slow-mo, big damage, a
  sword wave). This is the most satisfying beat of the back-and-forth.
- Interrupt: hitting an enemy in the second half of its wind-up breaks the move.
- Dodge through an attack that would have hit: brief slow-mo, restores a resource.

## Dodge has top priority
Dodge cancels attacks (any frame), casting, blocking, potions, and hitstop. Only hit-stun and
the ultimate cannot be dodged out of.

## Enemies
- **Few and sturdy**: three or four per wave, each takes four or five hits.
- **Only one melee attacker at a time**; the rest circle outside.
- Give each enemy type one behaviour that *answers* the player: a double strike, a parry of
  light attacks followed by a counter, a ranged cast with a ground telegraph.
- Always one ranged enemy, and its projectiles can be cut down.
- Telegraphs give enough reaction time and are effects themselves (`vfx-ui-audio.md`).

## Difficulty
Tune until your own scripted test that only mashes attack survives a while. Version one is
almost always too hard: lower enemy damage, raise player health and post-hit invulnerability
before weakening enemy behaviour.

## Camera
- Narrow zoom range (e.g. 0.95–1.3×); no big push-ins with distance.
- **Leash the focus**: at most 3–4 m from the hero. In a boss fight bias the focus toward the
  boss a little, but the hero stays near the middle of the frame.
- One smoothing stage only (smoothed focus, camera rigidly offset from it). A second lerp on
  the camera position drags the hero off-centre.
- Mouse pull on the camera: very small.
- Cutscene → gameplay: set the cutscene's end pose to the gameplay camera pose, hand control
  back when nearly there, then ramp follow speed from slow to normal. Otherwise it jumps.
- Clamp camera height above terrain each frame.
- Tall things between camera and hero (gates, trees, pillars, pavilions) fade: horizontal
  distance from the object to the camera–hero segment under its radius → fade out.

## Arena
- Shape the play area as a smooth union of circles with a noisy edge, never a perfect circle.
  Place colliding rocks, broken pillars, trees to break it up.
- Neighbouring circle colliders form concave pockets that snag; a row of obstacles gets one
  capsule collider.
- **Before closing off a walkable area** (a boss intro sealing the way back), move the hero
  to a known-safe spot first, or they can be left on an island.
- Run a whole-map sweep test: grid points, push in eight directions for dozens of logic
  frames (`G.upd`), then check the hero can leave from where they stopped.
