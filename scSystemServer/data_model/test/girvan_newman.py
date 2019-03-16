import networkx as nx
graph = nx.Graph()
graph.add_nodes_from(['a', 'b', 'c', 'd', 'e'])
graph.add_edges_from([('a', 'b'), ('a', 'c'), ('b', 'c'),
                          ('c', 'd'), ('c', 'e'), ('d', 'e')])


import cylouvain
partition = cylouvain.best_partition(graph)
print(partition)

modularity = cylouvain.modularity(partition, graph)
print("Modularity: %0.3f\n" % modularity)