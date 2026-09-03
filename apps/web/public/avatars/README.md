# Pre-rendered avatar clips

Drop SadTalker-generated talking-head clips here. **Until you do, nothing
breaks:** `PrerenderedAvatarProvider` throws for a missing file, the media
pipeline treats that as "no avatar configured", and the drawn teacher panel is
used exactly as it is today.

## Layout

```
apps/web/public/avatars/
├── english/
│   ├── intro.mp4
│   ├── idle.mp4
│   ├── correct.mp4
│   ├── repair_transition.mp4
│   └── complete.mp4
├── hindi/     (same five)
└── hinglish/  (same five)
```

Served at `/public/avatars/<language>/<role>.mp4`.

## What each clip is for

| Role | Played when |
| --- | --- |
| `intro` | First scene of a lesson |
| `idle` | Ordinary teaching scenes - the one to add first |
| `correct` | Just after a correct checkpoint answer |
| `repair_transition` | A misconception repair scene |
| `complete` | The final learning report |

Only `idle.mp4` is needed to see the feature working; the rest degrade to the
drawn panel individually, so a missing `complete.mp4` never affects `idle`.

## Making them

See `docs/TALKING_HEAD_SETUP.md`. In short: one still portrait, then SadTalker
at `--preprocess crop --size 256 --still` per clip. 10-20 seconds each is
plenty - they loop under longer scenes.

**Use a face you have the right to use:** a synthetic portrait, a licensed
stock portrait, or someone who has consented. Not a photograph of a real person
who has not agreed.

## After adding clips

Set `GURUFLOW_HIDE_BUILTIN_TEACHER=1` so the rendered lesson videos drop the
drawn cartoon teacher, instead of showing a second, competing teacher beside
your real one.

## Reverting

From the browser console: `mediaAdapter.useFallbackAvatar()`, or simply remove
the files.
