import networkx as nx 

G = nx.DiGraph()
G.add_node('1')
G.add_node('2')
G.add_weighted_edges_from([('2','1', 2)])
G.add_weighted_edges_from([('2','1', 3)])
G.add_node('2')
nx.pagerank(G)
print(G.has_edge('2','1'))
print(G['2']['1']['weight'])
