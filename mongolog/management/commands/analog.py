# -*- coding: utf-8 -*-
#!/usr/bin/env python
from __future__ import print_function
import logging
import logging.config
import django
import json
import sys

import pymongo
pymongo_version = int(pymongo.version.split(".")[0])
if pymongo_version >= 3:
    from pymongo.collection import ReturnDocument


from mongolog.handlers import get_mongolog_handler

from django.core.management.base import BaseCommand

#logger = logging.getLogger(__name__)
logger = logging.getLogger('mongolog')


class Command(BaseCommand):
    if django.VERSION[1] <= 7:
        from optparse import make_option
        option_list = BaseCommand.option_list + (
            make_option(
                '-l', '--limit', default=10, type=int, action='store', dest='limit',
                help='Delete poll instead of closing it'),
            make_option(
                '-t', '--tail', default=False, action='store_true', dest='tail',
                help='Tail the log file.  By default it will limit to 10 results.  Use --limit to change'),
            make_option(
                '-q', '--query', default=None, action='store', dest='query',
                help='Pass in a search query to mongo.'),
       )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.prev_object_id = None


    def add_arguments(self, parser):
        if django.VERSION[1] >= 7:
            parser.add_argument(
                '-l', '--limit', default=10, type=int, action='store', dest='limit',
                help='Limit Results',
            )
            parser.add_argument(
                '-t', '--tail', default=False, action='store_true', dest='tail',
                help='Tail the log file.  By default it will limit to 10 results.  Use --limit to change',
            )
            parser.add_argument(
                '-q', '--query', default=None, type=str, action='store', dest='query',
                help='Pass in a search query to mongo.',
            )

    def print_results(self, results):
        try:
            results = list(results['result'])
        except TypeError as e:
            if "'CommandCursor' object has no attribute '__getitem__'" in str(e):
                print("FAIL: result(%s)" % results)
                print("result.__dict__: ", results.__dict__)
            else:
                raise

        results.reverse()
        for r in results:
            level = r.get('level', None)
            if level == 'INFO':
                logger.info(r)
            elif level == 'WARNING':
                logger.warn(r)
            elif level == 'ERROR':
                logger.error(r)
            elif level == 'DEBUG':
                logger.debug(r)
            elif level == 'CRITICAL':
                logger.critical(r)
            elif level == 'MONGOLOG-INTERNAL' or level == None:
                # Print nothing if it's a mongolog internal log
                pass
            else:
                raise Exception("level(%s) not found" % level)

    def fetch_results(self, options):
        query = options['query'] if options['query'] else {}
        proj = {'_id': 1, 'level': 1, 'msg': 1,}
        limit = options['limit']
        return self.collection.aggregate([
            {"$match": query},
            {"$project": proj},
            {"$sort": {'created': pymongo.DESCENDING}},
            {"$limit": limit},
        ])

    def tail(self, options):
        initial = self.fetch_results(options)
        self.print_results(initial)
        raise NotImplementedError("--tail flag not implemented yet")

    def handle(self, *args, **options):
        if options['query']:
            options['query'] = json.loads(options['query'])

        handler = get_mongolog_handler()
        print("handler: ", handler)
        self.collection = handler.get_collection()

        if options['tail']:
            self.tail(options)
        else:
            results = self.fetch_results(options)
            self.print_results(results)
