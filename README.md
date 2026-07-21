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
