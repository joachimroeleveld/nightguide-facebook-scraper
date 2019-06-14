import logging
from scrapy import FormRequest, Request
from scrapy.exceptions import CloseSpider
from facebook_scraper.lib.sheets import get_facebook_credentials
import os

LOGIN_URL = 'https://m.facebook.com/login.php'


def get_credentials():
    if os.getenv('FB_ACCOUNT'):
        return tuple(os.getenv('FB_ACCOUNT').split(','))
    else:
        return get_facebook_credentials()


def login(cookiejar, callback):
    return Request(LOGIN_URL,
                   dont_filter=True,
                   callback=lambda res: login_using_response(res, cookiejar, callback))


def login_using_response(response, cookiejar, callback):
    email, password = get_credentials()
    logging.debug('Using credentials: {}:{}'.format(email, password))

    return FormRequest.from_response(
        response,
        dont_filter=True,
        formxpath='//form[contains(@action, "login")]',
        formdata={'email': email, 'pass': password},
        meta={'cookiejar': cookiejar},
        callback=lambda res: _check_logged_in(res, cookiejar, callback)
    )


def _check_logged_in(response, cookiejar, callback):
    # Check for captcha
    if 'checkpoint' in response.url:
        raise CloseSpider('blocked_by_robot_check')
    # Handle 'save-device' redirection
    if response.xpath("//div/a[contains(@href,'save-device')]"):
        return FormRequest.from_response(
            response,
            meta={'cookiejar': cookiejar},
            formdata={'name_action_selected': 'dont_save'},
            callback=callback
        )
    else:
        return callback()
