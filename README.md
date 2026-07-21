# Flappy Bird (Python / Pygame)

A Flappy Bird clone built with Pygame, developed incrementally — this repo's
commit history is the build log.

## Run it

```
pip install pygame
python flappy_bird.py
```

Space or click to flap.

## Journey

### v1 — Basic playable prototype
Plain shapes only: a circle for the bird, rectangles for the pipes. Gravity,
flap, collision, scrolling pipes, score, restart. No images, no menu — just
proving the core loop works before touching any art.

### v2 — Real graphics, and fixing what broke
Swapped the shapes for actual images. First pass just force-resized whatever
PNG was dropped in, which caused two problems once real assets came in:

- The source PNGs had no real alpha channel — what looked like a transparent
  checkerboard was actually baked into the pixels, so it rendered as solid
  gray/white in-game instead of disappearing. Fixed by flood-filling from the
  image edges to strip the baked-in background, leaving inner details (like
  an eye) untouched.
- Square source images were being stretched into bird/pipe shapes, distorting
  them. Fixed by cropping to actual content bounds and scaling with aspect
  ratio preserved. The pipe went further: split into a cap + a tileable body
  strip so it can extend to any length without stretching.

### v3 — Menu, leaderboard, and real button art
Added a proper front end instead of dropping straight into gameplay:

- Game states: menu → playing → game over → leaderboard
- Start and Leaderboard buttons on the menu; Retry/Menu on the game-over
  screen; Back on the leaderboard screen
- Scores persist to `leaderboard.json` next to the script, capped at the
  top 5
- Swapped the plain rectangle buttons for real art: extracted the title
  logo and the two button graphics from reference images (the button
  source image had its background scene baked in opaque, so it needed
  the same flood-fill isolation trick as the bird/pipe fix in v2)

### v4 — Full asset pack: animation, sound, scrolling ground
Replaced the hand-extracted bird/pipe art with a proper open-source asset
pack ([samuelcust/flappy-bird-assets](https://github.com/samuelcust/flappy-bird-assets),
MIT licensed):

- Bird now animates through 3 flap frames instead of a static image
- Pipe uses the pack's real sprite (same cap + tileable body approach as v2,
  now on authentic art)
- Scrolling ground strip at the bottom — bird now dies on the ground, not
  the screen edge
- Sky background fills the screen
- Score renders with the pack's pixel-digit sprites instead of system font
- Sound effects: wing flap, point scored, hit, die, menu swoosh

Title and button art from v3 were kept as-is — only the gameplay assets
were replaced.

## Credits
Sprites and sounds in v4+: [samuelcust/flappy-bird-assets](https://github.com/samuelcust/flappy-bird-assets) (MIT).
