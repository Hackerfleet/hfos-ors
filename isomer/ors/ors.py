#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# HFOS - Hackerfleet Operating System
# ===================================
# Copyright (C) 2011-2019 Heiko 'riot' Weinen <riot@c-base.org> and others.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Heiko 'riot' Weinen"
__license__ = "AGPLv3"

"""

Module: ORS
===========

API wrapper for OpenRouteService.

"""

import socket
import os

import json

import openrouteservice

from circuits import Worker, task, Event
from isomer.logger import debug, verbose

from isomer.component import ConfigurableController

from urllib.request import urlopen


def get_query(query):
    """
    Threadable function to retrieve ors data from the internet
    :param url: URL of tile to get
    """
    log = ""
    connection = None

    url = query

    try:
        connection = urlopen(url=url, timeout=2)  # NOQA
    except Exception as e:
        log += "ORST: ERROR ors api open error: %s " % str([type(e), e, url])

    content = ""

    # Read and return requested content
    if connection:
        try:
            content = connection.read()
        except (socket.timeout, socket.error) as e:
            log += "ORST: ERROR ors api error: %s " % str([type(e), e])

        connection.close()
    else:
        log += "ORST: ERROR Got no connection."

    return content, log


class UrlError(Exception):
    pass


class cli_test_ors(Event):
    """Test if the ors api loader works"""
    pass


class ORSService(ConfigurableController):
    """
    ORS API loader component
    """

    configprops = {}

    # channel = 'isomer-web'

    channel = '/ors'

    def __init__(self, *args):
        """

        :param kwargs:
        """
        super(ORSService, self).__init__('ORS', *args)

        # Insert your api key here, for now:
        self.key = ''

        self.target = (13.40955, 52.52079)

        # self.worker = Worker(process=False, workers=2,
        #                     channel="orsworkers").register(self)

        # self.fire(
        #    cli_register_event('test_orsloader', cli_test_ors), 'isomer-web')

    # @handler("cli_test_ors", channel='isomer-web')
    # def cli_test_ors(self, event, *args):
    #    self.log('Testing ORS API data loader..')

    def route(self, arg1, arg2):
        self.log('I got a query:', arg1, arg2, pretty=True, lvl=debug)

        profile = 'driving-car'
        instructions = False
        simplify = True

        coords = ((arg2, arg1), self.target)

        client = openrouteservice.Client(
            key=self.key)
        routes = openrouteservice.client.directions(
            client,
            coordinates=coords,
            profile=profile,
            format='geojson',
            instructions=instructions,
            geometry_simplify=simplify
        )

        return json.dumps(routes)

    def revgeocode(self, arg1, arg2):
        self.log('I got a rev query:', arg1, arg2, pretty=True, lvl=debug)

        coords = (arg2, arg1)

        client = openrouteservice.Client(
            key=self.key)
        address = openrouteservice.client.pelias_reverse(
            client,
            coords,
            size=1
        )

        self.log(self.request.headers, pretty=True, lvl=verbose)
        self.response.headers['Content-Type'] = 'application/json'
        # self.response.headers['X-Content-Type-Options'] = 'nosniff'
        self.response.headers['Access-Control-Allow-Headers'] = '*'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

        self.log(self.response, pretty=True, lvl=verbose)

        self.log(address, pretty=True, lvl=debug)

        return json.dumps(address)

    def geocode(self, place):
        self.log('I got a geocode query:', place, pretty=True, lvl=debug)

        client = openrouteservice.Client(
            key=self.key)
        address = openrouteservice.client.pelias_autocomplete(
            client,
            text=place
        )

        self.log(self.request.headers, pretty=True, lvl=verbose)
        self.response.headers['Content-Type'] = 'application/json'
        # self.response.headers['X-Content-Type-Options'] = 'nosniff'
        self.response.headers['Access-Control-Allow-Headers'] = '*'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

        self.log(self.response, pretty=True, lvl=verbose)

        self.log(address, pretty=True, lvl=debug)

        return json.dumps(address)
