#!/usr/bin/env python3
''' A Tool for Clipping Coupons on Safeway.com!

    You will need to install ChromeDriver, download link here:
        https://sites.google.com/a/chromium.org/chromedriver/
    Current Version is 2.43

    Download Operating System SPecific Version!


'''


from selenium import webdriver
import os


__author__ = "Sam Gutentag"
__copyright__ = "Copyright 2018, Sam Gutentag"
__credits__ = ["Sam Gutentag"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Sam Gutentag"
__email__ = "developer@samgutentag.com"
__status__ = "Prototype"



def main():


    # open a browser window with default/Firefox
    # driver = webdriver.Firefox()
    # driver.get("www.samgutentag.com")

    chromedriver = './chromedriver'
    driver = webdriver.Chrome(chromedriver)
    driver.get("http://www.safeway.com")

    # login data
    login_username = os.environ.get(f'SAFEWAY_USERNAME')
    print(login_username)
    login_password = os.environ.get(f'SAFEWAY_PASSWORD')
    print(login_password)





if __name__ == '__main__':
    main()
