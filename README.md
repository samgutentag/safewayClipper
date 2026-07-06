# Safeway / Vons Coupon Clipper

Clips your digital for-U coupons automatically, so you don't have to sit there tapping "Clip
Coupon" a hundred times before every grocery run.

Works with any Albertsons banner (Safeway, Vons, Albertsons) since they all run the same platform.
Which one you use is a single line of config.

## So Long, Selenium

The original version of this drove a real browser with Selenium: log in, scroll the coupons page,
click every button. It ran nightly for months until April 2023, when Safeway put a captcha on the
login page and the whole thing fell over. The last commit message was literally `captcha'd EOL`.

Since then login got harder, not easier. Vons now wants a password, sometimes a captcha, and an
emailed one-time code. Automating your way through all of that is a losing fight.

So this rebuild stops fighting it. Instead of automating login, it automates the boring part and
lets you do the login by hand, once.

## How It Works

Two pieces:

1. **Capture (on your Mac).** `clipper login` opens a real browser at the vons.com sign-in page.
   You log in yourself, solving whatever it throws at you (password, captcha, the emailed code).
   The tool grabs the resulting session and, if you've pointed it at a Pi, rsyncs it over.
2. **Clip (on a Raspberry Pi).** Every night a cron job runs `clipper clip`, which replays that
   session straight against the for-U JSON API with plain HTTP requests. No browser, no scrolling,
   no clicking. It clips every unclipped coupon and moves on.

The trick that makes a manual login worth it: the session tokens rotate as you use them, and every
nightly run saves the refreshed cookies back. That stretches a single login from days to weeks.
When it finally expires, you get a Pushover notification and run `clipper login` again.

## Setup

Install it (Playwright is only needed on the machine you log in from):

```bash
# On the Mac you'll log in from:
pip install '.[capture]'
python -m playwright install chromium

# On the Pi that does the nightly clipping:
pip install .
```

Copy `config.toml.example` to `config.toml` and fill in your banner, the for-U API credentials
(see the comments in that file for where to grab them), and your Pushover keys. Then:

```bash
clipper login    # on the Mac, logs in and pushes the session to the Pi
clipper clip     # clips everything unclipped (add --dry-run to see what it would do)
clipper status   # session age and last run result
```

Pi setup and the cron line are in [`deploy/README.md`](deploy/README.md).

## A Note on Credentials

The clip endpoint routes through Albertsons' API gateway and needs a couple of app-level
credentials (an API key and an IBM gateway client id/secret). These aren't your login, they're
constants baked into the vons.com web app, the same for every visitor. But since this repo is
public they live in `config.toml`, which is gitignored, rather than in the source. Grab them from
a logged-in request via DevTools once and you're set.

Nothing with your password or session tokens is ever committed.

## Design

The full design and the confirmed API contract are in
[`docs/superpowers/specs/`](docs/superpowers/specs/) and
[`docs/superpowers/plans/`](docs/superpowers/plans/) if you want to see how it fits together or
adapt it for your own banner.
