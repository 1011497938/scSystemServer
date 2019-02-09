import sqlite3
import re
# from opencc import OpenCC 
import json
from .db_manager import dbManager as db
from .neo4j_manager import graph
from  .person_manager import personManager
from .addr_manager import addrManager
from .time_manager import timeManager
from .relation2type import getRelTypes
import threading
import time

class EventManager(object):
	"""docstring for Event_Extract"""
	def __init__(self):
		self.event_array = []
		self.id2event = {}
		self.event_id_set = set()
		self.event_type_index = {}

		self.is_all = False
		self.is_sort = False
		# self.trigger_manager =EventTriggerManager()

	def getAll(self, get_times = 30):
		if not self.is_all:	
			threading_array = []
			has1 = has2 = has3 = has4 = True
			threading_array = []
			for times in range(0,get_times):
				t1= threading.Thread(target=self.loadRelationEvents,args=(10000,10000*times, None))
				# t2= threading.Thread(target=self.loadPostOfficeEvents,args=(10000,10000*times, None))
				t3= threading.Thread(target=self.loadTextEvents,args=(10000,10000*times, None))
				# t4= threading.Thread(target=self.loadEntryEvents,args=(10000,10000*times, None))
				t5= threading.Thread(target=self.loadAddrEvents,args=(10000,10000*times, None))

				t1.start()
				time.sleep(0.1)
				threading_array.append(t1)
				# t2.start()
				# time.sleep(0.1)
				# threading_array.append(t2)
				t3.start()
				time.sleep(0.1)
				threading_array.append(t3)
				# t4.start()
				# time.sleep(1)
				# threading_array.append(t4)
				t5.start()
				time.sleep(0.1)
				threading_array.append(t5)

				t1.join()
				t3.join()
				t5.join()
				# if has1:
				# 	has1 = eventManager.loadRelationEvents(LIMIT = 10000,SKIP = 10000*times)   #person_id=3767 苏轼
				# if has2:
				# 	has2 = eventManager.loadPostOfficeEvents(LIMIT = 10000,SKIP = 10000*times)
				# if has3:
				# 	has3 = eventManager.loadTextEvents(LIMIT = 10000,SKIP = 10000*times)
				# if has4:
				# 	has4 = eventManager.loadEntryEvents(LIMIT = 10000,SKIP = 10000*times)
				# if not has1  and not has2 and not has3 and not has4:
				# 	break

			# for t in threading_array:
			# 	t.join()

		# 之后不需要再重新爬取了
		if True:  # get_times == 100:
			self.is_all = True
			for person in personManager.person_array:
				person.has_all_events = True


	def sortByYear(self):
		event_array = sorted(self.event_array, key=lambda event: float(event.time_range[0])+float(event.sequence)*0.1) 
		return event_array

	# 加载关系事件
	def loadRelationEvents(self, LIMIT = 1000000,SKIP = 0, person_id = None):
		print('开始加载关系事件')
		# 使用neo4j提取
		# 获取事件
		if person_id is None:
			query = 'MATCH (person:Biog_main)--(n:Assoc_data) RETURN n, id(n) SKIP {} LIMIT {} '.format(str(SKIP), str(LIMIT))
		else:
			query = 'MATCH (person:Biog_main{{c_personid:"{}"}})--(n:Assoc_data) RETURN n, id(n) SKIP {} LIMIT {} '.format(str(person_id),str(SKIP), str(LIMIT))
		results = graph.run(query).data()
		csv_data = []
		for node_data in results:
			node_id = node_data['id(n)']
			node_data = node_data['n']
			# node_object_id = node_data['OBJECT_ID']
			# 添加时间
			# print(node_data['c_assoc_year']==None)
			event = self.createEvents(node_id)
			event.type = '关系事件'


			if 'c_sequence' in node_data.keys():
				sequence = node_data['c_sequence']
				if sequence != 'None' and sequence is not None:
					event.sequence = int(sequence)

			c_assoc_year = node_data['c_assoc_year']
			if c_assoc_year is not None and c_assoc_year!=0 and c_assoc_year!='0' and c_assoc_year!='None':
				c_assoc_year = int(c_assoc_year)
				range_field = graph.getTableRange('assoc_data', 'c_assoc_year')
				year_range = node_data[range_field]
				event.addTimeAndRange(c_assoc_year, year_range)

			# if 'c_assoc_nh_code' in node_data.keys():
			# 	nh_code = node_data['c_assoc_nh_code']
			# 	if nh_code != 'None' and nh_code is not None:
			# 		nh_range = timeManager.getNianHaoRange(nh_code)
			# 		event.addTimeAndRange(nh_range[0], '之后')
			# 		event.addTimeAndRange(nh_range[1], '之前')

			row = [node_id]
			csv_data.append(row)
		# print(csv_data)

		if len(csv_data)==0:
			return False

		id_list_str = ','.join([str(row[0]) for row in csv_data])
		# 获得角色
		# START n=node(282787) MATCH (person:Biog_main)-[r]-(n) RETURN id(person), r, n, person
		results = graph.run('START n=node({}) MATCH (person:Biog_main)-[r]-(n) RETURN r, person, id(n)'.format(id_list_str))
		results = results.data()
		for result in results:
			person =  personManager.createPerson(result['person'])
			event_id = result['id(n)']
			role =  result['r']['RELATION_TYPE']
			if role =='关系':
				role = '主角'
			self.createEvents(event_id).addPerson(person, role)
		print('加载关系事件角色')


		# 加载地点
		results = graph.run('START n=node({}) MATCH (addr:Addr_codes)-[r]-(n) RETURN addr.c_addr_id as addr_id, id(n)'.format(id_list_str))
		results = results.data()
		for result in results:
			addr_id =  result['addr_id']
			event_id = result['id(n)']
			self.createEvents(event_id).setAddr(addrManager.getAddr(addr_id))
		print('加载关系数据地址')

		# 加载触发词
		results = graph.run('START n=node({}) MATCH (assoc:Assoc_codes)<-[r]-(n) RETURN assoc.c_assoc_desc_chn, id(n)'.format(id_list_str))
		results = results.data()
		for result in results:
			trigger_name =  result['assoc.c_assoc_desc_chn']
			event_id = result['id(n)']
			self.createEvents(event_id).setTrigger(trigger_name)
			# print(self.createEvents(event_id).trigger)
		print('加载事件触发词')

		# graph.runWithCsv(csv_data, 'START n=node(toInt(row[0])) MATCH (person:Biog_main)-[r]-(n) RETURN id(person), r, person, row[0]')
		# print()
		if len(csv_data)<LIMIT:
			return False

		return True

	def loadAddrEvents(self, LIMIT = 1000000,SKIP = 0, person_id = None ):
		print('开始加载迁移事件')
		if person_id is None:
			query = 'MATCH (person:Biog_main)--(event:Biog_addr_data) RETURN person, event, id(event) SKIP {} LIMIT {} '.format(str(SKIP), str(LIMIT))
		else:
			query = 'MATCH (person:Biog_main{{c_personid:"{}"}})-->(event:Biog_addr_data) RETURN person, event, id(event) SKIP {} LIMIT {} '.format(str(person_id),str(SKIP), str(LIMIT))

		# print(query)
		results = graph.run(query).data()
		id_list = []
		for node_data in results:
			# print(node_data)
			node_id = node_data['id(event)']
			person = node_data['person']
			node_data = node_data['event']
			
			event = self.createEvents(node_id)
			event.type = '前往'

			event.addPerson(personManager.createPerson(person), '主角')
			event.setTrigger('前往')
			event.type = '前往'
			event.detail = '前往某地'

			field = 'c_firstyear'
			year = node_data[field]
			if year is not None and year!=0 and year!='0' and year!='None':
				year = int(year)
				range_field = graph.getTableRange('Biog_addr_data', field)
				year_range = node_data[range_field]
				event.addTimeAndRange(year, year_range)


			event = self.createEvents('离开'+str(node_id))
			event.addPerson(personManager.createPerson(person), '主角')
			event.setTrigger('离开')
			event.type = '离开'
			event.detail = '离开某地'

			field = 'c_lastyear'
			if field in node_data.keys():
				year = node_data[field]
				# print(year)
				if year is not None and year!=0 and year!='0' and year!='None':
					year = int(year)
					range_field = graph.getTableRange('Biog_addr_data', field)
					year_range = node_data[range_field]
					# print(year)
					event.addTimeAndRange(year, year_range)

			id_list.append(str(node_id))


		if len(id_list)==0:
			return False
		# print(id_list)
		id_list_str = ','.join(id_list)

		# 加载地点
		results = graph.run('START n=node({}) MATCH (addr:Addr_codes)--(n) RETURN addr.c_addr_id as addr_id, id(n)'.format(id_list_str))
		results = results.data()
		# print(results)
		for result in results:
			addr_id =  result['addr_id']
			event_id = str(result['id(n)'])
			# print(addr_id)

			event = self.createEvents(event_id)
			addr = addrManager.getAddr(addr_id)
			event.setAddr(addr)
			event.detail = '前往'+ str(addr.name)


			event = self.createEvents('离开'+event_id)
			addr = addrManager.getAddr(addr_id)
			event.setAddr(addr)
			event.detail = '离开'+ str(addr.name)

		# 加载原因
		print('加载迁移数据地址')

		results = graph.run('START n=node({}) MATCH (addr:Biog_addr_codes)--(n) RETURN addr.c_addr_desc_chn as desc, id(n)'.format(id_list_str))
		results = results.data()
		# print(results)
		for result in results:
			desc =  str(result['desc'])
			event_id = str(result['id(n)'])
			# print(addr_id)

			event = self.createEvents(event_id)
			event.setTrigger(desc)
			event.detail = event.detail + '由于' + desc
		print('加载迁移原因')

		if len(id_list)<LIMIT:
			return False
		return True
		# 加载原因


	# 加载官职变化事件（还有一些其他信息没有添加，比如说靠亲戚之类的）
	def loadPostOfficeEvents(self, LIMIT = 1000000,SKIP = 0, person_id = None):
		print('开始加载仕途事件')
		# 使用neo4j提取
		# 使用Posting_Data可能有问题，有些信息未连起来
		# --(n3:Posted_to_addr_data)
		if person_id is None:
			query = 'MATCH (person:Biog_main)--(n1:Posted_to_office_data)--(n2:Posting_data) RETURN person,n1,n2,id(n1),id(n2) SKIP {} LIMIT {} '.format(str(SKIP), str(LIMIT))
		else:
			query = 'MATCH (person:Biog_main{{ c_personid:"{}" }})--(n1:Posted_to_office_data)--(n2:Posting_data) RETURN person,n1,n2,id(n1),id(n2) SKIP {} LIMIT {} '.format(str(person_id) ,str(SKIP), str(LIMIT))

		results = graph.run(query).data()
		id_list1 = []
		id_list2 = []
		id_list3 = []
		id2id = {}
		for node_data in results:
			node_id1 = str(node_data['id(n1)'])
			node_id2 = str(node_data['id(n2)'])
			# node_id3 = str(node_data['id(n3)'])

			node_data1 = node_data['n1']
			node_data2 = node_data['n2']
			node_data3 = node_data['n3']

			event1 = self.createEvents('担任'+node_id1)  #担任
			event2 = self.createEvents('卸任'+node_id1)  #卸任
			event1.type = '官职事件'
			event2.type = '官职事件'


			field = 'c_firstyear'
			year = node_data1[field]
			if year is not None and year!=0 and year!='0' and year!='None':
				year = int(year)
				range_field = graph.getTableRange('posted_to_office_data', field)
				year_range = node_data1[range_field]
				event1.addTimeAndRange(year, year_range)


			field = 'c_lastyear'
			event2.addTimeAndRange(event1.time_range[0], '之后')
			year = node_data1[field]
			if year is not None and year!=0 and year!='0' and year!='None':
				year = int(year)
				range_field = graph.getTableRange('posted_to_office_data', field)
				year_range = node_data1[range_field]
				event2.addTimeAndRange(year, year_range)

			if 'c_sequence'in node_data1.keys():
				sequence = node_data1['c_sequence']
				if sequence != 'None' and sequence is not None:
					event1.sequence = int(sequence)
					event2.sequence = int(sequence)

			id_list1.append(node_id1)
			id_list2.append(node_id2)
			# id_list3.append(node_id3)

			id2id[node_id1] = node_id1
			id2id[node_id2] = node_id1
			# id2id[node_id3] = node_id1

			person =  personManager.createPerson(node_data['person'])
			event1.addPerson(person, '主角')
			event2.addPerson(person, '主角')

			event1.setTrigger('担任')
			event2.setTrigger('卸任')

		if len(id_list1)==0:
			return False

		id_list_str1 = ','.join(id_list1)
		id_list_str2 = ','.join(id_list2)
		# id_list_str3 = ','.join(id_list3)
		# print(id_list_str3)

		# 加载地点
		results = graph.run('START n=node({}) MATCH (addr:Addr_codes)--(:Posted_to_addr_data)--(n) RETURN addr.c_addr_id as addr_id, id(n)'.format(id_list_str2))
		results = results.data()
		# print('START n=node({}) MATCH (addr:Addr_codes)-[r]-(n) RETURN addr.c_addr_id as addr_id, id(n)'.format(id_list_str3))
		# print(results)
		for result in results:
			addr_id =  result['addr_id']
			event_id = str(result['id(n)'])
			# print(addr_id)
			self.createEvents('担任'+id2id[event_id]).setAddr(addrManager.getAddr(addr_id))
			self.createEvents('卸任'+id2id[event_id]).setAddr(addrManager.getAddr(addr_id))
		print('加载仕途数据地址')

		# 加载职位
		results = graph.run('START n=node({}) MATCH (office:Office_codes)-[r]-(n) RETURN office, id(n)'.format(id_list_str1))
		results = results.data()
		# print('START n=node({}) MATCH (addr:Addr_codes)-[r]-(n) RETURN addr.c_addr_id as addr_id, id(n)'.format(id_list_str3))
		# print(results)
		for result in results:
			office_code =  result['office']
			event_id = str(result['id(n)'])
			event1 = self.createEvents('担任'+id2id[event_id])
			event2 = self.createEvents('卸任'+id2id[event_id])
			event1.detail = str(office_code['c_office_chn'])
			event2.detail = str(office_code['c_office_chn'])

			# self.createEvents('担任'+id2id[event_id]).setTrigger('担任'+str(office_code['c_office_chn']))
			# self.createEvents('卸任'+id2id[event_id]).setTrigger('卸任'+str(office_code['c_office_chn']))
		print('加载仕途官职')

		# 加载官职的授予方式
		results = graph.run('START n=node({}) MATCH (office:Appointment_type_codes)-[r]-(n) RETURN office, id(n)'.format(id_list_str1))
		results = results.data()
		# print('START n=node({}) MATCH (addr:Addr_codes)-[r]-(n) RETURN addr.c_addr_id as addr_id, id(n)'.format(id_list_str3))
		# print(results)
		for result in results:
			office_code =  result['office']['c_appt_type_desc_chn']
			event_id = str(result['id(n)'])
			self.createEvents('担任'+id2id[event_id]).detail += '授予方式' + str(office_code)
			# self.createEvents('担任'+id2id[event_id]).setTrigger('担任'+str(office_code['c_office_chn']))
			# self.createEvents('卸任'+id2id[event_id]).setTrigger('卸任'+str(office_code['c_office_chn']))
		print('加载仕途官职')
		if len(id_list1)<LIMIT:
			return False
		return True

	# 加载文学事件
	def loadTextEvents(self, LIMIT = 1000000,SKIP = 0, person_id = None):
		print('开始加载文学事件')
		if person_id is None:
			query = 'MATCH (person:Biog_main)--(event:Text_data)--(text:Text_codes) RETURN person,event,id(event),text SKIP {} LIMIT {} '.format(str(SKIP), str(LIMIT))
		else:
			query = 'MATCH (person:Biog_main{{c_personid:"{}"}})--(event:Text_data)--(text:Text_codes) RETURN person,event,id(event),text SKIP {} LIMIT {} '.format(str(person_id) ,str(SKIP), str(LIMIT))
		results = graph.run(query).data()
		id_list = []
		id2person = {}
		for node_data in results:
			event_id = str(node_data['id(event)'])

			person = node_data['person']
			event_node = node_data['event']
			text = node_data['text']   #也有时间，未用

			event = self.createEvents(event_id)
			event.type = '文学事件'
			field = 'c_year'
			year = event_node[field]
			if year is not None and year!=0 and year!='0' and year!='None':
				year = int(year)
				range_field = graph.getTableRange('text_data', field)
				year_range = event_node[range_field]
				event.addTimeAndRange(year, year_range)

			id_list.append(event_id)
			person =  personManager.createPerson(person)
			id2person[event_id] = person

			

		if len(id_list)==0:
			return False

		id_list_str = ','.join(id_list)
		# print(id_list_str)
		# 加载角色
		results = graph.run('START event=node({}) MATCH (role:Text_role_codes)--(event) RETURN role.c_role_desc_chn AS role, id(event)'.format(id_list_str))
		results = results.data()
		# print(results)
		for result in results:
			role =  result['role']
			event_id = str(result['id(event)'])
			self.createEvents(event_id).addPerson(person, role)
			event.setTrigger('文学作品'+role)
		print('加载文学事件角色')


		if len(id_list)<LIMIT:
			return False
		return True

	# 入仕事件(还有很多信息没存储)
	def loadEntryEvents(self, LIMIT = 1000000,SKIP = 0, person_id = None):
		print('开始加载入仕数据')
		if person_id is None:
			query = 'MATCH (person:Biog_main)-[:参与人]->(event:Entry_data) RETURN person,event,id(event) SKIP {} LIMIT {} '.format(str(SKIP), str(LIMIT))
		else:
			query = 'MATCH (person:Biog_main{{ c_personid:"{}" }})-[:参与人]->(event:Entry_data) RETURN person,event,id(event) SKIP {} LIMIT {} '.format(str(person_id),str(SKIP),str(LIMIT))
		
		results = graph.run(query).data()
		id_list = []
		for node_data in results:
			event_id = str(node_data['id(event)'])
			person = node_data['person']
			event_node = node_data['event']

			event = self.createEvents(event_id)
			event.type = '入仕事件'
			field = 'c_year'
			year = event_node[field]

			if year is not None and year!=0 and year!='0' and year!='None':
				year = int(year)
				range_field = graph.getTableRange('entry_data', field)
				year_range = event_node[range_field]
				event.addTimeAndRange(year, year_range)

			if 'c_sequence' in node_data.keys():
				sequence = node_data['c_sequence']
				if sequence != 'None' and sequence is not None:
					event.sequence = int(sequence)

			id_list.append(event_id)

			person =  personManager.createPerson(person)
			event.addPerson(person, '主角')

		if len(id_list)==0:
			return False

		id_list_str = ','.join(id_list)

		# 入仕法
		results = graph.run('START event=node({}) MATCH (method:Entry_codes)--(event) RETURN method.c_entry_desc_chn AS method, id(event)'.format(id_list_str))
		results = results.data()
		# print(results)
		for result in results:
			method =  result['method']
			event_id = str(result['id(event)'])
			self.createEvents(event_id).setTrigger('入仕')
			self.createEvents(event_id).detail = str(method)
			# self.createEvents(event_id).setTrigger(str(method))
		print('加载入仕方式')

		# 相关机构

		if len(id_list)<LIMIT:
			return False
		# 分数
		return True


	def createEvents(self, node_id):
		node_id = str(node_id)
		id2event = self.id2event
		if node_id in self.event_id_set:
			return id2event[node_id]
		else:	
			# if node_id in self.id2event.keys():
			# 	print('ERROR!!!')
			new_event = Event(node_id)
			id2event[node_id] = new_event
			self.event_array.append(new_event)
			self.event_id_set.add(node_id)
			return new_event

class Event(object):
	def __init__(self, event_id):
		self.id = event_id
		self.time_range = [-9999, 9999]
		self.type = None  #类型,没啥用，以后以trigger为主
		self.trigger = None  #触发词
		self.is_state = False
		self.roles = []  #{person: , role:}   
		self.addrs = []  #将原先的单一地址改为了多地址
		self.sequence = 10
		self.related_nodes = {}
		self.setTrigger('未知')
		self.detail = ''

	def setAddr(self, new_addr):
		if new_addr not in self.addrs:
			self.addrs.append(new_addr)

		# if self.addr is None or self.addr.isParent(addr):
		# 	self.addr = addr
		# 	# print(str(addr), addr.time_range)
		# 	# self.addTimeAndRange(addr.time_range[0], '之前')
		# 	# self.addTimeAndRange(addr.time_range[1], '之后')
		# else:
		# 	# 需要判断大小然后操作
		# 	print('重复给事件添加地址')
		# 	pass

	def addRelatedNodes(self, node):
		self.related_tables.add(node)

	def addTimeAndRange(self, year, range_code):
		if year == -1:
			return

		# print(year)
		if self.time_range[0]==self.time_range[1]:
			return
		if year is None:
			# 这里似乎有问题
			# print('year is None')
			return
		# print('不是None')

		up = 9999
		down = -9999
		# print(year, range_code)
		range_code = graph.getRange(range_code)
		if range_code=='之前':
			up = year
		elif range_code=='之后':
			down = year
		elif range_code=='约':
			up = year+1
			down = year-1
		elif range_code=='960-1082':
			up = 1082
			down = 960
		elif range_code=='1082-1279':
			up = 1279
			down = 1082
		elif range_code=='之间':
			up = year
			down = year
		elif range_code is None or range_code == 'None': 
			up = year
			down = year
		else:
			print('addTimeAndRange出错', year, range_code)
			return 

		time_range=[self.time_range[0], self.time_range[1]]
		# print(time_range, down)
		if up<time_range[1]:
			time_range[1]=up
		if down>time_range[0]:
			time_range[0]=down
		if time_range[0]<=time_range[1]:
			self.time_range = time_range
		# else:			
		# 	print('Error time_range:{}'.format(str(time_range)))

	
	def getSource(self, type):
		return

	def addPerson(self, person, role):
		# print(person, role)
		# 角色应该能帮助缩小时间范围,可以添加
		new_role = {'person':person, 'role':role}
		if new_role not in self.roles:
			self.roles.append(new_role)
			person.bind_event(self)

	def setTrigger(self, trigger_name):
		trigger = triggerManager.createTrigger(trigger_name)
		self.trigger = trigger

	def __str__(self):
		string = '[(事件) id:{}, 时间:{}, 地点:{}, 类型:{}, 触发词:{}, 角色: {}]'.format(
			str(self.id), str(self.time_range),
			'[' + ','.join([str(addr) for addr in self.addrs]) + ']', 
			str(self.type), str(self.trigger), 
			str(','.join([ '【{}/{}】'.format(elm['person'], elm['role']) for elm in self.roles])))
		return string

	def __hash__(self):
		return hash(str(self.id + '事件'))

	def toDict(self):
		trigger = None
		addrs = []
		if self.trigger is not None:
			trigger = self.trigger
		else:
			trigger = triggerManager.createTrigger('未知')
		if self.addrs is not None:
			addrs = self.addrs

		return {
			'id': self.id,
			'time_range': self.time_range,
			'trigger': trigger.id,
			'addrs': [addr.id for addr in addrs],
			'roles': [{'person': elm['person'].id, 'role': elm['role']}  for elm in self.roles],
			'detail': self.detail,
			'sequence' : self.sequence
			# 'is_state': self.is_state
		}




# 管理触发词的分类计算
class EventTriggerManager(object):
	"""docstring for EventTriggerManager"""
	def __init__(self):
		self.name2trigger = {}
		# self.triggers = []   #Trigger
		# self.relationship_cat = self._getRelationshipCat()   #暂时没有用到
		self.trigger_set = set()

		# self.now_id = 0

		self.trigger2type_score = json.loads(open('scSystemServer/data_model/data/relation_code2type.json', 'r', encoding='utf-8').read())
		
		self.trigger2type_score['反对攻讦'] = {
			'score': 8,
			'type': '政治对抗',
			'parent_type': '政治'
		}

	def getTriggerType(self, trigger_name):
		if trigger_name in self.name2trigger.keys():
			return self.name2trigger[trigger_name].type
		else:
			return None

	def set_trigger_type(self, trigger, type = None):
		if type is not None:
			trigger.type = type
		elif trigger.name in self.trigger2type_score:
				item = self.trigger2type_score[trigger.name ]
				trigger.parent_type = item['parent_type']
				trigger.type = item['type']
				trigger.score = item['score']
		# else:
		# 	print(str(trigger.name) + '不存在评分和类型')

			# # 进行一系列计算 
			# if trigger.name in self.relationship_cat.keys():
			# 	trigger.type = self.relationship_cat[trigger.name]
			# else:
			# 	trigger.type = '其他'
				
	def createTrigger(self, trigger_name):
		if trigger_name in self.trigger_set:
			return self.name2trigger[trigger_name]
		else:
			new_trigger = Trigger(trigger_name)
			self.name2trigger[trigger_name] = new_trigger
			new_trigger.id = trigger_name + '_trigger'
			# self.now_id += 1
			self.trigger_set.add(trigger_name)
			self.set_trigger_type(new_trigger)
			return new_trigger

	def toDict(self):
		return {trigger_id: self.name2trigger[trigger_id].toDict() for trigger_id in self.name2trigger}

class Trigger(object):
	"""docstring for Trigger"""
	def __init__(self, name):
		self.name = name
		self.type = '未分类'
		self.parent_type = '未分类'
		self.score = 0
		self.id = hash(self)

	def __str__(self):
		return '[(触发词) 触发词:{}, 分类:{}]'.format(str(self.name), str(self.type))

	def __hash__(self):
		return hash(str(self))
	
	def toDict(self):
		return {
			'id': self.id,
			'name': self.name,
			'type': self.type,
			'parent_type': self.parent_type,
			'score': self.score
		}

triggerManager = EventTriggerManager()
eventManager = EventManager()

if __name__ == '__main__':
	print('测试事件模块')
	# event_extractor = EventExtractor()


