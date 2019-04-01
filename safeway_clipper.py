#!/usr/bin/env python3

""" safewayClipper.py:  A Tool for Clipping Coupons on Safeway.com

    You will need to install ChromeDriver, download link here:
        https://sites.google.com/a/chromium.org/chromedriver/
    Current Version is 2.44

    Download Operating System Specific Version!

"""

import os
import time
from selenium import webdriver


__author__ = "Sam Gutentag"
__copyright__ = "Copyright 2018, Sam Gutentag"
__credits__ = ["Sam Gutentag"]
__license__ = "GPL"
__version__ = "0.5.0"
__maintainer__ = "Sam Gutentag"
__email__ = "developer@samgutentag.com"
__status__ = "Developement"
# "Production", "Developement", "Prototype"


def click_offers_on_page(driver=None, headless=False, page=None, button_title=None,
                         button_class=None, scroll_limit=100, scroll_min=30):

    """ Scrolling and clicking elements with specified class tags

    Keyword arguments:
        driver (webdriver)      --  the target Selenium web driver
        page (string)           --  the webpage URL to search for offers
        button_title (string)   --  the text label of the button to "click"
        button_class (string)   --  the css class of the button to "click"
        scroll_limit (int)      --  page scrolls <n> times to load content
                                    before looking for buttons to "click"
        scroll_min (int)        --  ensure at least this many scrolls
    """

    if not headless:
        print(f"Loading page: {page}")

    # load page url
    driver.get(page)

    time.sleep(3)

    if not headless:
        print(f"Scrolling...")
    found_button_count = 0
    previous_button_count = 0
    for i in range(0, scroll_limit + 1):
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        # get number of buttons, if does not increase after first 5 scrolls, stop scrolling
        found_button_count = len(
            driver.find_elements_by_xpath(f'//*[@title="{button_title}"]')
        )
        if i > scroll_min:
            if found_button_count != previous_button_count:
                previous_button_count = found_button_count
            else:
                break
        time.sleep(1)

    time.sleep(3)

    if not headless:
        print(f"Getting buttons...")
    add_buttons = driver.find_elements_by_xpath(
        f'//*[@title="{button_title}"]'
    )

    found_button_count = len(add_buttons)

    if not headless:
        print(f"Found {found_button_count} buttons by searching text...")

    if found_button_count < 1 and not button_class is None:
        add_buttons = driver.find_elements_by_class_name(button_class)

    if not headless:
        print(f"Found {len(add_buttons)} total buttons by searching css class...")

    valid_buttons = [x for x in add_buttons if x.text == "Add"]
    if not headless:
        print(f"Found {len(valid_buttons)} total buttons to click!")

    invalid_buttons = [x for x in add_buttons if x.text == "Added"]
    if not headless:
        print(f"Found {len(invalid_buttons)} total buttons to ignore!")

    for idx, button in enumerate(valid_buttons):
        if not headless:
            print(f"{idx+1} of {len(valid_buttons)}:\t{button}")
        try:
            button.click()
        except Exception as ex:
            if not headless:
                print(f"{ex}")

    return driver


def get_webdriver(headless=False):
    """ setup webdriver, else set to None
    """
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        chromedriver = f"{dir_path}/chromedriver"

        if headless:

            options = webdriver.ChromeOptions()
            options.add_argument("headless")

            driver = webdriver.Chrome(chromedriver, options=options)

            # specify webdriver window resolution
            driver.set_window_size(1440, 900)

        else:
            driver = webdriver.Chrome(chromedriver)

    except Exception as ex:
        if not headless:
            print(f"Error: {ex}")
        driver = None
    return driver


def login(driver=None, headless=False, login_username=None, login_password=None):

    """ Login to Safeway member portal, defaults to env variable credientials

    Keyword arguments:
        driver (webdriver)      --  the target Selenium web driver
        login_username (string) --  username for login, might be an email
        login_password (string) --  password for login
    """

    # login data
    if not login_username:
        login_username = os.environ.get("SAFEWAY_USERNAME")
    if len(login_username) == 0:
        if headless:
            return -1
        else:
            print("ERROR: 'login_username' was not passed or set in environment variables")
            return -1
    if not login_password:
        login_password = os.environ.get("SAFEWAY_PASSWORD")
    if len(login_password) == 0:
        if headless:
            return -1
        else:
            print("ERROR: 'login_password' was not passed or set in environment variables")
            return -1

    if not headless:
        print(f"Retrieved login credentials")

    # refresh page - Safeway"s login page doesnt load properly the first time
    if not headless:
        print("refreshing page...")
    driver.refresh()
    time.sleep(3)

    if not headless:
        print(f"attempting login...")
    try:
        username = driver.find_element_by_id("input-email")
        password = driver.find_element_by_id("password-password")
        username.send_keys(login_username)
        password.send_keys(login_password)
        # click sign in button
        login_attempt = driver.find_element_by_id("create-account-btn")
        login_attempt.click()
        if not headless:
            print(f"\tlogin success!")
        return 0

    except Exception as ex:
        if not headless:
            print(f"Whoops... Something went wrong trying to login.\n\t{ex}")
        return -1


def main():
    """
    main loop of the program
    """

    headless = True

    driver = get_webdriver(headless)
    if not driver:
        if not headless:
            print(f"ERROR: Could not assign Webdriver...")
        return -1

    driver.get("https://www.safeway.com/CMS/account/login/")

    time.sleep(3)

    """
    #===========================================================================
    #       Input Your Details Here!
    #===========================================================================
    """
    login(driver=driver, headless=headless)
    time.sleep(5)

    # Just For U
    just_for_u_offers = "https://www.safeway.com/ShopStores/Justforu-Coupons.page#/category/all"
    button_title = "Add"
    button_class = "lt-place-add-button"

    driver = click_offers_on_page(
        driver=driver,
        headless=headless,
        page=just_for_u_offers,
        button_title=button_title,
        button_class=button_class,
    )

    driver.quit()
    if not headless:
        if not headless:
            print("All Done! Happy Shopping!")
    return 0


if __name__ == "__main__":
    main()


# EOF
