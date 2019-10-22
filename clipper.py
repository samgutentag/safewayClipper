#! /usr/bin/env python3

"""Safeway Coupon Clipper using Selenium

Uses a selenium driver Chrome browser to clip Safeway coupons. Relies on passed
username and password else defualt sto environment variables. Offers page is
dynamically loaded, so this script keeps track of new found coupons after each
scroll and can be limited.  default behavior is to scroll until no more
un-clipped coupons are found.

This script is dumb, and relies on the the css Class of coupons and their
buttons to identify click targets.  As the css changes, this script will need
to be updated.

Writes data log of the run datetime, number of coupons clipped, and the number
of coupons found.  Keep in mind that this number of coupons found may be
truncated from the total number of available coupons by the scroll limit.


This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

"""


__authors__ = ["Sam Gutentag"]
__email__ = "developer@samgutentag.com"
__date__ = "2019/10/22"
__deprecated__ = False
__license__ = "GPLv3"
__maintainer__ = "Sam Gutentag"
__status__ = "Developement"
__version__ = "0.7.0"
# "Prototype", "Development", "Production", or "Legacy"


import argparse
import logging
import os
import time
from datetime import datetime

from selenium import webdriver

MIN_CHROME_DRIVER_VERSION = 77


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


def parse_arguments():
    """Parse arguments from command line."""
    logging.info("parsing command line arguements")
    parser = argparse.ArgumentParser(description=("Clipping coupons from "
                                                  "Safeway.com Just4U page."))

    parser.add_argument("-headless", "--headless_mode", action="store_true",
                        required=False, default=False,
                        help="run in headless browser mode.")

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


def get_webdriver(headless=False):
    """Initialize web driver.

    Parameters
    headless (bool): initialize webdriver in headless mode.

    """
    DRIVER_VERSION = MIN_CHROME_DRIVER_VERSION

    driver_path = os.path.dirname(os.path.realpath(__file__))
    chromedriver = os.path.join(driver_path,
                                "webdrivers",
                                f"chromedriver_{DRIVER_VERSION}")

    while not os.path.exists(chromedriver):
        DRIVER_VERSION += 1

        chromedriver = os.path.join(driver_path,
                                    "webdrivers",
                                    f"chromedriver_{DRIVER_VERSION}")

    logging.info(f"using webdriver version {DRIVER_VERSION}")
    logging.info(f"webdriver lcoated at: {chromedriver}")

    if headless:
        logging.info("running headless")
        options = webdriver.ChromeOptions()
        options.add_argument("headless")

        logging.info("initializing headless Chrome webdriver")
        driver = webdriver.Chrome(chromedriver, options=options, service_log_path='/dev/null')

        # specify webdriver window resolution, helps clicking
        driver.set_window_size(1440, 900)

    else:
        logging.info("initializing Chrome webdriver")
        driver = webdriver.Chrome(chromedriver, service_log_path='/dev/null')

    logging.info("chromedriver ready.")
    return driver


def safeway_login(driver, username, password):
    """Log in to safeway site.

    Parameters
    driver (webdriver): selenium webdriver session
    username (string): username for login authentication
    password (string): password for login authentication

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
    login_button = driver.find_element_by_id("sign-in-profile-text")

    if login_button.text == "Sign In / Up":
        logging.critical("ERROR: Not logged in correctly")
        return -1
    else:
        logging.info("success!")
        return 0


def clip_coupons(driver, headless_mode=False):
    """Navigate to offer page and collect coupon offers.

    Parameters
    driver (webdriver): selenium webdriver session

    """
    logging.info("starting coupon clipping")
    offer_url = "https://www.safeway.com/justforu/coupons-deals.html"

    logging.info(f"navigating to offers url: {offer_url}")
    driver.get(offer_url)

    time.sleep(3)

    # scroll page to load all offers
    keep_scrolling = True
    add_buttons_found = 0

    while keep_scrolling:

        # # uncomment this if requiring a literal scroll
        # driver.execute_script(
        #     "window.scrollTo(0, document.body.scrollHeight);"
        # )

        # scroll until the load more button goe away
        try:
            load_more_btn = driver.find_elements_by_class_name("load-more")[0]
            load_more_btn.click()
            time.sleep(5)

            # get add button count
            btn_class = "coupon-clip-button"
            add_buttons = driver.find_elements_by_class_name(btn_class)
            add_buttons = [b for b in add_buttons if b.text.lower() == "add"]
            add_button_count = len(add_buttons)

            if add_button_count > add_buttons_found:
                add_buttons_found = add_button_count
            else:
                keep_scrolling = False

        except Exception:
            keep_scrolling = False

    # collect coupons
    coupons_found = driver.find_elements_by_class_name("grid-coupon-container")
    logging.info(f"found {len(coupons_found)} coupons.")

    coupons_clipped = 0

    for idx, coupon in enumerate(coupons_found):

        # get add button
        add_button_class = "grid-coupon-btn"
        add_button = coupon.find_elements_by_class_name(add_button_class)[0]
        if add_button.text.lower() == "add":

            # get description
            description_class = "grid-coupon-description-text-title"
            description = coupon.find_elements_by_class_name(description_class)

            savings_class = "grid-coupon-heading-offer-price"
            savings = coupon.find_elements_by_class_name(savings_class)

            try:
                savings_text = savings[0].text
                description_text = description[0].text
                logging.info(f"\t[{idx+1:3} of {len(coupons_found):3}]\t{savings_text:20}\t{description_text}")
            except Exception:
                pass

            # click add button
            try:
                driver.execute_script("arguments[0].click();", add_button)
                coupons_clipped += 1
            except Exception:
                pass

    return (coupons_clipped, len(coupons_found))


def clip_counter(coupons_clipped, coupons_found):
    """Record to file the number of coupons clipped.

    Parameters:
    coupons_clipped (int): number of coupons clipped
    coupons_found (int): total number of coupons found
    """

    # name of this file
    this_file = os.path.splitext(os.path.basename(__file__))[0]
    log_datetag = datetime.today().strftime("%Y%m")

    # construct name of log file
    data_file = f"{this_file}_datafile_{log_datetag}.csv"

    # ensure logging directory exists
    logging.info("ensuring data directory exists")
    this_dir = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(this_dir, "data")
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    data_filepath = os.path.join(data_dir, data_file)

    # append to datafile
    logging.info(f"appending data record to datefile {data_filepath}")

    log_datetime = datetime.today().strftime("%Y-%m-%d %H:%m:%S")
    data_line = f"{log_datetime},{coupons_clipped},{coupons_found}\n"

    new_file = not os.path.exists(data_filepath)

    with open(data_filepath, "a") as f:
        if new_file:
            f.write("datetime,coupons_clipped,coupons_found\n")
        f.write(data_line)


def clipper():
    """Primary function. This should all be a class."""
    args = parse_arguments()

    logging.info("getting web driver")
    driver = get_webdriver(headless=args["headless_mode"])

    if driver == -1:
        logging.critical("Something went wrong initializing webdriver... quitting.")
        driver.quit()
        return -1

    login = safeway_login(driver,
                          username=args['username'],
                          password=args['password'])
    if login == -1:
        logging.critical("Something went wrong logging in... quitting.")
        driver.quit()
        return -1

    coupons_clipped, coupons_found = clip_coupons(driver, headless_mode=args["headless_mode"])
    if coupons_clipped == -1:
        logging.critical("Something went wrong clipping coupons... quitting.")
        driver.quit()
        return -1

    # record clip counter
    clip_counter(coupons_clipped, coupons_found)

    driver.quit()
    logging.info("complete")


if __name__ == "__main__":
    setup_logging()
    clipper()
