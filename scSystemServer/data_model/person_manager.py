import sqlite3
import re
from opencc import OpenCC 
import json
from .db_manager import dbManager as db
from .neo4j_manager import graph
from .addr_manager import addrManager
import math
import numpy as np

class PersonManager(object):
	"""docstring for PersonManager"""
	def __init__(self):
		self.id2person = {}  #c_personid
		self.id_set = set()
		self.person_array = []
		self.event_manager = None
		self.all2vec = None
		print('初始化人物')

		self.song_people = set()  #整理所有的宋朝人物

	def calculateAllSongPeople(self):
		self.song_people = set()
		for person in self.person_array:
			if person.isSong():
				self.song_people.add(person)

		for event in self.event_manager.event_array:
			if event.isCertain():
				if event.time_range[0] < 1500 or event.time_range[0]>800:
					for elm in event.roles:
						this_person = elm['person']
						self.song_people.add(this_person)
		for depth in range(0,2):
			literal_song_people = list(self.song_people)
			for person in literal_song_people:
				events = person.getAllEvents()
				for event in events:
					for elm in event.roles:
						this_person = elm['person']
						# if not this_person.isSong():
						self.song_people.add(this_person)



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

		self.page_rank = 0

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
			else:
				self.birth_year = -9999
			# 	self.birth_year = self.range[0]
			if death_year!=0 and death_year!='0' and death_year!='null' and death_year is not None:
				death_event = event_manager.createEvents('death'+ self.id)
				death_event.addTimeAndRange(int(death_year), '之间')
				death_event.addPerson(self, '主角')
				death_event.setTrigger('死亡')
				# self.range[1] = death_year
			else:
				self.death_year = 9999
				# self.death_year = self.range[1]
			self.event_manager = event_manager
		else:
			print("WARNNING: 没有给person_manager注册event_manager")

		self.has_all_events = False
		self.year2event = None
		self.score_array = None

	def getRelatedEvents(self, limit_depth = 3):
		print('开始爬取所有相关人员事件', self, limit_depth)
		has_pull = set()
		need_pull = set()
		person2depth = {}

		start_person = self
		need_pull.add(start_person)
		person2depth[hash(start_person)] = 1

		all_events = set()

		while(len(need_pull)!=0):
			person = need_pull.pop()
			has_pull.add(person)

			now_depth = person2depth[hash(person)]
			events = person.getAllEvents()
			for event in events:
				all_events.add(event)
				roles = event.roles
				for role in roles:
					related_person = role['person']
					hash_vale = hash(related_person)
					if hash_vale in person2depth:    #更新子节点的depth
						this_depth = person2depth[hash_vale]
						if this_depth>now_depth+1:
							person2depth[hash_vale] = now_depth+1
							if this_depth>=limit_depth and now_depth+1<limit_depth and related_person in has_pull:   #如果发现层数更近恢复
								has_pull.remove(related_person)
								need_pull.add(related_person)
					else:
						person2depth[hash_vale] = now_depth+1
						if now_depth<limit_depth and related_person not in has_pull:
							need_pull.add(related_person)
			# print(len(has_pull), person, person2depth[hash(person)])

		return list(all_events)


	def getSortedEvents(self):
		# 还要加入sequence的比较
		sort_events = []
		for event in self.event_array:
			if event.time_range[1]-event.time_range[0]<2:    #True:# 
				sort_events.append(event)
		return sorted(sort_events, key=lambda event: float(event.time_range[0])+float(event.sequence)*0.1) 
	
	def getYear2event(self):
		# 注意浅拷贝！！！！
		# if self.year2event is None:
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
		self.year2event = year2event
		# print(len(year2event.keys()))
		return self.year2event


	# -9999也加进去了
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

	def getScoreArray(self, Align=False):
		if self.score_array is None:
			year2event = self.getYear2event()
			year2score = {}
			year2score_array = []
			for year in year2event:
				events = year2event[year]
				total_score = 0
				# event_length = 0
				for event in events:
					# idf = personManager.all2vec.event2idf[event.getTriggerId(self)]
					total_score += event.getScore(self)
					# event_length += idf
				# print(event_length, total_score)
				# min_score = total_score/event_length*math.log(event_length+1)
				min_score = total_score/len(events)*math.log(len(events)+1)
				year2score[year] = min_score
				year2score_array.append([int(year), min_score])
			year2score_array = sorted(year2score_array, key=lambda elm: elm[0])
			self.score_array = year2score_array
			if Align and len(self.score_array)>0: 
				self.score_array = [[elm[0]-self.score_array[0][0], elm[1]]  for elm in self.score_array]
			self.score_array = np.array(self.score_array)
		return list(self.score_array)

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
		year2event = self.getYear2event()
		years = year2event.keys()
		return {
			'id': self.id,
			'name': self.name,
			'birth_year': self.birth_year,
			'death_year': self.death_year,
			'certain_events_num': self.getCertaintyLength(),
			'events_num': len(self.event_array),
			'page_rank': self.page_rank,
			'year2vec': { year:personManager.all2vec.year_person2vec[self.id + ',' + str(year)].tolist()  for year in years}
			# 'events': [event.id for event in self.event_array]
			# 'time_range': self.range
		}

	def isSong(self):
		return (self.dy==15 or self.dy=='15' or self in personManager.song_people) # and len(self.event_array)>=10

	def inferUncertainty(self, all2vec):
		all_events = set()

		def getTriggerId(event, person):
			for role in event.roles:
				if role['person'] == person:
					return event.trigger.name + ' ' + role['role']
			return None

		year2events = self.getYear2event()
		events_with_infer = {}
		for year in year2events:
			events =year2events[year]
			# infer = set()
			events_with_infer[year] = {}

			# 记得分个类
			type2event = {}
			for event in events:
				trigger_type = event.trigger.parent_type
				if trigger_type in type2event:
					type2event[trigger_type].append(event)
				else:
					type2event[trigger_type] = [event]
			# print(type2event)
			for trigger_type in type2event:
				events = type2event[trigger_type]	
				triggers = [getTriggerId(event, self)  for event in events]
				most_similar = all2vec.trigger_model.most_similar(positive=triggers, topn=30)
				# print(triggers, most_similar)
				count = 0
				for sim_trigger, sim in most_similar:
					if sim<0.45:
						continue
					for event in self.event_array:
						if count>20:
							continue
						time_range = event.time_range
						# print(time_range, year, getTriggerId(event, self), sim_trigger)
						year = int(year)
						if year<=time_range[1] and year>=time_range[0] and getTriggerId(event, self)==sim_trigger and time_range[1]!=time_range[0]:
							count += 1
							# print(event)
							if event.id in events_with_infer[year]:
								now_sim = events_with_infer[year][event.id]['sim']
								if now_sim<sim:
									events_with_infer[year][event.id]['sim'] = sim
							else:
								# print(event)
								events_with_infer[year][event.id] = {
									'event': event,
									'sim': sim
								}
							all_events.add(event)
		return events_with_infer, list(all_events)

	def getCertaintyLength(self):
		return len([ event for event in self.event_array if event.time_range[0]==event.time_range[1] and event.time_range[0]!=-9999])

personManager = PersonManager()

if __name__ == '__main__':
	print('测试人物模块')

