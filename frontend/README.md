# DISHAA frontend

A static landing page and chat bar. Plain HTML, CSS and JavaScript, no build step.

- `index.html`: the page. The airplane, loop and dotted trail are inline SVG animation (SMIL), so the design lives in the elements.
- `styles.css`: black and white only. Font stack is Satoshi, then DM Sans.
- `app.js`: warm-up call to `/health`, `POST /ask` (PRD FR-23), safe rendering (text only, citation links limited to http and https), reduced-motion support, browser speech input where supported.
- `config.js`: set `API_BASE` to the deployed API URL. Empty means "API not deployed yet".

Run locally: `python3 -m http.server 8080` inside this folder, then open http://localhost:8080.

Deploy: S3 bucket behind CloudFront (Terraform, not written yet). The CloudFront origin must allow the API origin in CORS.

Not in v0.1: file upload (the add-files button is disabled; see R19) and the voice button falls back to disabled when the browser has no speech recognition.
