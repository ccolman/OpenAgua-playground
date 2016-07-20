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

#conn = JsonConnection(url='www.openaguadss.org')
conn = JsonConnection()
conn.login(username = 'root', password = '')
session_id = conn.session_id
project_name = 'Monterrey'
network_name = 'base network'

def get_project_by_name(conn, project_name):
        return conn.call('get_project_by_name', {'project_name':project_name})

def get_network_by_name(conn, project_id, network_name):
        return conn.call('get_network_by_name', {'project_id':project_id, 'network_name':network_name})

# get project ID
try:
        project = get_project_by_name(conn, project_name)
except: # project doesn't exist, so let's create it
        proj = dict(name = project_name)
        project = conn.call('add_project', {'project':proj})
project_id = project.id       
        
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
                f = {'type':'LineString',
                     'geometry':{ 'type': 'LineString',
                                  'coordinates': [coords[n1],coords[n2]] },
                     'properties':{'name':l.name,
                                   'description':l.description,
                                   'linetype':ftype.name,
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
        return [s for s in shapes if s['type']==ftype]

# add features - formatted as geoJson - from Leaflet
def make_nodes(shapes):
        nodes = []
        for s in shapes:
                x, y = s['geometry']['coordinates']
                n = dict(
                        id = -s['id'],
                        #name = s['properties']['name'],
                        name = 'Point' + str(random.randrange(0,1000)),
                        description = 'It\'s a new node!',
                        x = str(x),
                        y = str(y)
                )
                nodes.append(n)
        return nodes

# use this to add shapes from Leaflet to Hydra
def add_features(conn, network_id, shapes):
        
        # modify to account for possibly no network... create network instead of add node
        
        # convert geoJson to Hydra features & write to Hydra
        points = get_shapes(shapes, 'Feature')
        nodes = make_nodes(points)
        
        polylines = get_shapes(shapes, 'Polyline')
        #links = make_links(polylines)
        links = []
        
        if network_id and points:
                nodes = conn.call('add_nodes', {'network_id': network_id, 'nodes': nodes})
        elif network_id and polylines:
                links = conn.call('add_links', {'network_id': network_id, 'links': links})
        else:
                network = conn.call('add_network', {'net':{'nodes':nodes, 'links':links}})
        
       
# add initial network data       
# update existing network - TEST - Hydra Platform does not work when adding / modifying networks
#def make_test_shapes():
        #shapes = []
        #for i in range(3):
                #x = str(random.uniform(-105,-95))
                #y = str(random.uniform(24,26))
                #name = "Res" + str(random.randrange(1,1000))
                #shape = {"id":1,"type":"Feature","properties":{"name":name,"feature_type":"Reservoir"},"geometry":{"type":"Point","coordinates":[x,y]}}
                #shapes.append(shape)
        #shapes = {"shapes": shapes}
        #return shapes

def get_network_features(conn, project_id, network_name):
        try:
                network = get_network_by_name(conn, project_id, network_name)
                coords = get_coords(network)
                nodes = nodes_geojson(network.nodes, coords)
                links = links_geojson(network.links, coords)
                features = nodes + links  
        except:
                network = None
                features = []
        return network, features

network, features = get_network_features(conn, project_id, network_name)

#
# Flask app
#

app = Flask(__name__)

@app.route('/')
def index():
        return render_template('index.html',
                               session_id=session_id,
                               project_name=project_name,
                               network_name=network_name,
                               features=features)

@app.route('/_save_network')
def save_network():
        
        network, features = get_network_features(conn, project_id, network_name)
        
        new_features = request.args.get('new_features')
        new_features = json.loads(new_features)['shapes']        
        
        if not network and new_features:
                #add_features(conn, None, new_features)
                status_id = 0
                status_message = 'New network created'        
        if network and new_features:
                add_features(conn, network.id, new_features)
                status_id = 1
                status_message = 'Edits saved'
        else:
                status_id = 2
                status_message = 'No edits detected'

        # get updated network and features
        network, features = get_network_features(conn, project_id, network_name)
        
        result = dict(
                status_id = status_id,
                status_message = status_message,
                features = features
                )
        
        result_json = jsonify(result=result)
        return result_json
        
if __name__ == "__main__":
        
        app.run(debug=True)
