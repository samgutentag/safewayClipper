#!/usr/bin/env python3
"""A tool for clipping Safeway coupons."""

import os
import argparse
import time
from selenium import webdriver

__author__ = "Sam Gutentag"
__copyright__ = "Copyright 2018, Sam Gutentag"
__credits__ = ["Sam Gutentag"]
__license__ = "GPL"
__version__ = "0.6.1"
__maintainer__ = "Sam Gutentag"
__email__ = "developer@samgutentag.com"
__status__ = "Developement"
# "Production", "Developement", "Prototype"


def parse_arguments():
    """Parse arguments from command line."""
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
    return args


def get_webdriver(headless=False):
    """Initialize web driver.

    Parameters
    headless (bool): initialize webdriver in headless mode.

    """
    try:
        driver_path = os.path.dirname(os.path.realpath(__file__))
        chromedriver = f"{driver_path}/chromedriver"

        if headless:
            options = webdriver.ChromeOptions()
            options.add_argument("headless")

            driver = webdriver.Chrome(chromedriver, options=options)

            # specify webdriver window resolution, helps clicking
            driver.set_window_size(1440, 900)

        else:
            driver = webdriver.Chrome(chromedriver)

        return driver

    except Exception:
        return -1


def safeway_login(driver, username, password):
    """Log in to safeway site.

    Parameters
    driver (webdriver): selenium webdriver session
    username (string): username for login authentication
    password (string): password for login authentication

    """
    login_page = "https://www.safeway.com/account/sign-in.html"

    driver.get(login_page)
    time.sleep(3)

    # refresh the page, helps slow loading
    driver.refresh()
    time.sleep(3)

    # enter login credentials
    username_field = driver.find_element_by_id("label-email")
    username_field.send_keys(username)

    password_field = driver.find_element_by_id("label-password")
    password_field.send_keys(password)

    # attempt to login
    login_button = driver.find_element_by_id("btnSignIn")
    login_button.click()

    # verify login by checking text in "sign-in-profile-text" button
    time.sleep(10)
    login_button = driver.find_element_by_id("sign-in-profile-text")

    if login_button.text == "Sign In / Up":
        return -1
    else:
        return 0


def clip_coupons(driver):
    """Navigate to offer page and collect coupon offers.

    Parameters
    driver (webdriver): selenium webdriver session

    """
    offer_url = "https://www.safeway.com/justforu/coupons-deals.html"

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
    coupons = driver.find_elements_by_class_name("coupon-container")

    for coupon in coupons:

        # get add button
        add_button_class = "grid-coupon-btn"
        add_button = coupon.find_elements_by_class_name(add_button_class)[0]
        if add_button.text.lower() == "add":

            # get description
            description_class = "coupon-description-text-title-wrapper"
            description = coupon.find_elements_by_class_name(description_class)

            savings_class = "heading-offer-price"
            savings = coupon.find_elements_by_class_name(savings_class)

            print(f"{savings[0].text}\t{description[0].text}")

            # click add button
            try:
                driver.execute_script("arguments[0].click();", add_button)
            except Exception:
                return -1

    return 0


def clipper():
    """Primary function."""
    args = parse_arguments()

    driver = get_webdriver(headless=args["headless_mode"])
    if driver == -1:
        if not args["headless_mode"]:
            print("Something went wrong initializing webdriver... quitting.")
        driver.quit()
        return -1

    login = safeway_login(driver, username=args['username'],
                          password=args['password'])
    if login == -1:
        if not args["headless_mode"]:
            print("Something went wrong logging in... quitting.")
        driver.quit()
        return -1

    clip_status = clip_coupons(driver)
    if clip_status == -1:
        if not args["headless_mode"]:
            print("Something went wrong clipping coupons... quitting.")
        driver.quit()
        return -1

    driver.quit()


if __name__ == "__main__":
    clipper()
