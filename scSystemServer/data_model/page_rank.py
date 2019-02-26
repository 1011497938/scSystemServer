from .db_manager import dbManager as db
from .neo4j_manager import graph
from .event_manager import eventManager, triggerManager
from .person_manager import personManager
from .relation2type import getEventScore
import json
import networkx as nx 
import numpy as np
import traceback 

# import matplotlib.pyplot as plt 


def pageRank(event_array):
	# event_array = eventManager.event_array
	G = nx.DiGraph()
	# nx.MultiDigraph() 版本没有
	for event in event_array:
		score = 1 #getEventScore(event)
		roles = event.roles
		if len(roles)==1:
			person = roles[0]['person']
			node_id = person.id
			G.add_node(node_id)
			if G.has_edge(node_id,node_id):
				if G[node_id][node_id]['weight']<score:
					G.add_weighted_edges_from([(node_id, node_id, score)])
			else:
				G.add_weighted_edges_from([(node_id, node_id, score)])
			# G.add_weighted_edges_from([(node_id, node_id, score)])
		else:
			from_node = None
			to_node = None
			for elm in roles:
				person = elm['person']
				role = elm['role']
				if role == '主角':
					from_node = person.id
				else:
					to_node = person.id
			if from_node is not None and to_node is not None:
				G.add_node(from_node)
				G.add_node(to_node)
				if G.has_edge(from_node,to_node):
					if G[from_node][to_node]['weight']<score:
						G.add_weighted_edges_from([(from_node, to_node, score)])
				else:
					G.add_weighted_edges_from([(from_node, to_node, score)])

	person_rank = {}
	# print(len(G.nodes))
	pr=nx.pagerank(G, weight='weight', max_iter=1000)

	ranks = np.array([pr[person_id] for person_id in pr])
	max = np.max(ranks)
	min = np.min(ranks)

	for person_id in pr:
		rank = pr[person_id]
		rank = (rank-min)/(max-min)
		person = personManager.getPerson(person_id)
		person_name = person.name
		person.page_rank = rank
		person_rank[person_name] = rank
	open('scSystemServer/data_model/temp_data/pageRank.json', 'w', encoding='utf-8').write(json.dumps(person_rank, indent=3, ensure_ascii = False) )
	return pr

# 计算一下每年的page_rank

# 用于计算关系网络
class PersonGraph(object):
	"""docstring for PersonGraph"""
	def __init__(self, eventManager):
		print('开始构建关系有向图')
		self.G = nx.Graph()
		G = self.G

		event_array = eventManager.event_array
		for event in event_array:
			score = getEventScore(event)
			if score == 0:
				score = 1
			roles = event.roles
			if len(roles)==1:
				node_id = roles[0]['person'].id
				G.add_node(node_id)
				G.add_weighted_edges_from([(node_id, node_id, 1/abs(score))])
			else:
				from_node = None
				to_node = None
				for elm in roles:
					person = elm['person']
					role = elm['role']
					if role == '主角':
						from_node = person.id
					else:
						to_node = person.id
				if from_node is not None and to_node is not None:
					G.add_node(from_node)
					G.add_node(to_node)
					G.add_weighted_edges_from([(from_node, to_node,  1/abs(score))])

	def getSim(self, person1, person2):
		# if person1.id not in self.G or person2.id not in self.G:
		# 	return 9999
		try:
			# print(person1, person2, nx.shortest_path_length(self.G,source=person1.id,target=person2.id))
			return nx.shortest_path_length(self.G,source=person1.id,target=person2.id)
		except:  
			traceback.print_exc()
			print(person1, person2, '中间没得路径')
			return 9999
		
		