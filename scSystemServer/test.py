from django.http import HttpResponse
import json

def test_response(request):
    data = {'info': 'success'}
    return HttpResponse(json.dumps(data))


# import community
# import networkx as nx
# import matplotlib.pyplot as plt

# # Replace this with your networkx graph loading depending on your format !
# G = nx.erdos_renyi_graph(30, 0.05)

# #first compute the best partition
# partition = community.best_partition(G)
# print(partition)
# #drawing
# size = float(len(set(partition.values())))
# pos = nx.spring_layout(G)
# count = 0.
# for com in set(partition.values()) :
#     count = count + 1.
#     list_nodes = [nodes for nodes in partition.keys()
#                                 if partition[nodes] == com]
#     nx.draw_networkx_nodes(G, pos, list_nodes, node_size = 20,
#                                 node_color = str(count / size))


# nx.draw_networkx_edges(G, pos, alpha=0.5)
# plt.show()