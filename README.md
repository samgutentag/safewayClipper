# Safeway Coupon Clipper

A simple tool to clip Safeway grocery coupons!

---

## Switch to the Firfox Gecko Driver

Originally this project used the Chrome Webdriver for Selenium instances. Given chromes updates, and
fighting toggling auto update off constantly, I have migrated to using the Gecko Driver with
Firefox. The minimum verion of Gecko Driver is 26.

That said, using the `-driver chrome` argument will use the Chrome webdriver. This was lasted tested
using Chrome Driver version 101.

- The latest Chrome Driver can be downloaded from [Chromium](https://chromedriver.chromium.org)
- The latest Gecko Driver can be downloaded from the
  [Mozilla GitHub](https://github.com/mozilla/geckodriver/releases)

Once downloaded, place the Gecko Driver or Chrome Driver in the `./webdrivers/` directory. Format
the name as `geckodriver-##`

Alternatively you can modify the `get_webdriver()` function in `clipper.py` to point to the location
you have chosen.

---

## "Automation" with Cron Jobs

To help not spam the Safeway website with my login and coupon checks, I allow a cron to run the
`clipper.py` script at 2am every day to complete the "automation" portion of the script.

---

## Requirements

Running `clipper.py` will require a web driver (see above), and I reccomend using the
`python -m pip install -r requirements.txt` command to install the other needed packages.

## Tips and Tricks

- Make sure the Chrome Driver suffix matches the `MIN_CHROME_DRIVER_VERSION` variable
- on M1 Macs, control click the webdriver to authenticate and work around Apple Security Issues
  - More information here:
    [Apple can’t check app for malicious software](https://support.apple.com/guide/mac-help/apple-cant-check-app-for-malicious-software-mchleab3a043/mac)
