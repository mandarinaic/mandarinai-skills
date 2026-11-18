# Rigged characters and motion

For the unrigged MandarinAi cast, start with whole-body procedural motion (`cast-3d.md`).
This file is for characters that have a skeleton: generated heroes, enemies, bosses, or a
cast member rigged later.

## Bringing a rigged model in
- Load, return to the bind pose, measure the bounding box for scale, put the feet on the ground.
- Facing: take the world positions of the left and right thigh bones → "right" vector;
  cross with up → "forward"; that gives the yaw correction the model needs.
- Record bone names and the rest pose (world positions and rotations); all motion is built on it.
- Collision radius and hit ranges live in data, never derived from the mesh: swapping a
  model must not change how the game feels.

## Platform preset clips (walk, run, hit, fall)
- **Presets carry root motion.** Zeroing the root position track is not enough: the hip's
  parent is usually tilted. Transform to model space, pin the horizontal part to the rest
  value, keep the vertical bob, transform back. Symptom: "the character drifts a metre off its
  foot ring" or "always walks sideways a little".
- Each preset may face 90° off the bind pose: measure each on load, store the correction.
- Files used only for their clips can be stripped of meshes and textures at pack time
  (`packaging.md`). Drop `.scale` tracks when loading clips.

## Authored moves: never guess joint angles
Guessed Euler angles always twist the body. Instead:
- Write poses in **character space**: +Y up, +Z forward, metres, right hand at −X.
- Per key pose: hip offset, spine and head turn, **hand target position**, **weapon
  direction**, **foot placement**.
- Solve arms and legs with two-bone IK (with an elbow/knee hint), then rotate the wrist so the
  weapon points where asked.
- Bake key poses into clips so they crossfade like presets.
- Build a **numeric probe**: print each joint relative to the root at a frame and check with
  numbers ("hand in front of the shoulder", "foot on the ground"); add a close-up showcase
  page (`?show=char`) and screenshot it.

## Weight
A move needs at least five keys: wind-up → **coil hold** (a little deeper, ≈0.08 s) → fast
release (quartic ease-out) → **follow-through overshoot** → recover to the ready pose. Three
keys (wind-up, hit, return) always look stiff.
- Start and end every move on the combat-ready pose or combos will pop.
- Active (damage) frames align with the release beat; edit keys → edit the hit table.
- Big bodies standing up or falling: head leads, weight shifts onto a support, legs push,
  torso follows last. Never a 0.1 s crossfade between very different poses ("folding open").

## Idle and weapons
- Out of combat: relaxed stance, weapon on the back; draw before the first strike; sheathe a
  few seconds after combat. A character always holding a weapon "looks stiff".
- Weapon hangs from a node under the hand bone; a second node on the back; switch parents.
- Blocking: weapon diagonal and close to the body.

## Worth doing with time left
Wide sleeves, long hair, capes (every MandarinAi character has a blue cape or scarf) look
dead when rigidly skinned. Add spring bones if there is time.
