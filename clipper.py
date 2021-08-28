#! /usr/bin/env python3

"""Safeway Coupon Clipper using Selenium

Uses a Selenium web driver Firefox Gecko or Chrome browser to clip Safeway
coupons. Relies on passed username and password else defualt sto environment
variables. Offers page is dynamically loaded, so this script keeps track of
new found coupons after each scroll and can be limited.  default behavior is
to scroll until no more un-clipped coupons are found.

This script is dumb, and relies on the the css Class of coupons and their
buttons to identify click targets.  As the css changes, this script will need
to be updated.

Writes data log of the run datetime, number of coupons clipped, and the number
of coupons found.  Keep in mind that this number of coupons found may be
truncated from the total number of available coupons by the scroll limit.

Use CalVer versioning from here https://calver.org/

"""

__authors__ = ["Sam Gutentag"]
__email__ = "developer@samgutentag.com"
__maintainer__ = "Sam Gutentag"
__version__ = "2021.08.27dev"
# "dev", "alpha", "beta", "rc1"


import argparse
import logging
import os
import time
from datetime import datetime

from selenium import webdriver

MIN_CHROME_DRIVER_VERSION = 79
MIN_GECKO_DRIVER_VERSION = 29


def setup_logging():
    """Set up  logging filename and ensure logging directory exists."""
    # name of this file
    this_file = os.path.splitext(os.path.basename(__file__))[0]

    log_datetag = datetime.today().strftime("%Y%m%d")

    # construct name of log file
    log_file = f"{this_file}_logfile_{log_datetag}.txt"

    # ensure logging directory exists
    this_dir = os.path.dirname(os.path.realpath(__file__))
    log_dir = os.path.join(this_dir, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # logging settings
    logging.basicConfig(filename=os.path.join(log_dir, log_file),
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    # logging.disable(logging.CRITICAL)
    logging.info("\n\n\n\n")
    logging.info("-" * 80)


def safe_print(msg="", headless=True):
    """Print to console if in headless mode."""
    if headless:
        return
    else:
        print(msg)


def parse_arguments():
    """Parse arguments from command line.

    Returns:
        args (dict): dictionary of input command line arguments

    """

    logging.info("parsing command line arguements")
    parser = argparse.ArgumentParser(description=("Clipping coupons from "
                                                  "Safeway.com Just4U page."))

    parser.add_argument("-headless", "--headless_mode", action="store_true",
                        required=False, default=False,
                        help="run in headless browser mode.")

    parser.add_argument("-driver", "--which_driver", dest="which_driver",
                        required=False, default="gecko",
                        help="Use gecko or chrome driver, gecko default.")

    parser.add_argument("-u", "--username", dest="username",
                        required=False,
                        default=os.environ.get("SAFEWAY_USERNAME"),
                        help=("user login, defaults to env variable "
                              "'SAFEWAY_USERNAME'."))

    parser.add_argument("-p", "--password", dest="password",
                        required=False,
                        default=os.environ.get("SAFEWAY_PASSWORD"),
                        help=("user password, defaults to env variable "
                              "'SAFEWAY_PASSWORD'."))

    args = vars(parser.parse_args())
    logging.info(f"arguments: {args}")

    return args


def get_webdriver(which_driver="gecko", headless=False):
    """Initialize web driver.

    Will use the Gecko web driver unless an "chrome" is passed to
    the "which_driver" argument.

    Args:
        which_driver (string): use either gecko or chrome webdriver.
        headless (bool): initialize webdriver in headless mode.

    Returns:
        driver (web driver object): -1 on failure

    Raises:
        Exception: something wrong with web driver

    """
    driver_path = os.path.dirname(os.path.realpath(__file__))

    # Gecko Driver Usage
    if which_driver == "gecko":
        geckodriver = os.path.join(driver_path,
                                   "webdrivers",
                                   f"geckodriver-{MIN_GECKO_DRIVER_VERSION}")
        logging.info(f"using webdriver version {MIN_GECKO_DRIVER_VERSION}")
        logging.info(f"webdriver located at: {geckodriver}")

        try:

            if headless:
                logging.info("running headless")

                options = webdriver.FirefoxOptions()
                options.add_argument("-headless")

                logging.info("initializing headless Gecko webdriver")
                driver = webdriver.Firefox(executable_path=geckodriver,
                                           firefox_options=options,
                                           service_log_path="/dev/null")

                # specify webdriver window resolution, helps clicking
                driver.set_window_size(1440, 900)

            else:

                logging.info("initializing Gecko webdriver")
                driver = webdriver.Firefox(executable_path=geckodriver,
                                           service_log_path="/dev/null")

        except Exception as err:
            logging.debug(err)
            return -1
        logging.info("geckodriver ready.")
        return driver

    # ChromeDriver Usage
    else:
        chromedriver = os.path.join(driver_path,
                                    "webdrivers",
                                    f"chromedriver_{MIN_CHROME_DRIVER_VERSION}")

        logging.info(f"using webdriver version {MIN_CHROME_DRIVER_VERSION}")
        logging.info(f"webdriver located at: {chromedriver}")

        try:

            if headless:
                logging.info("running headless")
                options = webdriver.ChromeOptions()
                options.add_argument("headless")
                logging.info("initializing headless Chrome webdriver")
                driver = webdriver.Chrome(chromedriver, options=options,
                                          service_log_path="/dev/null")

                # specify webdriver window resolution, helps clicking
                driver.set_window_size(1440, 900)

            else:

                logging.info("initializing Chrome webdriver")
                driver = webdriver.Chrome(chromedriver,
                                          service_log_path="/dev/null")

        except Exception as err:
            logging.debug(err)
            return -1

        logging.info("chromedriver ready.")
        return driver


def safeway_login(driver, username, password):
    """Log in to safeway site.

    Verifies login success by searching for a "Sign In/Up" button. If
    this button is not found, assumes login was successful.

    Args:
        driver (webdriver): selenium webdriver session
        username (string): username for login authentication
        password (string): password for login authentication

    Returns:
        result (int): 0 on success, -1 on failure

    """
    logging.info("navigating to login page...")
    login_page = "https://www.safeway.com/account/sign-in.html"

    driver.get(login_page)
    time.sleep(3)

    # refresh the page, helps slow loading
    logging.info("refresh page to ensure all elements have loaded")
    driver.refresh()
    time.sleep(3)

    # enter login credentials
    logging.info("filling in username field")
    username_field = driver.find_element_by_id("label-email")
    username_field.send_keys(username)

    logging.info("filling in password field")
    password_field = driver.find_element_by_id("label-password")
    password_field.send_keys(password)

    # attempt to login
    logging.info("attempting to log in")
    login_button = driver.find_element_by_id("btnSignIn")
    login_button.click()

    # verify login by checking text in "sign-in-profile-text" button
    time.sleep(10)
    logging.info("verifying login status...")
    login_button = driver.find_element_by_class_name("menu-nav__profile-button-sign-in-up")

    if login_button.text == "Sign In / Up":
        logging.critical("ERROR: Not logged in correctly")
        return -1
    else:
        logging.info("success!")
        return 0


def clip_coupons(driver, headless_mode=False):
    """Navigate to offer page and collect coupon offers.

    First scrolls page to load more offers, will scroll 10 times or until no
    new clip buttons are exposed, whichever is later. Once done scrolling will
    start clipping found coupons with a 0.5 second pause between clicks to not
    present as a bot.

    Args:
        driver (webdriver): selenium webdriver session

    Returns:
        clip_count (int): number of coupons clipped, -1 if none found

    """
    logging.info("starting coupon clipping")
    safe_print(msg="starting coupon clipping", headless=headless_mode)
    offer_url = "https://www.safeway.com/justforu/coupons-deals.html"

    logging.info(f"navigating to offers url: {offer_url}")
    safe_print(msg=f"navigating to offers url: {offer_url}",
               headless=headless_mode)
    driver.get(offer_url)

    time.sleep(10)

    # scroll page
    scroll_count = 10
    for i in range(scroll_count):
        load_more_btn = driver.find_element_by_xpath('//button[text()="Load more"]')
        load_more_btn.click()
        time.sleep(2)

    # get "Clip Coupon" buttons
    try:
        add_buttons = driver.find_elements_by_xpath('//button[text()="Clip Coupon"]')
        logging.info(f"found {len(add_buttons)} coupons.")
        safe_print(msg=f"found {len(add_buttons)} coupons.",
                   headless=headless_mode)
    except Exception:
        logging.info("no coupons found.")
        safe_print(msg="no coupons found.", headless=headless_mode)
        return 1

    coupons_clipped = 0
    for btn in add_buttons:
        if btn.text.lower() == "clip coupon":

            driver.execute_script("arguments[0].click();", btn)

            coupons_clipped += 1
            time.sleep(0.5)

    logging.info(f"clipped {coupons_clipped} coupons.")
    safe_print(msg=f"clipped {coupons_clipped} coupons.",
               headless=headless_mode)
    return coupons_clipped


def clipper():
    """Primary function to clip coupons."""
    args = parse_arguments()

    logging.info("getting web driver")
    driver = get_webdriver(which_driver=args["which_driver"],
                           headless=args["headless_mode"])

    if driver == -1:
        logging.critical(f"Something went wrong initializing {args['which_driver']} webdriver... quitting.")
        return -1

    login = safeway_login(driver,
                          username=args["username"],
                          password=args["password"])
    if login == -1:
        logging.critical("Something went wrong logging in... quitting.")
        driver.quit()
        return -1

    clip_coupons(driver, headless_mode=args["headless_mode"])

    driver.quit()
    logging.info("complete")
    safe_print(msg="complete", headless=args["headless_mode"])


if __name__ == "__main__":
    setup_logging()
    clipper()
