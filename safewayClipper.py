#!/usr/bin/env python3
''' A Tool for Clipping Coupons on Safeway.com!

    You will need to install ChromeDriver, download link here:
        https://sites.google.com/a/chromium.org/chromedriver/
    Current Version is 2.43

    Download Operating System SPecific Version!

'''

import os
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


__author__ = "Sam Gutentag"
__copyright__ = "Copyright 2018, Sam Gutentag"
__credits__ = ["Sam Gutentag"]
__license__ = "GPL"
__version__ = "0.1.1"
__maintainer__ = "Sam Gutentag"
__email__ = "developer@samgutentag.com"
__status__ = 'Production'


def click_offers_on_page(driver=None, page=None, button_class=None, scroll_limit=5):

    '''
        Scrolling and clicking elements with specified class tags
    '''

    print('Loading page: %s' % page)

    # load page url
    driver.get(page)

    time.sleep(10)

    # scroll to bottom of page
    scroll_count = 0
    while scroll_count < scroll_limit:
        print('%d of %d: Scrolling...' % (scroll_count+1, scroll_limit))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        scroll_count += 1

    time.sleep(15)

    print('Getting buttons...')
    add_buttons = driver.find_elements_by_class_name(button_class)

    for idx, button in enumerate(add_buttons):
        print('%d of %d:\t%s' % (idx, len(add_buttons), button))
        try:
            button.click()
        except:
            pass
        time.sleep(1)


def main():

    chromedriver = './chromedriver'
    driver = webdriver.Chrome(chromedriver)
    driver.get("https://www.safeway.com/CMS/account/login/")

    time.sleep(15)

    '''
    #===========================================================================
    #       Input Your Details Here!
    #===========================================================================
    '''
    login_username = None
    login_password = None

    # login data
    if not login_username:
        login_username = os.environ.get(f'SAFEWAY_USERNAME')
    if not login_password:
        login_password = os.environ.get(f'SAFEWAY_PASSWORD')

    print('Retrieved login credentials')

    # refresh page - Safeway's login page doesnt load properly the first time
    print('refreshing page...')
    driver.refresh()
    time.sleep(5)


    print('attempting login...')
    try:
        username = driver.find_element_by_id("input-email")
        password = driver.find_element_by_id("password-password")
        username.send_keys(login_username)
        password.send_keys(login_password)
        # click sign in button
        login_attempt = driver.find_element_by_id("create-account-btn")
        login_attempt.click()
        print('login success!')
    except Exception as e:
        print('Whoops... Something went wrong.\n\t%s' % e)
        return -1

    time.sleep(15)

    # Just For U
    just_for_U_offers = 'https://www.safeway.com/ShopStores/Justforu-Coupons.page#/category/all'
    add_button_class = 'lt-place-add-button'
    click_offers_on_page(driver=driver, page=just_for_U_offers, button_class=add_button_class, scroll_limit=50)

    time.sleep(15)

    # Club Specials
    club_special_offers = 'https://www.safeway.com/ShopStores/Justforu-YourClubSpecials.page?reloaded=true'
    add_button_class = 'lt-add-offer'
    click_offers_on_page(driver=driver, page=club_special_offers, button_class=add_button_class, scroll_limit=10)

    driver.quit()
    print('All Done! Happy Shopping!')


if __name__ == '__main__':
    main()



# EOF
