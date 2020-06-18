# 用于存储社团发现算法(目前是无权重的)
import networkx as nx
# import cylouvain
from django.http import HttpResponse
import json

import community

def getCommunity(request):
    node_num = int(request.GET.get('num'))
    links = request.GET.get('links')
    # print(links, node_num)
    links = links.split(',')
    # print(links)
    graph = nx.Graph()
    graph.add_nodes_from([str(id) for id in range(0,node_num)])

    node_links = []
    for link in links:
        link = link.split('-')
        node_links.append((link[0], link[1]))  #cylouvain
    # print(node_links, graph.nodes) 
    graph.add_edges_from(node_links)
    partition = community.best_partition(graph)
    # cylouvain.best_partition(graph)
    # print(partition)
    return HttpResponse(json.dumps({ 'data':partition, 'info': '社团发现'}))