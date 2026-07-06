# Running the clipper on a Raspberry Pi

The Pi does one thing: replay a captured session against the for-U API every night. It never
opens a browser and never sees your password. The login happens on your Mac (see the main README);
the Pi just needs the resulting `session.json` and a filled-in `config.toml`.

## One-time setup

Clone the repo and install it into a virtualenv. The Pi only needs `requests`, so skip the
`[capture]` extra (that's Playwright, Mac-only).

```bash
git clone https://github.com/samgutentag/safewayClipper.git foru-clipper
cd foru-clipper
python3 -m venv .venv
.venv/bin/pip install .
```

Copy the example config and fill it in:

```bash
cp config.toml.example config.toml
```

You need three things in `config.toml`:

1. `banner` and `session_path` (leave `session_path = "session.json"`).
2. The `[api]` credentials. Grab `x-swy_api_key`, `x-ibm-client-id`, and `x-ibm-client-secret`
   from a logged-in vons.com request (DevTools > Network > any `offers/clip` POST > Copy as cURL).
   These are app-level constants, not your login, but they don't belong in a public repo, so
   they live here in the gitignored config.
3. Pushover `token` and `user` (or set `PUSHOVER_TOKEN` / `PUSHOVER_USER` as env vars instead).

The `session.json` itself arrives from your Mac. Running `clipper login` there captures the
session and rsyncs it to the Pi automatically, as long as you set `[pi] ssh_host` and
`session_path` in the Mac's config.

## The nightly job

`deploy/crontab.example` has the line. Install it with `crontab -e` and point the path at your
clone. It runs `clipper clip` at 2am, wrapped in `flock` so a slow run never stacks on top of the
next one, and appends output to `logs/cron.log`.

## When it stops working

Sessions don't last forever. When one expires, the next run sends a high-priority Pushover push
telling you to run `clipper login` on the Mac again. That's the whole maintenance loop. You can
also check `clipper status` on the Pi to see the session age and the last run result.
