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
import json
import openrouteservice
import click

from urllib.request import urlopen
from urllib.request import unquote
from circuits import Worker, task, Event


from isomer.logger import debug, verbose, critical, isolog as log, set_verbosity, set_logfile
from isomer.component import ConfigurableController


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

    def __init__(self, *args, **kwargs):
        """

        :param kwargs:
        """
        super(ORSService, self).__init__('ORS', *args, **kwargs)

        self.key = kwargs.get('api_key', None)

        if self.key is None:
            self.log('No api key defined!', lvl=critical)

        self.target = (12.74137258529663, 53.309627534617626)

        # self.worker = Worker(process=False, workers=2,
        #                     channel="orsworkers").register(self)

        # self.fire(
        #    cli_register_event('test_orsloader', cli_test_ors), 'isomer-web')

    # @handler("cli_test_ors", channel='isomer-web')
    # def cli_test_ors(self, event, *args):
    #    self.log('Testing ORS API data loader..')

    def route(self, arg1):
        self.log('I got a query:', arg1, pretty=True, lvl=debug)

        profile = 'driving-car'
        instructions = False
        simplify = True

        query = json.loads(unquote(arg1))

        self.log(query, pretty=True)

        coords = query

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

        self.response.headers['Content-Type'] = 'application/json'
        # self.response.headers['X-Content-Type-Options'] = 'nosniff'
        self.response.headers['Access-Control-Allow-Headers'] = '*'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

        self.log(self.response.headers, pretty=True, lvl=critical)
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
        place = unquote(place)
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


@click.command()
@click.argument('api-key', envvar='ORS_API_KEY')
@click.option('--debug', '-d', help='Load a very verbose debugger, too', default=False)
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=8057)
@click.pass_context
def ors_standalone(ctx, api_key, debug, host, port):
    from circuits import Manager, Debugger
    from circuits.web import Server

    set_logfile('/tmp', 'mini')
    set_verbosity(5)

    app = Manager()

    if debug:
        debugger = Debugger().register(app)

    ors_controller = ORSService(api_key= api_key, no_db=True).register(app)

    try:
        server = Server(
            (host, port),
            display_banner=False,
            secure=False,
        ).register(app)
    except PermissionError as e:
        if port <= 1024:
            log("Could not open privileged port (%i), check permissions!"
                % port, e, lvl=critical,
                )
        else:
            log("Could not open port (%i):" % port, e, lvl=critical)
    except OSError as e:
        if e.errno == 98:
            log("Port (%i) is already opened!" % port, lvl=critical)
        else:
            log("Could not open port (%i):" % port, e, lvl=critical)

    app.run()
