from django.http import HttpResponse
from .data_model.event_manager import eventManager, triggerManager
from .data_model.person_manager import personManager
from .data_model.addr_manager import addrManager
from .data_model.neo4j_manager import graph
from py2neo import Graph,Node,Relationship,cypher
from .data_model.time_manager import timeManager
# from relation2type import getRelTypes
from .data_model.page_rank import pageRank,PersonGraph
from .data_model.word2vec import All2vec
from .data_model.common_function import dist_dif

from scipy.spatial.distance import euclidean
from fastdtw import fastdtw

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

# 初始化
personManager.registEventManager(eventManager)
eventManager.getAll()
all2vec = All2vec(personManager, addrManager, eventManager)

eventManager.registAll2vec(all2vec)

person_graph = PersonGraph(eventManager)
person_rank = pageRank(eventManager.event_array)

eventManager.person_graph = person_graph
personManager.all2vec = all2vec
addrManager.all2vec = all2vec

# year2events =  eventManager.getYear2Events()
# year2pagerank = {year:pageRank(year2events[year])  for year in year2events}
# print(year2pagerank)
# open('scSystemServer/data_model/temp_data/year2pagerank.json', 'w', encoding='utf-8').write(json.dumps(year2pagerank, indent=3, ensure_ascii = False))


trigger_name_imp = eventManager.calculateImporatnce1()
# 有一些数据会在最初全部加载(对应的vec还没有加),还可以再优化的
# 宋代人物
song_people = {person.id: person.toDict() for person in personManager.person_array if person.isSong()}
#宋代地点
song_addrs = addrManager.toSongDict()
#所有触发词 
triggers = triggerManager.toDict()
# 转载
init_data = json.dumps({
    'people': song_people, 
    'addrs': song_addrs, 
    'triggers': triggers, 
    'trigger_imp': trigger_name_imp,
    'trigger2vec': { key: all2vec.trigger2vec[key].tolist() for key in all2vec.trigger2vec},
    'info': '初始化数据'
    })
open('scSystemServer/data_model/temp_data/预加载数据/data', 'w', encoding='utf-8').write(init_data)

# fs_vec = open('scSystemServer/data_model/temp_data/事件vec', 'w', encoding='utf-8')
# fs_meta = open('scSystemServer/data_model/temp_data/事件meta', 'w', encoding='utf-8')
# for event in personManager.getPerson('3767').getRelatedEvents(limit_depth=2):
#     if event.isCertain(): # and event.time_range[0]<1100 and event.time_range[0]>1060:
#         vec = list(event.toVec())
#         # print(len(vec))
#         fs_vec.write( '\t'.join([str(item) for item in vec]) + '\n' )
#         fs_meta.write( str(event) + '\n')
# fs_vec.close()
# fs_meta.close()

print('共加载', len(eventManager.event_array), '事件')

def init(request):
    if init is not None:
        return  HttpResponse(init_data)
    else:
        data = {'info': 'server is loading, please wait'}
        return HttpResponse(json.dumps(data))

def events2dict(event_array):
    events = set()
    addrs = set()
    people = set()
    triggers = set()
    
    for event in event_array:
        events.add(event)
        triggers.add(event.trigger)
        for addr in event.addrs:
            addrs.add(addr)
        for role in event.roles:
            people.add(role['person'])
    
    #trigger 预加载已经加载好了
    results = {
        'events': { item.id: item.toDict()  for item in events},
        'addrs': { item.id: item.toDict()  for item in addrs if not item.isSong()},
        'people': { item.id: item.toDict()  for item in people  if not item.isSong()},
        # 'triggers': { item.id: item.toDict()  for item in triggers},   
    }

    return results

# 获得一个人的所有事件
def getPersonEvents(request):
    person_id = request.GET.get('person_id')
    print('获取' + person_id + '事件')
    events = personManager.getPerson(person_id).event_array
    print(person_id + '事件数共有' + str(len(events)))
    return HttpResponse(json.dumps(events2dict(events)))

# 推断一些可能事件的可能位置
def inferPersonsEvent(request):
    person_id = request.GET.get('person_id')
    print('推测' + person_id + '事件')
    infer, events = personManager.getPerson(person_id).inferUncertainty(all2vec)

    infer_data = {}
    for year in infer:
        for event_id in infer[year]:
            if event_id not in infer_data:
                infer_data[event_id] = {}
            infer_data[event_id][year] =  infer[year][event_id]['sim']
    extra_data = events2dict(events)
    print('推测结束')
    return HttpResponse(json.dumps({ 'data':extra_data, 'infer': infer_data, 'info': '推测数据'}))

# 如果是两个人的关系
# 如果是有时间的
# 如果是有地点的
def getRelatedEvents(request):
    event_id = request.GET.get('event_id')
    if event_id in eventManager.event_id_set:
        event = eventManager.id2event[event_id]
    else:
        print('没有找到', event_id, '对应的事件')
        return HttpResponse(json.dumps({'info': '没有找到事件'}))

    related_events = []
    for role in event.roles:
        this_person = role['person']
        trigger_id = event.trigger.name + ' ' + role['role']
        if trigger_id in all2vec.trigger2vec:
            most_similar = all2vec.trigger_model.most_similar(trigger_id, topn=50)
            most_similar = [item[0] for item in most_similar]

            this_person_events = this_person.getAllEvents() 
            for this_event in this_person_events:
                for role in this_event.roles:
                    if this_person == role['person']:
                        trigger_id = this_event.trigger.name + ' ' + role['role']
                        if trigger_id in most_similar:
                            related_events.append(this_event)

    #看情况判断要不要加
    related_events = [this_event for this_event in related_events if (len(this_event.addrs)!=0 or this_event.time_range[0]!=-9999 or this_event.time_range[1]!=9999)]
    related_events = list(set(related_events))
    sim = {}
    for related_event in related_events:
        sim[(event, related_event)] = eventManager.caclute_sim(event, related_event)

    related_events = sorted(related_events, key=lambda related_event: sim[(event, related_event)])
    if len(related_events)>40:
        related_events = related_events[0:40]

    dif = {related_event.id: sim[(event, related_event)]  for event, related_event in sim}
    related_events.append(event)
    data = events2dict(related_events)
    return HttpResponse(json.dumps({'data':data, 'sim': dif, 'center_event':event_id, 'info': '找到相关事件'}))

def getAllRelatedEvents(request):
    event_id = request.GET.get('event_id')
    depth = int(request.GET.get('depth'))
    trigger_num = int(request.GET.get('trigger_num'))
    max_event_num = int(request.GET.get('event_num'))

    if event_id in eventManager.event_id_set:
        event = eventManager.id2event[event_id]
    else:
        print('没有找到', event_id, '对应的事件')
        return HttpResponse(json.dumps({'info': '没有找到事件'}))
    events = []
    for role in event.roles:
        person = role['person']
        events += person.getRelatedEvents(limit_depth=depth)
    events = list(set(events))

    # 只留下相关类型的
    related_triggers = []
    for role in event.roles:
        # this_person = role['person']
        trigger_id = event.trigger.name + ' ' + role['role']
        if trigger_id in all2vec.trigger2vec:
            most_similar = all2vec.trigger_model.most_similar(trigger_id, topn=trigger_num)
            most_similar = [item[0] for item in most_similar]
            related_triggers += most_similar
    related_triggers = list(set([trigger.split(' ')[0] for trigger in related_triggers]))
    print(related_triggers)
    events = [event for event in events if event.trigger.name in related_triggers]

    sim = {}
    for related_event in events:
        sim[related_event] = eventManager.caclute_sim(event, related_event)
    events = sorted(events, key=lambda related_event: sim[related_event])
    if len(events)>max_event_num:
        events = events[0:max_event_num]
    dif = {related_event.id: sim[related_event]  for related_event in sim}
    data = events2dict(events)

    return HttpResponse(json.dumps({'data':data, 'dif': dif, 'event_id': event_id, 'info': '找到事件的所有相关事件'}))

def getRelatedPeopleEvents(request):
    person_id = request.GET.get('person_id')
    depth = int(request.GET.get('depth'))
    person = personManager.getPerson(person_id)
    events = person.getRelatedEvents(limit_depth=depth)
    data = events2dict(events)
    return HttpResponse(json.dumps({'data':data, 'person_id': person_id, 'person_name': person.name, 'info': '找到所有与此人有关的事件'}))

# 获得人物的分数，只有一种算法，有问题，
def getPersonScore(request):
    person_id = request.GET.get('person_id')
    person = personManager.getPerson(person_id)
    year2event = person.getYear2event()
    year2score = {}
    for year in year2event:
        events = year2event[year]
        year_score = 0
        for event in events:
            year_score += event.getScore(person)
        year2score[year] = year_score/len(events)*math.log(len(events))
    return HttpResponse(json.dumps({'score':year2score, 'info': '找到相关事件'}))

def getSimLife(request):
    person_id = request.GET.get('person_id')
    person = personManager.getPerson(person_id)
    person_score_array = person.getScoreArray(Align=False)
    # print(person_score_array)

    sim_array = []
    # 生成相似矩阵
    for sim_person in personManager.person_array:
        if sim_person == person:
            continue
        sim_person_scores = sim_person.getScoreArray(Align=False)
        if len(sim_person_scores)>5:    
            # print(sim_person_scores)
            distance, path = fastdtw(person_score_array, sim_person_scores, dist=euclidean)
            sim_array.append({
                'dist': distance,
                'person': sim_person.toDict(),
                'socres': sim_person_scores.tolist()
            })
    sim_array = sorted(sim_array, key=lambda elm: elm['dist'])[:40]
    return HttpResponse(json.dumps({'data':sim_array , 'info': '查找相似生涯'}))

if __name__ == '__main__':
    print('测试')
    # event_extractor = EventExtractor()


# 该如何发现人生中的重要事件呢(现在是通过trigger_imp)