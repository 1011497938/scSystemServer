import re
import json
from .db_manager import dbManager as db
from .neo4j_manager import graph

# 暂时还没有用上
class TimeManager(object):
	"""docstring for timeManager"""
	def __init__(self):
		self.nian_hao = {}

		data = graph.run('MATCH (n:Nian_hao) RETURN n').data()
		for nian_hao in data:

			nian_hao = nian_hao['n']
			# print(nian_hao)
			name = nian_hao['c_nianhao_chn']
			id = nian_hao['c_nianhao_id']
			start_year = nian_hao['c_firstyear']
			end_year = nian_hao['c_lastyear']
			range = [-9999, 9999]
			def isYear(year):
				return year is not None and year != 'None' and re.match('[-]*[0-9]+', str(year))
			if isYear(start_year):
				range[0] = int(start_year)
			if isYear(end_year):
				range[1] = int(end_year)

			self.nian_hao[id] = {
				'name': name,
				'id': id,
				'time_range': range
			}

	def getNianHaoRange(self, nian_hao_code):
		if nian_hao_code in self.nian_hao.keys():
			return self.nian_hao[nian_hao_code]['time_range']
		return [-9999,9999]	
	

timeManager = TimeManager()