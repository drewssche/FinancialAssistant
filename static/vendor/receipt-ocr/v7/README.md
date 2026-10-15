# Self-hosted receipt OCR assets

Unmodified distribution files, loaded only when the user requests scanning.
No CDN or photo-upload endpoint is used at runtime. `manifest.json` pins package
versions and SHA-256 hashes. All six core builds are retained for device capability
selection; only the selected build is downloaded by a client.

Sources:
- `tesseract.js@7.0.0`: `dist/tesseract.min.js`, `dist/worker.min.js`, their bundled
  license notices, and `LICENSE.md`. https://github.com/naptha/tesseract.js
- `tesseract.js-core@7.0.0`: all `*.wasm.js` (embedded WASM) and `LICENSE`.
  https://github.com/naptha/tesseract.js-core
- `@tesseract.js-data/rus@1.0.0`, `@tesseract.js-data/eng@1.0.0`:
  `4.0.0_best_int/*.traineddata.gz`. Data upstream:
  https://github.com/naptha/tessdata (Apache-2.0 license included).
  The npm package metadata labels its packaging MIT; only the trained data is copied.

To reproduce, install these exact packages into a temporary directory using
`npm install --ignore-scripts --no-audit --no-fund`, copy the listed files without
modification, and compare SHA-256 against the manifest. Review any mismatch rather
than updating hashes automatically. A version update must use a new versioned
asset directory to avoid mixing cached engines and models.

OCR runs in an isolated same-origin document with a dedicated worker, disposed
on completion, failure, cancellation or timeout. Images and recognized text are
not stored in browser persistence. Tesseract may cache public language models in
IndexedDB. Selected row text excerpts become receipt notes only after the user
transfers the draft and subsequently saves the normal operation.
