# Front-end assets

Heddle serves no executable code from a CDN. The checked-in HTMX 1.9.12 file
comes from the `htmx.org@1.9.12` npm package and its SHA-256 is recorded in
`.static-assets.sha256`.

Tailwind CSS is compiled from `static/src/input.css` and the checked-in
`tailwind.config.js` using CLI version 3.4.17:

```bash
npx --yes tailwindcss@3.4.17 -c tailwind.config.js \
  -i static/src/input.css -o static/css/app.css --minify
sha256sum -c .static-assets.sha256
```

When templates or dependencies change, regenerate the asset, review the diff,
update the expected hash intentionally, and exercise the UI under the Content
Security Policy before merging.
