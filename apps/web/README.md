# GuruFlow web client (apps/web)

The learner-facing classroom: onboarding, source analysis, timed lesson plan,
teaching scenes with visuals and captions, the checkpoint, the misconception
repair flow, and the final report.

## Running it

The client is served by the teacher brain, so there is nothing to build:

```bash
py -3.12 -m uvicorn apps.api.main:app --port 8077
```

Then open <http://127.0.0.1:8077/>.

## Why there is no build step

**Node.js is not required, and was not available on the machine this was built
on.** Rather than ship an unverifiable Next.js scaffold, the client is written
as ES modules the browser loads directly:

* no npm install, no bundler, no CDN, no webfonts
* the demo renders identically with the network switched off
* it imports Person 3's real modules from `services/visuals` and
  `services/media` instead of reimplementing them

The trade-off is explicit: no TypeScript type checking and no component test
framework. See "Porting to Next.js" below.

## Files

| File | Responsibility |
| --- | --- |
| `index.html` | Screen structure for all four screens plus the evidence drawer |
| `src/app.js` | Controller: scene flow, checkpoint, repair splicing, report |
| `src/api.js` | API client with a fixture-backed fallback |
| `src/visuals.js` | Renderers for every `Scene.visual.type` |
| `src/media-adapter.js` | Browser TTS/avatar providers for `services/media` |
| `src/styles.css` | Complete stylesheet, no framework |

## Integration with services/media

`services/media` ships mock providers that import Node's `crypto`, so they
cannot run in a browser. That is precisely the case the provider-neutral
interface exists for: `src/media-adapter.js` implements `TTSProvider` and
`AvatarProvider` for the browser and hands them to Person 3's
`DefaultSceneRenderer`. Scene rendering logic stays owned by `services/media`;
only the providers differ per environment.

`FallbackAvatarProvider` throws by design when no avatar vendor is configured,
which exercises the renderer's documented fallback path: the CSS teacher panel
plus captions. A provider failure degrades the lesson, it never stops it.

Voice is optional and off by default. Turning it on uses the browser's built-in
speech synthesis - no key, no network call.

## Fixture mode

If `/health` is unreachable the client switches to `demo-fixtures/` and the
full wrong-answer -> repair -> retry -> report loop still completes. The badge
in the header says which source is live, so the mode is never hidden.

Note the honest limit: because the backend also serves this page, fixture mode
covers a *broken API*, not a *stopped process*. Host `apps/web` on any static
server to get the fully backend-free demo.

## Porting to Next.js

The team plan specifies Next.js + TypeScript + Tailwind. The seams are already
in the right places:

1. `src/visuals.js` renderers become React components (one per visual type).
2. `src/api.js` becomes a typed client; generate types from
   `packages/contracts/lesson-contract.schema.json`.
3. `src/app.js` state becomes a reducer; the screen sections become routes.
4. `src/media-adapter.js` moves unchanged - it depends only on the contract.
