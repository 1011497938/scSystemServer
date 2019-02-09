import sqlite3
import re
from opencc import OpenCC 
import json
from .db_manager import dbManager as db
from .neo4j_manager import graph
from .addr_manager import addrManager

class PersonManager(object):
	"""docstring for PersonManager"""
	def __init__(self):
		self.id2person = {}  #c_personid
		self.id_set = set()
		self.person_array = []
		self.event_manager = None
		print('初始化人物')

	def createPerson(self,bio_main_node):
		new_id = bio_main_node['c_personid']
		if new_id in self.id_set:
			return self.id2person[new_id]
		else:
			new_person = Person(bio_main_node, self.event_manager)
			self.id2person[new_id] = new_person
			self.person_array.append(new_person)
			self.id_set.add(new_id)
			return new_person
		# 之后可以添加序列化功能

	def getPerson(self, person_id):
		person_id = str(person_id)
		if person_id in self.id_set:
			return self.id2person[person_id]
		else:
			print('run')
			data = graph.run('MATCH (n:Biog_main{{c_personid:"{}"}}) RETURN n'.format(str(person_id))).data()
			if len(data)!=0:
				# print(data[0])
				return self.createPerson(data[0]['n'])
		return None

	def registEventManager(self, eventManager):
		self.event_manager = eventManager

	def getEventsBetween(self, person1, person2):
		events1 = person1.event_array
		events2 = person2.event_array

		return [event for event in events1 if event in events2]


# 还需要一个年号对应的类
class Person(object):
	"""docstring for Person"""
	def __init__(self, bio_main_node, event_manager):
		# from event_manager import eventManager
		self.id = bio_main_node['c_personid']
		self.name = bio_main_node['c_name_chn']

		self.birth_year = bio_main_node['c_birthyear']
		self.death_year = bio_main_node['c_deathyear']

		self.event_array = []  #所有出现的event

		# 还要添加别名,籍贯等内容
		# self.range = [-9999,9999]  # range	暂时不计算,还有很多时间也没有添加
		
		self.index_year = bio_main_node['c_index_year']
		self.dy_nh_code = bio_main_node['c_dy_nh_code']          #在世始年
		self.index_year = bio_main_node['c_index_year']          #在世始年

		self.dy = bio_main_node['c_dy']
		if self.dy is not None:
			self.dy = int(self.dy)
		# self.dy = bio_main_node['c_dy']

		self.tribe = bio_main_node['c_tribe']   #"部、族"

		if event_manager is not None:
			# 创建出生死亡事件
			birth_year = self.birth_year
			death_year = self.death_year
			if birth_year!=0 and birth_year!='0' and birth_year!='null' and birth_year is not None:
				birth_event = event_manager.createEvents('birth'+ self.id)
				birth_event.addTimeAndRange(int(birth_year), '之间')
				birth_event.addPerson(self, '主角')
				birth_event.setTrigger('出生')
			# 	self.range[0] = birth_year
			# else:
			# 	self.birth_year = self.range[0]
			if death_year!=0 and death_year!='0' and death_year!='null' and death_year is not None:
				death_event = event_manager.createEvents('death'+ self.id)
				death_event.addTimeAndRange(int(death_year), '之间')
				death_event.addPerson(self, '主角')
				death_event.setTrigger('死亡')
				# self.range[1] = death_year
			# else:
				# self.death_year = self.range[1]
			self.event_manager = event_manager
		else:
			print("WARNNING: 没有给person_manager注册event_manager")

		self.has_all_events = False

	def getSortedEvents(self):
		# 还要加入sequence的比较
		sort_events = []
		for event in self.event_array:
			if event.time_range[1]-event.time_range[0]<2:    #True:# 
				sort_events.append(event)
		return sorted(sort_events, key=lambda event: float(event.time_range[0])+float(event.sequence)*0.1) 

	def getYear2event(self):
		self.getAllEvents()
		year2event = {}
		# print(len(self.event_array))
		for event in self.event_array:
			if event.time_range[1]-event.time_range[0]==0 and event.time_range[0]!=-9999 and event.time_range[1]!=9999:
				# print('addd')
				for year in range(event.time_range[0], event.time_range[1]+1):
					if year not in year2event.keys():
						year2event[year] = []
					year2event[year].append(event)

		for year in year2event.keys():
			year2event[year] = sorted(year2event[year], key=lambda event: float(event.time_range[0])+float(event.sequence)*0.1) 
		# print(len(year2event.keys()))
		return year2event

	def temp_getYear2event(self):
		self.getAllEvents()
		year2event = {}
		year2event[-9999] = []
		# print(len(self.event_array))
		for event in self.event_array:
			if event.time_range[1]-event.time_range[0]==0 and event.time_range[0]!=-9999 and event.time_range[1]!=9999:
				# print('addd')
				for year in range(event.time_range[0], event.time_range[1]+1):
					if year not in year2event.keys():
						year2event[year] = []
					year2event[year].append(event)
			else:
				year2event[-9999].append(event)

		for year in year2event.keys():
			year2event[year] = sorted(year2event[year], key=lambda event: float(event.time_range[0])+float(event.sequence)*0.1) 
		# print(len(year2event.keys()))
		return year2event

	def getAllEvents(self):
		# if not self.has_all_events:
		# 	# 获得所有相关事件
		# 	person_id = self.id
		# 	has1 = has2 = has3 = has4 = True
		# 	# , person_id=person_id
		# 	for times in range(0,1):
		# 		if has1:
		# 			has1 = self.event_manager.loadRelationEvents(LIMIT = 10000,SKIP = 10000*times, person_id=person_id)   #person_id=3767 苏轼
		# 		if has2:
		# 			has2 = self.event_manager.loadPostOfficeEvents(LIMIT = 10000,SKIP = 10000*times, person_id=person_id)
		# 		if has3:
		# 			has3 = self.event_manager.loadTextEvents(LIMIT = 10000,SKIP = 10000*times, person_id=person_id)
		# 		if has4:
		# 			has4 = self.event_manager.loadEntryEvents(LIMIT = 10000,SKIP = 10000*times, person_id=person_id)
		# 		if not has1  and not has2 and not has3 and not has4:
		# 			break
		# 	self.has_all_events = True
		# 	self.event_array = sorted(self.event_array, key=lambda event: event.time_range[0]) 
		return self.event_array

	def bind_event(self, event):
		if event not in self.event_array:
			self.event_array.append(event)
			# if self.birth_year != -9999:
			# 	event.addTimeAndRange(self.birth_year, '之后')
			# if self.death_year != 9999:
			# 	event.addTimeAndRange(self.death_year, '之前')


	def __str__(self):
		# return '[(人物) id:{}, 姓名:{}, range:{}]'.format(str(self.id), str(self.name), str(self.range))
		return '[(人物) id:{}, 姓名:{}]'.format(str(self.id), str(self.name))

	def allEvent2String(self):
		self.event_array = self.getSortedEvents()
		return '\n'.join([str(event) for event in self.event_array])
		
	def __hash__(self):
		return hash(str(self.id)+'人物')

	def toDict(self):
		return {
			'id': self.id,
			'name': self.name,
			'birth_year': self.birth_year,
			'death_year': self.death_year,
			# 'events': [event.id for event in self.event_array]
			# 'time_range': self.range
		}

	def isSong(self):
		return (self.dy==15 or self.dy=='15') and len(self.event_array)>=10

personManager = PersonManager()

if __name__ == '__main__':
	print('测试人物模块')

