#!/usr/bin/env python3

''' safewayClipper.py:  A Tool for Clipping Coupons on Safeway.com

    You will need to install ChromeDriver, download link here:
        https://sites.google.com/a/chromium.org/chromedriver/
    Current Version is 2.44

    Download Operating System Specific Version!

'''

import os
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


__author__ = "Sam Gutentag"
__copyright__ = "Copyright 2018, Sam Gutentag"
__credits__ = ["Sam Gutentag"]
__license__ = "GPL"
__version__ = "0.4.1"
__maintainer__ = "Sam Gutentag"
__email__ = "developer@samgutentag.com"
__status__ = 'Developement'
    # 'Production', 'Developement', 'Prototype'

def click_offers_on_page(driver=None, page=None, button_title=None,
                                        button_class=None, scroll_limit=30):

    ''' Scrolling and clicking elements with specified class tags

    Keyword arguments:
        driver (webdriver)      --  the target Selenium web driver
        page (string)           --  the webpage URL to search for offers
        button_title (string)   --  the text label of the button to 'click'
        button_class (string)   --  the css class of the button to 'click'
        scroll_limit (int)      --  page scrolls <n> times to load content
                                    before looking for buttons to 'click'
    '''

    print(f'Loading page: {page}')

    # load page url
    driver.get(page)

    time.sleep(5)

    print(f'Scrolling...')
    for i in range(0, scroll_limit+1):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    time.sleep(5)

    print(f'Getting buttons...')
    add_buttons = driver.find_elements_by_xpath(f'//*[@title="{button_title}"]')

    print(f'Found {len(add_buttons)} buttons by searching text...')

    if len(add_buttons) < 1 and not button_class is None:
        add_buttons = driver.find_elements_by_class_name(button_class)

    print(f'Found {len(add_buttons)} total buttons by searching css class...')

    valid_buttons = [x for x in add_buttons if x.text == 'Add']
    print(f'Found {len(valid_buttons)} total buttons to click!')

    invalid_buttons = [x for x in add_buttons if x.text == 'Added']
    print(f'Found {len(invalid_buttons)} total buttons to ignore!')

    for idx, button in enumerate(valid_buttons):
        # print('%d of %d:\t%s' % (idx, len(valid_buttons), button))
        print(f'{idx+1} of {len(valid_buttons)}:\t{button}')
        try:
            button.click()
        except:
            pass

    return driver

def get_webdriver():
    ''' setup webdriver, else set to None
    '''
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        chromedriver = f'{dir_path}/chromedriver'

        # options = webdriver.ChromeOptions()
        # options.add_argument('headless')
        #
        # driver = webdriver.Chrome(chromedriver, chrome_options=options)
        driver = webdriver.Chrome(chromedriver)
    except:
        print(f'Could not find chromedriver')
        driver = None
    return driver

def login(driver = None, login_username = None, login_password = None):

    ''' Login to Safeway member portal, defaults to env variable credientials

    Keyword arguments:
        driver (webdriver)      --  the target Selenium web driver
        login_username (string) --  username for login, might be an email
        login_password (string) --  password for login
    '''

    # login data
    if not login_username:
        login_username = os.environ.get('SAFEWAY_USERNAME')
    if not login_password:
        login_password = os.environ.get('SAFEWAY_PASSWORD')

    print(f'Retrieved login credentials')

    # refresh page - Safeway's login page doesnt load properly the first time
    print('refreshing page...')
    driver.refresh()
    time.sleep(5)


    print(f'attempting login...')
    try:
        username = driver.find_element_by_id("input-email")
        password = driver.find_element_by_id("password-password")
        username.send_keys(login_username)
        password.send_keys(login_password)
        # click sign in button
        login_attempt = driver.find_element_by_id("create-account-btn")
        login_attempt.click()
        print(f'\tlogin success!')
        return 0

    except Exception as e:
        print(f'Whoops... Something went wrong trying to login.\n\t{e}')
        return -1

def main():

    driver = get_webdriver()
    if not driver:
        print(f'ERROR: Could not assign Webdriver...')
        return -1

    driver.get("https://www.safeway.com/CMS/account/login/")

    time.sleep(5)

    '''
    #===========================================================================
    #       Input Your Details Here!
    #===========================================================================
    '''
    login(driver=driver)
    time.sleep(10)

    # Just For U
    just_for_U_offers = 'https://www.safeway.com/ShopStores/Justforu-Coupons.page#/category/all'
    button_title = 'Add'
    button_class = 'lt-place-add-button'

    driver = click_offers_on_page(driver=driver, page=just_for_U_offers,
                            button_title=button_title, button_class=button_class)

    driver.quit()
    print('All Done! Happy Shopping!')

if __name__ == '__main__':
    main()


# EOF
