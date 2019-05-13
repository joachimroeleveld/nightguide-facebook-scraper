#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scrapy import signals
from scrapy.exceptions import NotConfigured

import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

class StackDriverLogger(object):
    """Add the Google Stackdriver logging extensions to a Scrapy spider.
    When this extension is enabled, the spider.logger.<log type> functions
    will send their messages to your Google project's Stackdriver logs.
    """

    def __init__(self, project=None):

        """Create the extension object.
        Positional arguments:
        project -- Required string. Name the Google Cloud Platform project
                   that the logs belong to.
        """

        if project is None:
            raise ValueError("Missing Google project name")

        self.project = project

    @classmethod
    def from_crawler(cls, crawler):
        """Prepare the crawler to attach the log when the spider is opened."""

        if not crawler.settings.getbool("STACKDRIVER_ENABLED"):
            raise NotConfigured("Stackdriver not enabled")

        project = crawler.settings.get("STACKDRIVER_PROJECT_ID")

        if project is None:
            raise ValueError("STACKDRIVER_PROJECT_ID must be set")

        ext = cls(project)

        crawler.signals.connect(ext.attach_log, signal=signals.spider_opened)

        return ext

    def attach_log(self, spider):
        """Attach the StackDriver handler to the spider's logger."""

        client = google.cloud.logging.Client(project=self.project)
        handler = CloudLoggingHandler(client, name="scraper." + spider.name)

        spider.logger.logger.addHandler(handler)
        spider.logger.debug("StackDriver logging enabled.")