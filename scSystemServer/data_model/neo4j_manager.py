import sqlite3
import re
from opencc import OpenCC 
import json
from py2neo import Graph,Node,Relationship,cypher

class Neo4JManager(object):
	"""docstring for Neo4JManager"""
	def __init__(self):
		self._graph = Graph('http://localhost:7474',username='neo4j',password='123456')
		self._import_url = 'E:/Neo4JData/neo4jDatabases/database-ed7a278a-67c7-470d-ac3c-e90bf1a42253/installation-3.5.0/import/'
		self._csv_num = 0

		self._year2range = json.loads(open('scSystemServer/data_model/data/db/db_info/year2range.json','r', encoding='utf-8').read())

		self._code2range = {
			'-1':'之前',
			'0': '之间',
			'1': '之后',
			'2': '约',
			'300': '960-1082',
			'301': '1082-1279'
		}
		print('初始化neo4j管理器')


	def EventNode(self, event):
		new_node = Node('Event')
		new_node['id'] = event.id
		new_node['first_year'] = event.time_range[0]
		new_node['last_year'] = event.time_range[1]
		new_node['type'] = event.type
		new_node['is_state'] = event.is_state
		new_node['trigger'] = str(event.trigger)
		return new_node


	def AddrNode(self, addr):
		new_node = Node('Place')
		new_node['id'] = addr.id
		new_node['first_year'] = addr.first_year
		new_node['last_year'] = addr.last_year
		new_node['name'] = addr.name
		new_node['x'] = addr.x
		new_node['y'] = addr.y
		new_node['alt_names'] = addr.alt_names
		return new_node


	def PersonNode(self, person):
		new_node = Node('Person')
		new_node['person_id'] = person.person_id
		new_node['birth_year'] = person.birth_year 
		new_node['death_year'] = person.death_year
		new_node['start_year'] = person.range[0]
		new_node['end_year'] = person.range[1]
		new_node['tribe'] = person.tribe
		return new_node

	def run(self, query):
		# print(query)
		return self._graph.run(query)

	def runWithCsv(self, csv_data, query):
		csv_id = str(self._csv_num)
		
		fs = open(self._import_url + csv_id, 'w', encoding='utf-8')
		for row in csv_data:
			row = [str(elm) for elm in row]
			fs.write(','.join(row)+'\n')
		fs.close()
		self._csv_num  += 1
		print('写入import/{}成功'.format(csv_id))

		if query=='':
			print('query is empty in runWithCsv')
			# return
		return self.run('LOAD CSV WITH HEADERS FROM "file:///{}.csv" AS row '.format(csv_id) + query)

	def getTableRange(self, table, field):
		year2range = self._year2range
		if table in year2range.keys():
			year2range = year2range[table]
			if field in year2range.keys():
				return year2range[field]
		return None


	def isYear(self, field):
		return 'year' in field and 'range' not in field


	def getRange(self, range_code):
		if range_code in self._code2range.keys():
			return self._code2range[range_code]
		else:
			return range_code

graph = Neo4JManager()


if __name__ == '__main__':
	print('neo4j模块测试')

	# 用户画像
	# 受到媒体的影响
	# 描述特征
		# 分类
		# 内容

		# 相关

		# 相似度
		# 分类 -- 不同类别的属性剧变

		# 三元闭包
		# 群体发现

		# 属性合并
		# 网络节点中心度(重要度)
		# group
			# 社交网络
			# 两个网节点
		# 哑变量

