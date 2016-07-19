# import
import pandas
from pandas.io.json import json_normalize
import sys
from os.path import expanduser
from os.path import join
import json

from HydraLib.PluginLib import JsonConnection

url = 'www.openaguadss.org'
conn = JsonConnection(url=url)
conn.login(username = 'root', password = '')

def get_project_by_name(conn, project_name):
    return conn.call('get_project_by_name',
                     {'project_name':project_name})

def get_network_by_name(conn, project_id, network_name):
    return conn.call('get_network_by_name',
                     {'project_id':project_id, 'network_name':network_name})

# get project ID
project_name = 'Water Allocation Demo'
project = get_project_by_name(conn, project_name)
project_id = project.id

# get network ID
network_name = 'Water Allocation Network'
network = get_network_by_name(conn, project_id, network_name)
network_id = network.id

# get nodes
nodes = json_normalize(network.nodes)
n = nodes.id.values

# get links
links = json_normalize(network.links)
n1 = links.node_1_id.values
n2 = links.node_2_id.values
l = zip(*[n1,n2])

#
# create the model
#

from pyomo.environ import *

# create abstract model

m = AbstractModel()

# SETS

# nodes & links
m.nodes = Set(initialize=n)
m.links = Set(initialize=l)

# PARAMETERS

# VARIABLES


print(m.links)

print('finished')