import logging
from scrapy import FormRequest, Request
from scrapy.exceptions import CloseSpider
import os

ACCOUNTS = os.getenv('FB_ACCOUNTS')
LOGIN_URL = 'https://m.facebook.com/login.php'


def get_credentials(index=0):
    if not ACCOUNTS:
        raise Exception('No Facebook accounts found in FB_ACCOUNTS')
    user = ACCOUNTS.split(',')[index]
    un, password, *rest = user.split(';')
    logging.debug('Using credentials: {}:{}'.format(un, password))
    return un, password


def login(cookiejar, callback, credentials=get_credentials()):
    return Request(LOGIN_URL,
                   dont_filter=True,
                   callback=lambda res: login_using_response(res, credentials, cookiejar, callback))


def login_using_response(response, credentials, cookiejar, callback):
    email, password = get_credentials()

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
