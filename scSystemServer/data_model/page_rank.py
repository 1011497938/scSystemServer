from .db_manager import dbManager as db
from .neo4j_manager import graph
from .event_manager import eventManager, triggerManager
from .person_manager import personManager
from .relation2type import getEventScore
import json
import networkx as nx 

# import matplotlib.pyplot as plt 

def pageRank():
	event_array = eventManager.event_array
	G = nx.DiGraph()
	for event in event_array:
		score = getEventScore(event)
		roles = event.roles
		if len(roles)==1:
			node_id = roles[0]['person'].id
			G.add_node(node_id)
			G.add_weighted_edges_from([(node_id, node_id, score)])
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
				G.add_weighted_edges_from([(from_node, to_node, score)])
			else:
				# print('Error:没有凑齐一对节点')
				print(str(event))
	pr=nx.pagerank(G, weight='weight')
	person_rank = {}
	for person_id in pr:
		person_name = personManager.getPerson(person_id).name
		person_rank[person_name] = pr[person_id]
	open('scSystemServer/data_model/temp_data/pageRank.json', 'w', encoding='utf-8').write(json.dumps(person_rank, indent=3, ensure_ascii = False) )


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
				if node_id not in G:
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
				G.add_node(from_node)
				G.add_node(to_node)
				G.add_weighted_edges_from([(from_node, to_node,  1/abs(score))])

	def getSim(self, person1, person2):
		return nx.shortest_path_length(self.G,source=person1.id,target=person2.id)