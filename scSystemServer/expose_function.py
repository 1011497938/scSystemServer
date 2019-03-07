from django.http import HttpResponse
from .data_model.event_manager import eventManager, triggerManager
from .data_model.person_manager import personManager
from .data_model.addr_manager import addrManager
from .data_model.neo4j_manager import graph
from py2neo import Graph,Node,Relationship,cypher
from .data_model.time_manager import timeManager
# from relation2type import getRelTypes
from .data_model.page_rank import pageRank  #,PersonGraph
# from .data_model.word2vec import All2vec
from .data_model.common_function import dist_dif
from .data_model.event2vec import Event2Vec

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

event2vec= Event2Vec(personManager, eventManager, addrManager, triggerManager)
event2vec.train(TOTAL_TIMES=100)
event2vec.load()
event2vec.load2Manager()
event2vec.saveToView()

# all2vec = All2vec(personManager, addrManager, eventManager)

# person_graph = PersonGraph(eventManager)
person_rank = pageRank(eventManager.event_array, personManager.person_array)
for person in personManager.person_array:
    person.page_rank = person_rank[person.id]


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
    'info': '初始化数据'
    })
# open('scSystemServer/data_model/temp_data/预加载数据/data', 'w', encoding='utf-8').write(init_data)


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

# 推断一些可能事件的可能时间  （还可以加上地点）
def inferPersonsEvent(request):
    person_id = request.GET.get('person_id')
    print('推测' + person_id + '事件')

    person = personManager.getPerson(person_id)
    events = person.getAllEvents()
    events = [event  for event in events if not event.isCertain()]

    event2prob_year = {}
    for event in events:
        prob_year = event2vec.getEventProbYear(event)
        print(event, prob_year)
        prob_year = {year: prob_year[year] for year in prob_year.keys() if prob_year[year]>0.45 }
        event2prob_year[event.id] = prob_year

    print('推测结束')
    return HttpResponse(json.dumps({ 'data':events2dict(events), 'infer': event2prob_year, 'info': '推测数据'}))

require2renponse = {}
def getRelatedEvents(request):
    event_id = request.GET.get('event_id')
    max_num = int(request.GET.get('event_num'))

    require_id = 'getAllRelatedEvents_{}_{}'.format(event_id, max_num)
    if require_id in require2renponse:
        print(require_id, '重复调用，直接使用纪录')
        return HttpResponse(json.dumps(require2renponse[require_id]))

    if event_id in eventManager.event_id_set:
        center_event = eventManager.id2event[event_id]
    else:
        print('没有找到', event_id, '对应的事件')
        return HttpResponse(json.dumps({'info': '没有找到事件'}))

    positive = [center_event]
    main_people = center_event.getPeople()
    # positive += main_people
    # positive += event.addrs

    events = []
    for person in main_people:
        events += person.getRelatedEvents(limit_depth=3)
    events = list(set(events))
    sim2event = {this_event: event2vec.similar_by_object(center_event, this_event)  for this_event in events}
    related_events = sorted(events , key=lambda this_event: sim2event[this_event])[-max_num:]
    related_events.append(center_event)
    # related_events = event2vec.getRelatedObject(positive=positive, num=max_num*2)
    # related_events = [event for event in related_events if not isinstance(event, int) and event.type=='event'][:max_num]
    # related_events.append(event)
    data = events2dict(related_events)
    
    response = {'data':data, 'center_event':event_id, 'info': '找到相关事件'}
    require2renponse[require_id] = response
    return HttpResponse(json.dumps(response))


def getRelatedPeopleEvents(request):
    person_ids = request.GET.get('person_ids')
    person_ids = person_ids.split(',')
    depth = int(request.GET.get('depth'))
    
    events = []
    for person_id in person_ids:
        person = personManager.getPerson(person_id)
        events += person.getRelatedEvents(limit_depth=depth)
    events = list(set(events))
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

# 找到多个人的所有关系（可以在前端实现交集并集的处理）
def getPersonRelation(request):
    person_ids = request.GET.get('person_ids')
    person_ids = person_ids.split(',')
    mian_people = [ personManager.getPerson(person_id) for person_id in person_ids]
    all_people = set()
    for main_person in mian_people:
        if main_person is None:
            print('没有找到', person_ids, '中的对应的人物')
            continue
        for event in main_person.event_array:
            for role in event.roles:
                person = role['person']
                all_people.add(person)
    result_events = set()
    for person in all_people:
        for event in person.event_array:
            all_person_is_in = True
            for role in event.roles:
                if role['person'] not in all_people:
                    all_person_is_in = False
            if all_person_is_in:
                result_events.add(event)
    result_events = list(result_events)
    print('找到了',len(all_people), '个人,共', len(result_events),'事件')
    result_events = events2dict(result_events)
    return HttpResponse(json.dumps({'data':result_events, 'info': '找到某人的所有关系'}))

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