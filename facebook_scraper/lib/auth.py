import logging
from scrapy import FormRequest, Request
from facebook_scraper.lib.sheets import get_facebook_credentials
import os

LOGIN_URL = 'https://m.facebook.com/login.php'


def get_credentials():
    if os.getenv('FB_ACCOUNT'):
        return tuple(os.getenv('FB_ACCOUNT').split(','))
    else:
        return get_facebook_credentials()


def login(callback, **kwargs):
    return Request(LOGIN_URL,
                   dont_filter=True,
                   callback=lambda res: login_using_response(res, callback, **kwargs),
                   **kwargs)


def login_using_response(response, callback, **kwargs):
    email, password = get_credentials()
    logging.debug('Using credentials: {}:{}'.format(email, password))

    return FormRequest.from_response(
        response,
        dont_filter=True,
        formxpath='//form[contains(@action, "login")]',
        formdata={'email': email, 'pass': password},
        callback=lambda res: _handle_device_check(res, callback, **kwargs),
        **kwargs
    )


def _handle_device_check(response, callback, **kwargs):
    # Handle 'save-device' redirection
    if response.xpath("//div/a[contains(@href,'save-device')]"):
        return FormRequest.from_response(
            response,
            formdata={'name_action_selected': 'dont_save'},
            callback=lambda res: callback(),
            **kwargs
        )
    # Handle 'GDPR' redirection
    if response.xpath("//div/a[contains(@href,'gdpr/consent')]"):
        url = response.xpath("//div/a[contains(@href,'gdpr/consent')]/@href").get()
        return Request(url, dont_filter=True, callback=lambda res: _handle_gdpr_consent_step(res, callback, **kwargs))
    else:
        return callback()


def _handle_gdpr_consent_step(response, callback, **kwargs):
    if response.xpath("//div/a[contains(@href,'consent_step')]"):
        url = response.xpath("//div/a[contains(@href,'conset_step')]/@href").get()
        return Request(url, dont_filter=True, callback=lambda res: _handle_gdpr_consent_step(res, callback, **kwargs))
    else:
        return callback()
