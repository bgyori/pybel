# -*- coding: utf-8 -*-

import logging
import time

import requests
from requests.compat import urlparse
from requests_file import FileAdapter

log = logging.getLogger(__name__)


def get_iso_8601_date():
    """Gets the current ISO 8601 date as a string

    :rtype: str
    """
    return time.strftime('%Y%m%d')


def is_url(s):
    """Checks if a string is a valid URL

    :param str s: An input string
    :return: Is the string a valid URL?
    :rtype: bool
    """
    return urlparse(s).scheme != ""


def download(url):
    """Uses requests to download an URL, maybe from a file"""
    session = requests.Session()
    session.mount('file://', FileAdapter())

    try:
        res = session.get(url)
    except requests.exceptions.ConnectionError as e:
        raise e

    res.raise_for_status()
    return res
