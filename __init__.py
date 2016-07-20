from flask import Flask, jsonify, Response, json, request, session, redirect, url_for, escape, send_file, render_template
import random # delete later - used to create randomly distributed test nodes around Monterrey
import requests

import logging

import pandas
from pandas.io.json import json_normalize
import sys
from os.path import expanduser
from os.path import join
import json

from HydraLib.PluginLib import JsonConnection

#
# connect - this should be done through the interface
#

conn = JsonConnection()
conn.login(username = 'root', password = '')
session_id = conn.session_id
project_name = 'Monterrey'
network_name = 'base_network'

def get_project_by_name(conn, project_name):
        return conn.call('get_project_by_name', {'project_name':project_name})

def get_network_by_name(conn, project_name, network_name):
        project = get_project_by_name(conn, project_name)
        return conn.call('get_network_by_name', {'project_id':project.id, 'network_name':network_name})

def get_network(conn, network_id):
        return conn.call('get_network', {'network_id':network_id})    
        
# convert hydra nodes to geoJson for Leaflet
def nodes_geojson(nodes, coords):
        gj = []
        for n in nodes:
                if n.types:
                        ftype = n.types[0] # assume only one template
                        ftype_name = ftype.name
                        template_name = ftype.template_name
                else:
                        ftype_name = 'UNASSIGNED'
                        template_name = 'UNASSIGNED'
                f = {'type':'Feature',
                           'geometry':{'type':'Point',
                                       'coordinates':coords[n.id]},
                           'properties':{'name':n.name,
                                         'description':n.description,
                                         'nodetype':ftype_name,
                                         'template':template_name,
                                         'popupContent':'TEST'}} # hopefully this can be pretty fancy
                gj.append(f)
        return gj

def links_geojson(links, coords):
        gj = []
        for l in links:
                n1 = l['node_1_id']
                n2 = l['node_2_id']
                if l.types:
                        ftype = l.types[0] # assume only one template
                        ftype_name = ftype.name
                        template_name = ftype.template_name
                else:
                        ftype_name = 'UNASSIGNED'
                        template_name = 'UNASSIGNED'
                f = {'type':'Feature',
                     'geometry':{ 'type': 'LineString',
                                  'coordinates': [coords[n1],coords[n2]] },
                     'properties':{'name':l.name,
                                   'description':l.description,
                                   'linetype':ftype_name,
                                   'template':template_name,
                                   'popupContent':'TEST'}}
                
                gj.append(f)
        
        return gj

def get_coords(network):
        coords = {}
        for n in network['nodes']:
                coords[n.id] = [float(n.x), float(n.y)] 
        return coords


# get shapes of type ftype
def get_shapes(shapes, ftype):
        return [s for s in shapes if s['geometry']['type']==ftype]

# make nodes - formatted as geoJson - from Leaflet
def make_nodes(shapes):
        nodes = []
        for s in shapes:
                x, y = s['geometry']['coordinates']
                n = dict(
                        id = -1,
                        #name = s['properties']['name'],
                        name = 'Point' + str(random.randrange(0,1000)),
                        description = 'It\'s a new node!',
                        x = str(x),
                        y = str(y)
                )
                nodes.append(n)
        return nodes

# make links - formatted as geoJson - from Leaflet
# need to account for multisegment lines
# for now, this assumes links lack vertices
def make_links(polylines, coords):
        d = 4 # rounding decimal points to match link coords with nodes.
        # p.s. This is annoying. It would be good to have geographic/topology capabilities built in to Hydra
        nlookup = {(round(x,d), round(y,d)): k for k, [x, y] in coords.items()}
        links = []
        for pl in polylines:
                xys = []
                for [x,y] in pl['geometry']['coordinates']:
                        xy = (round(x,d), round(y,d))
                        xys.append(xy)
                
                l = dict(
                        id = -1,
                        #name = pl['properties']['name'],
                        name = 'Link' + str(random.randrange(0,1000)),
                        description = 'It\'s a new link!',
                        node_1_id = nlookup[xys[0]],
                        node_2_id = nlookup[xys[1]]
                )
                links.append(l)
        return links

def add_network(conn, project_name):
        network = conn.call('add_network', {'net':{'nodes':[], 'links':[]}})       

# use this to add shapes from Leaflet to Hydra
def add_features(conn, network_id, shapes):
        
        # modify to account for possibly no network... create network instead of add node
        
        # convert geoJson to Hydra features & write to Hydra
        points = get_shapes(shapes, 'Point')
        polylines = get_shapes(shapes, 'LineString')    
        
        if points:
                nodes = make_nodes(points)
                if nodes:
                        nodes = conn.call('add_nodes', {'network_id': network_id, 'nodes': nodes})
        if polylines:
                network = get_network(conn, network_id)
                coords = get_coords(network)                   
                links = make_links(polylines, coords)
                if links:                         
                        links = conn.call('add_links', {'network_id': network_id, 'links': links})

def get_features(network):
        coords = get_coords(network)
        nodes = nodes_geojson(network.nodes, coords)
        links = links_geojson(network.links, coords)
        features = nodes + links
        return features

#
# Set up project. To be deleted once we can integrate into the UI.
#

# load / create project
try:
        project = get_project_by_name(conn, project_name)
except: # project doesn't exist, so let's create it
        proj = dict(name = project_name)
        project = conn.call('add_project', {'project':proj})  

# load / create network
exists = conn.call('network_exists', {'project_id':project.id, 'network_name':network_name})
if exists=='Y':
        network = get_network_by_name(conn, project_name, network_name)
else:
        net = dict(
                project_id = project.id,
                name = network_name,
                description = 'Prototype DSS network for Monterrey'
        )
        network = conn.call('add_network', {'net':net})
activated = conn.call('activate_network', {'network_id':network.id})

#polyline = dict(
        #type = 'Feature',
        #geometry = {
                #'type': 'Point',
                #'coordinates': [[-99.7012322, 25.0], [-101.2172767, 25.95]]
                #},
        #properties = {
                #"name": "Dinagat Islands"
                #}
        #)
#polylines = [polyline]
#coords = get_coords(network)
#links = make_links(polylines, coords)

# get features (blank if network is new)
features = get_features(network)

#
# Flask app
#

app = Flask(__name__)

@app.route('/')
def index():
        return render_template('index.html',
                               session_id=session_id,
                               project_name=project_name,
                               network_name=network_name)

@app.route('/_load_network')
def load_network():
        network = get_network_by_name(conn, project_name, network_name)
        features = get_features(network)
        
        status_id = 1
        status_message = 'Network "%s" loaded' % network_name
        
        features = json.dumps(features)
        result = dict( status_id = status_id, status_message = status_message, features = features )
        result_json = jsonify(result=result)
        return result_json

@app.route('/_save_network')
def save_network():
        
        network = get_network_by_name(conn, project_name, network_name)
        features = get_features(network)
        
        new_features = request.args.get('new_features')
        new_features = json.loads(new_features)['shapes']        
        
        if new_features:
                add_features(conn, network.id, new_features)
                network = get_network(conn, network.id) # get updated network
                features = get_features(network) # get updated features
                status_id = 1
                status_message = 'Edits saved'
        else:
                status_id = 2
                status_message = 'No edits detected'

        # get updated network and features
        
        features = json.dumps(features)
        result = dict(
                status_id = status_id,
                status_message = status_message,
                features = features
                )
        
        result_json = jsonify(result=result)
        return result_json
        
if __name__ == "__main__":
        
        app.run(debug=True)
