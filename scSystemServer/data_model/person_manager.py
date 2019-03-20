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

        print('初始化人物')
        self.event2vec = None
        self.song_people = set()  #整理所有的宋朝人物

    def loadExtraData(self):
        rows = db.runSelect('SELECT c_personid,c_alt_name,c_alt_name_chn from altname_data')
        for row in rows:
            person = self.getPerson(row[0])
            if person is not None:
                person.alt_name.append(row[2])
                person.alt_name_en.append(row[1])
        
        rows = db.runSelect('SELECT c_personid,c_status_code from status_data')
        for row in rows:
            person = self.getPerson(row[0])
            if person is not None:
                person.status.append(row[1])

    def selfDestory(self):
        for person in self.person_array:
            person.selfDestory()
        self.id2person = None  #c_personid
        self.id_set = None
        self.person_array = None
        self.event_manager = None
        self.all2vec = None
        self.song_people = None

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

        def allIsSong(event):
            main_people = event.getPeople()
            for person in main_people:
                if not person.isSong():
                    return False
            return True

        # events = []
        # people = self.song_people
        # for person in self.song_people:
        #     person.event_array = [event  for event in person.event_array if allIsSong(event)]
        #     events += person.event_array
        # events = list(set(events))
        # self.event_manager.event_array = events
        # self.id2event = {event.id:event  for event in events}
        # self.event_id_set = set([event.id  for event in events])

        # self.id2person = {person.id:person  for person in people}  #c_personid
        # self.id_set = set([person.id for person in people])
        # self.person_array = people

    def createPerson(self,bio_main_node):
        new_id = 'person_' + bio_main_node['c_personid']
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
        if 'person_' not in str(person_id):
            person_id = 'person_' + str(person_id)
        if person_id in self.id_set:
            return self.id2person[person_id]
        # else:
        #     print(person_id, '没有找到，到数据库中查找')
            # print('run')
            # data = graph.run('MATCH (n:Biog_main{{c_personid:"{}"}}) RETURN n'.format(str(person_id))).data()
            # if len(data)!=0:
            #     # print(data[0])
            #     return self.createPerson(data[0]['n'])
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
        self.id = 'person_' + bio_main_node['c_personid']
        self.name = bio_main_node['c_name_chn']

        self.en_name = bio_main_node['c_name']

        self.birth_year = bio_main_node['c_birthyear']
        self.death_year = bio_main_node['c_deathyear']

        self.event_array = []  #所有出现的event

        self.female = bio_main_node['c_female']
        self.ethnicity = bio_main_node['c_ethnicity_code']

        self.household_status = bio_main_node['c_household_status_code']  #户籍
        self.alt_name = []
        self.alt_name_en = []

        self.status = []  #社会区分
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
                self.birth_year = int(birth_year)
            # 	self.range[0] = birth_year
            else:
                self.birth_year = -9999
            # 	self.birth_year = self.range[0]
            if death_year!=0 and death_year!='0' and death_year!='null' and death_year is not None:
                death_event = event_manager.createEvents('death'+ self.id)
                death_event.addTimeAndRange(int(death_year), '之间')
                death_event.addPerson(self, '主角')
                death_event.setTrigger('死亡')
                self.death_year = int(death_year)
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

        self.depth2related_events = {}
        self.depth2related_people = {}

        self.vec = []

        self.type = 'person'
    def getProbYearRange(self):
        max_year = -9999
        min_year = 9999
        for event in self.event_array:
            time_range = event.time_range
            for year in time_range:
                if year!=9999 and year!=-9999:
                    if year<min_year:
                        min_year = year
                    if year>max_year:
                        max_year = year
        if max_year==-9999:
            max_year = 9999
        if min_year==9999:
            min_year = -9999
        if self.birth_year != -9999:
            min_year = self.birth_year
        if self.death_year != 9999:
            max_year = self.death_year
        return [min_year, max_year]

        
    # 将各元素拼接生成一个数组,现在八成没用了
    def toVec(self):
        if(len(self.vec)==0):
            print('没有计算向量表达了', self)
        return list(self.vec)

    def selfDestory(self):
        self.id = None
        self.name = None
        self.birth_year = None
        self.death_year = None
        self.event_array = None
        self.index_year = None
        self.dy_nh_code = None          #在世始年
        self.index_year = None          #在世始年

        self.dy = None
        self.tribe = None

        self.page_rank = None
    
    def getRelatedPeople(self, limit_depth=2):
        events = self.getRelatedEvents(limit_depth=limit_depth-1)
        people = []
        for event in events:
            main_people = event.getPeople()
            people += main_people
        people = list(set(people))
        return people

    def getRelatedEvents(self, limit_depth = 3):
        if limit_depth in self.depth2related_events:
            return self.depth2related_events[limit_depth]

        # print('开始爬取所有相关人员事件', self, limit_depth)
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

        all_events = list(all_events)
        self.depth2related_events[limit_depth] = all_events
        return all_events


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
        # year2event = self.getYear2event()
        # years = year2event.keys()
        return {
            'id': self.id,
            'name': self.name,
            'birth_year': self.birth_year,
            'death_year': self.death_year,
            'certain_events_num': self.getCertaintyLength(),
            'events_num': len(self.event_array),
            'page_rank': self.page_rank,
            'dy': self.dy,
            'vec': self.vec,
            'en_name': self.en_name,

            'alt_name': self.alt_name,
            'alt_name_en': self.alt_name_en,
            'status': self.status,
            'household_status': self.household_status,
            'ethnicity': self.ethnicity,
            'female': self.female,
            # 'events': [event.id for event in self.event_array]
            'time_range': self.getProbYearRange()
        }

    def isSong(self):
        #  or self in personManager.song_people
        return (self.dy==15 or self.dy=='15')and len(self.event_array)>=50

    def getCertaintyLength(self):
        return len([ event for event in self.event_array if event.time_range[0]==event.time_range[1] and event.time_range[0]!=-9999])

personManager = PersonManager()

if __name__ == '__main__':
    print('测试人物模块')

