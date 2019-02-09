from .event_manager import eventManager, triggerManager
from .person_manager import personManager
from .addr_manager import addrManager
from .neo4j_manager import graph
from py2neo import Graph,Node,Relationship,cypher
from .time_manager import timeManager
# from relation2type import getRelTypes
from .page_rank import pageRank,PersonGraph
from .word2vec import All2vec

import json
# from word2vec import allEvents2Vec,allPerson2Vec,relationEmbedding
import threading
import time
import json

import numpy as np
import math
from multiprocessing import cpu_count
import random
import math

personManager.registEventManager(eventManager)


def getPersonStory(person_id, limit_depth = 3, period_year = None, period_range = 2):
	print('开始爬取所有相关数据')
	has_pull = set()
	need_pull = set()
	person2depth = {}

	person_id = str(person_id)
	start_person = personManager.getPerson(person_id)
	need_pull.add(start_person)
	person2depth[hash(start_person)] = 1

	all_events = set()

	while(len(need_pull)!=0):
		person = need_pull.pop()
		has_pull.add(person)
		# print(str(person))

		now_depth = person2depth[hash(person)]
		person.getAllEvents()
		events = person.event_array
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
						if this_depth>limit_depth and now_depth+1<limit_depth:   #如果发现层数更近恢复
							has_pull.remove(related_person)
							need_pull.add(related_person)
				else:
					person2depth[hash_vale] = now_depth+1
					if now_depth<limit_depth and related_person not in has_pull:
						need_pull.add(related_person)
		# print(len(has_pull))

	return list(all_events)

	persons = {}
	events = {}
	addrs = {}
	triggers = {}

	for event in all_events:
		# 只留下有关的事件
		# 暂时只筛选了时间，还应该考虑人物等
		if period_year is not None:
			time_range = event.time_range
			if (time_range[0]>(period_year+period_range) or time_range[0]<(period_year-period_range)) and (time_range[1]>(period_year+period_range) or time_range[1]<(period_year-period_range)):
				continue

		events[event.id] = event.toDict()

		for addr in event.addrs:
			addrs[addr.id] = addr.toDict()

		if event.trigger is not None:
			triggers[event.trigger.id] = event.trigger.toDict()

		for role in event.roles:
			person = role['person']
			# print(person)
			persons[person.id] = person.toDict()

	data = {
		'persons': persons,
		'events': events,
		'addr': addrs,
		'triggers': triggers
	}
	return data

eventManager.getAll()
all2vec = All2vec(personManager, addrManager, eventManager)
person_graph = PersonGraph(eventManager)
# data = getPersonStory('3767', limit_depth=1, period_year = 1079, period_range = 10) 	#苏轼

# 接下来是非常奇怪的计算环节
# 似乎有问题
def cos_sim(vector_a, vector_b):
    vector_a = np.mat(vector_a)
    vector_b = np.mat(vector_b)
    num = float(vector_a * vector_b.T)
    denom = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    cos = num / denom
    sim = 0.5 + 0.5 * cos
    # print('sim'+ str(sim))
    return sim

def dist_sim(vector_a, vector_b):
	return np.linalg.norm(np.mat(vector_a) - np.mat(vector_b))
# 对不同的确实信息应该有不同的计算方式
def caclute_sim(event1, event2):
	# 计算地点的最小距离
	addr_diff = 1
	trigger_diff = 1
	person_diff = 0
	time_diff = 1
	def isValidRange(event):
		return event.time_range[0]!=-9999 and event.time_range[1]!=9999
	if isValidRange(event1) and isValidRange(event2):
		time_diff = dist_sim(event1.time_range, event2.time_range)/9999
		# cos_sim( event1.time_range, event2.time_range )


	for addr1 in event1.addrs:
		for addr2 in event2.addrs:
			if addr1.id in all2vec.addr2vec and addr2.id in all2vec.addr2vec:
				# v1 = all2vec.addr2vec[addr1.id]
				# v2 = all2vec.addr2vec[addr2.id]
				diff = all2vec.addr_model.similarity(addr1.id, addr2.id)
				if addr_diff>diff:
					addr_diff = diff
			else:
				if addr1.id not in all2vec.addr2vec:
					print(addr1.name + '不存在')
				if addr2.id not in all2vec.addr2vec:
					print(addr2.name + '不存在')	

	for role1 in event1.roles:
		for role2 in event2.roles:
			trigger_id1 = event1.trigger.name + ' ' + role1['role']
			trigger_id2 = event2.trigger.name + ' ' + role2['role']
			if trigger_id1 in all2vec.trigger2vec and trigger_id2 in all2vec.trigger2vec:
				v1 = all2vec.trigger2vec[trigger_id1]
				v2 = all2vec.trigger2vec[trigger_id2]
				# diff = cos_sim(v1,v2)
				diff = all2vec.trigger_model.similarity(trigger_id1, trigger_id2)
				if trigger_diff>diff:
					trigger_diff = diff
				# print(trigger_id1 + ' 存在')
			# else:
			# 	if trigger_id1 not in all2vec.trigger2vec:
			# 		print(trigger_id1 + ' 不存在')
			# 	if trigger_id2 not in all2vec.trigger2vec:
			# 		print(trigger_id2 + ' 不存在')	

	allperson = set()
	for role1 in event1.roles:
		for role2 in event2.roles:
			person1 = role1['person']
			person2 = role2['person']
			allperson.add(person1)
			allperson.add(person2)
	allperson = list(allperson)
	for person1 in allperson:
		for person2 in allperson:
			person_diff += person_graph.getSim(person1, person2)
	person_diff /= 10   #理论上最大为10

	# print(event1, event2, addr_diff,trigger_diff,time_diff,person_diff)
	# 计算事件的最小距离
	# 
	return (addr_diff+trigger_diff*3+time_diff+person_diff*4)/9

reuslts = {}

thread_array = []

# 如果是两个人的关系
# 如果是有时间的
# 如果是有地点的
def thread_func(event):
	# # 在两年中找关系
	# if len(event.roles)>1:
	# 	person1 = event.roles[0]['person']
	# 	person2 = event.roles[1]['person']
	# 	related_events = personManager.getEventsBetween(person1, person2)
	# 	for role in event.roles:
	# 		this_person = role['person']
	# 		trigger_id = event.trigger.name + ' ' + role['role']
	# 		most_similar = all2vec.trigger_model.most_similar(positive=[trigger_id], topn=30)
	# 		for related_event in related_events:
	# 			if related_events:
	# 				pass

	related_events = []
	# 找到另一个人
	ops_person = None
	for role in event.roles:
		this_person = role['person']
		trigger_id = event.trigger.name + ' ' + role['role']
		if trigger_id in all2vec.trigger2vec:
			most_similar = all2vec.trigger_model.most_similar(trigger_id, topn=30)
			# all2vec.trigger_model.most_similar(positive=[trigger_id], topn=30)
			most_similar = [item[0] for item in most_similar]
			# related_events  + this_person.getAllEvents()

			this_person_events = this_person.getAllEvents() 
			for this_event in this_person_events:
				for role in this_event.roles:
					if this_person == role['person']:
						trigger_id = this_event.trigger.name + ' ' + role['role']
						if trigger_id in most_similar:
							related_events.append(this_event)

	#看情况判断要不要加
	# related_events = [this_event for this_event in related_events if this_event != event and (len(this_event.addrs)!=0 or this_event.time_range[0]!=-9999 or this_event.time_range[1]!=9999)]
	related_events = list(set(related_events))
	sim = {}
	for related_event in related_events:
		sim[(event, related_event)] = caclute_sim(event, related_event)

	related_events = sorted(related_events, key=lambda related_event: sim[(event, related_event)])
	if len(related_events)>40:
		related_events = related_events[0:40]

	reuslts[event.id] = {
		'event': str(event),
		'related_events': [  {'related_event': str(related_event), 'sim': sim[(event, related_event)]} for related_event in related_events]
	}


# print('推荐相关事件')
# for event in personManager.getPerson('3767').event_array:
# 	t = threading.Thread(target=thread_func,args=(event, ))
# 	thread_array.append(t)
# 	t.start()
# 	time.sleep(0.001)

# for t in thread_array:
# 	t.join()

def getTriggerId(event, person):
	for role in event.roles:
		if role['person'] == person:
			return event.trigger.name + ' ' + role['role']
	return None



def inferUncertainty(id):
	person = personManager.getPerson(id)
	year2events = person.getYear2event()
	events_with_infer = {}
	for year in year2events:
		events =year2events[year]
		
		# print(triggers)

		
		events_with_infer[year] = {
			'events': [str(event)  for event in events],
		}
		infer = set()

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
			triggers = [getTriggerId(event, person)  for event in events]
			most_similar = all2vec.trigger_model.most_similar(positive=triggers, topn=30)
			count = 0
			for sim_trigger, sim in most_similar:
				for event in person.event_array:
					if count>20:
						continue
					count += 1
					time_range = event.time_range
					if year<=time_range[1] and year>=time_range[0] and getTriggerId(event, person)==sim_trigger and time_range[1]!=time_range[0]:
						infer.add(event)

		infer = list(infer)
		events_with_infer[year]['infer'] = [str(event)  for event in infer]
	return events_with_infer

# id = '3767'
# open('scSystemServer/data_model/temp_data/infer{}.json'.format(id), 'w', encoding='utf-8').write(json.dumps(inferUncertainty(id), ensure_ascii = False, indent=4))

# id = '1762'
# open('./temp_data/infer{}.json'.format(id), 'w', encoding='utf-8').write(json.dumps(inferUncertainty(id), ensure_ascii = False, indent=4))

# id = '1097'
# open('./temp_data/infer{}.json'.format(id), 'w', encoding='utf-8').write(json.dumps(inferUncertainty(id), ensure_ascii = False, indent=4))


def test_inferUncertainty_module():
	infer_num = 0
	error_year = 0
	event2error = {}
	try_num = 0
	# 测试一下上面的正确率
	def test_inferUncertainty(person):
		# 分出训练集和测试集
		temp_event_array = person.event_array
		event_array = [event for event in person.event_array if event.time_range[0]==event.time_range[1]]
		random.shuffle(event_array)
		if len(event_array)<8:
			return

		middle = math.floor( len(event_array)*0.8 )
		train_array = event_array[0:middle]
		test_array =  event_array[middle+1:]
		person.event_array = train_array

		global infer_num
		global error_year
		global event2error
		global try_num


		year2events = person.getYear2event()

		# 还没有分测试集和验证集
		events_with_infer = {}
		for year in year2events:
			events =year2events[year]
			
			events_with_infer[year] = {
				'events': [str(event)  for event in events],
			}
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
				triggers = [getTriggerId(event, person)  for event in events]
				most_similar = all2vec.trigger_model.most_similar(positive=triggers, topn=30)
				# print('t',triggers)
				# print('m',most_similar)
				for sim_trigger, sim in most_similar:
					for event in test_array:
						time_range = event.time_range
						infer_num += 1

						if event in event2error:
							event2error[event]['num'] += 1
							event2error[event]['error_year'] += abs(time_range[0]-year) * sim
						else:
							event2error[event] = {
								'num': 1,
								'error_year': abs(time_range[0]-year) * sim,
								'correct_num': 0
							}

						if time_range[0]==year:
							try_num += event2error[event]['num']
							event2error[event]['success'] = True
							event2error[event]['correct_num'] += 1

		person.event_array = temp_event_array


	# for time in range(1,1):
	# print(str(time))
	for person in personManager.person_array:
		test_inferUncertainty(person)

	correct_num = 0
	correct_freq = 0
	mean_error_year = 0
	total_error = 0
	correct_test_num = 0
	error_num = 0
	for event in event2error:
		error = event2error[event]
		# if 'success' not in error:
		if 'success' in error:
			correct_test_num += error['num']
			correct_num += 1
			correct_freq += error['correct_num']
		else:
			total_error += error['error_year']
			error_num += error['num']
	mean_error_year = total_error/infer_num
	mean_correct_test_num = correct_test_num/correct_num

	print(infer_num, correct_num, len(event2error.keys()) ,mean_error_year, correct_test_num/correct_freq, correct_freq)

# id = '3767'
# sushi = personManager.getPerson(id)
# year2events = sushi.temp_getYear2event()
# open('./temp_data/year2events_{}.json'.format(id), 'w', encoding='utf-8').write(json.dumps({year:[str(event)  for event in year2events[year]] for year in year2events}, ensure_ascii = False, indent=4))

# id = '1762'
# sushi = personManager.getPerson(id)
# year2events = sushi.temp_getYear2event()
# open('./temp_data/year2events_{}.json'.format(id), 'w', encoding='utf-8').write(json.dumps({year:[str(event)  for event in year2events[year]] for year in year2events}, ensure_ascii = False, indent=4))

# id = '1097'
# sushi = personManager.getPerson(id)
# year2events = sushi.temp_getYear2event()
# open('./temp_data/year2events_{}.json'.format(id), 'w', encoding='utf-8').write(json.dumps({year:[str(event)  for event in year2events[year]] for year in year2events}, ensure_ascii = False, indent=4))


# song_people = [person for person in personManager.person_array if person.dy==15 and len(person.event_array)>10]
# open('./temp_data/all_persons.json'.format(id), 'w', encoding='utf-8').write(json.dumps({'data': [ person.toDict() for person in song_people]}, ensure_ascii = False, indent=4))

