from django.http import HttpResponse
from .data_model.event_manager import eventManager, triggerManager
from .data_model.person_manager import personManager
from .data_model.addr_manager import addrManager
from .data_model.neo4j_manager import graph
from py2neo import Graph,Node,Relationship,cypher
from .data_model.time_manager import timeManager
# from relation2type import getRelTypes
from .data_model.page_rank import loadPageRank,savePageRank  #,PersonGraph
from .data_model.word2vec import All2vec
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

from .evaluate import evaluateAccuracy, evalueForUsers

# 初始化
personManager.registEventManager(eventManager)
eventManager.getAll(60, multi_process=True)
personManager.loadExtraData()

personManager.calculateAllSongPeople()
event2vec= Event2Vec(personManager, eventManager, addrManager, triggerManager)
# event2vec.train(TOTAL_TIMES=5)
event2vec.load()
event2vec.load2Manager()
# event2vec.saveToView() 
# event2vec.saveToViewTrigger()

eventManager.event2vec = event2vec

# evaluateAccuracy()
evalueForUsers()

# 为了给宋词的系统下数据用的
# name2person = {}
# for person in personManager.person_array:
#     name = person.name
#     if name not in name2person:
#         name2person[name] = []
#     name2person[name].append(person)
# author_list = open('scSystemServer/data_model/data/author_list.csv', 'r', encoding='utf-8').read().strip('\n').split('\n')
# author_list = set(author_list)
# relation_set = set()
# for name in author_list:
#     if name in name2person:
#         people = name2person[name]
#         for person in people:
#             events = person.event_array
#             for event in events:
#                 roles = event.roles
#                 if len(roles)==2:
#                     ivl_names = [role['person'].name for role in roles]
#                     roles = [role['role'] for role in roles]
#                     if ivl_names[0] in author_list and ivl_names[1] in author_list:
#                         if roles[0] == '主角':
#                             row = ivl_names[0] + ',' + ivl_names[1] + ',' + event.trigger.name + ',0'
#                         elif roles[0] == '对象':
#                             row = ivl_names[1] + ',' + ivl_names[0] + ',' + event.trigger.name + ',0'
#                         else:
#                             row = ivl_names[1] + ',' + ivl_names[0] + ',' + event.trigger.name + ',1'
#                         relation_set.add(row)
# open('scSystemServer/诗人关系.csv', 'w', encoding='utf-8').write('\n'.join(relation_set))

# person_info = {}
# print(len(person_info.keys()))
# for name in author_list:
#     if name in name2person:
#         people = name2person[name]
#         person_info[name] = [elm.toDict()  for elm in people]
# open('scSystemServer/data_model/temp_data/词人基本信息.json', 'w', encoding='utf-8').write(json.dumps(person_info, indent=1, ensure_ascii = False))



# 加载trigger
trigger_types = set()
for elm in triggerManager.trigger_set:
    trigger_types.add(elm.parent_type)
    trigger_types.add(elm.type)
trigger_type2vec = {elm: event2vec.getVec(elm).tolist() for elm in trigger_types}

# all2vec = All2vec(personManager, addrManager, eventManager)

# cached_person_set = set()
# def chacheFunction(person):
#     # if person in cached_person_set:
#     #     return
#     # cached_person_set.add(person)
#     # events = person.getRelatedEvents(limit_depth=3)
#     # print('加载缓存', len(events),person)
#     # for event in events:
#     #     event.toDict(need_infer=True)
#     # print('缓存加载完成')
#     return
# threading.Thread(target=chacheFunction,args=(personManager.getPerson('person_3767'),)).start()


# person_graph = PersonGraph(eventManager)
# savePageRank(eventManager.event_array, personManager.person_array)
# person_rank = 
loadPageRank(personManager.person_array)
# for person in personManager.person_array:
#     person.page_rank = person_rank[person.id]

trigger_name_imp = eventManager.calculateImporatnce1()
# 有一些数据会在最初全部加载(对应的vec还没有加),还可以再优化的
# 宋代人物
init_people = {person.id: person.toDict() for person in personManager.person_array if person.isSong()}
#宋代地点
init_addrs = addrManager.toSongDict()
#所有触发词 
triggers = triggerManager.toDict()
# 转载
init_data = json.dumps({
    'people': init_people, 
    'addrs': init_addrs, 
    'triggers': triggers, 
    'trigger_imp': trigger_name_imp,
    'year2vec': event2vec.getYear2Vec(),
    'info': '初始化数据',
    'parent_trigger2vec': {}  #trigger_type2vec
})

open('scSystemServer/data_model/temp_data/trigger_imp.json', 'w', encoding='utf-8').write(json.dumps(trigger_name_imp, indent=2, ensure_ascii = False))
# open('scSystemServer/data_model/temp_data/预加载数据/data', 'w', encoding='utf-8').write(init_data)

# 获得苏轼和辛弃疾  3767 30359
for person in [personManager.getPerson('3767'), personManager.getPerson('30359')]:
    events = person.event_array
    new_events = []
    for event in events:
        new_event = {
            'time_range': event.time_range,
            'roles': [{'role':elm['role'], 'person': elm['person'].name, 'page_rank':elm['person'].page_rank }  for elm in event.roles],
            'trigger': {'name': event.trigger.name, 'score': event.trigger.score},
        }
        if(event.trigger.name=='担任'):
            new_event['detail'] = event.detail
        new_events.append(new_event)
    open('scSystemServer/data_model/temp_data/' + person.name +'.json', 'w', encoding='utf-8').write(json.dumps(new_events, indent=2, ensure_ascii = False))

# 获得词人的range
# poets_names = open('scSystemServer/data_model/data/poets.csv', 'r', encoding='utf-8').read().strip('\n').split('\n')
# poet2range = {}
# for name in poets_names:
#     people = personManager.person_array
#     poet2range[name] = []
#     for person in people:
#         if person.name == name:
#             poet2range[name].append(person.getProbYearRange())
# open('scSystemServer/data_model/temp_data/poet2range', 'w', encoding='utf-8').write(json.dumps(poet2range, indent=2, ensure_ascii = False))

print('共加载', len(eventManager.event_array), '事件')

def init(request):
    if init is not None:
        return  HttpResponse(init_data)
    else:
        data = {'info': 'server is loading, please wait'}
        return HttpResponse(json.dumps(data))

def events2dict(event_array, person_array=[], addr_array=[],need_infer = False):
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
    
    for person in person_array:
        people.add(person)
    for addr in addr_array:
        addrs.add(addr)

    #trigger 预加载已经加载好了
    results = {
        'events': { item.id: item.toDict(need_infer = need_infer)  for item in events},
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

    # threading.Thread(target=chacheFunction,args=(person,)).start()

    # temp_events = set(events)
    # for event in events:
    #     sim_events = event2vec.getSimEvents(event)[0:5]
    #     temp_events = temp_events.union(set(sim_events))
    # events = list(temp_events)
    return HttpResponse(json.dumps(events2dict(events, need_infer = True)))

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
        # print(event, prob_year)
        prob_year = {year: prob_year[year] for year in prob_year.keys()}
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

    # positive = [center_event]
    main_people = center_event.getPeople()
    # positive += main_people
    # positive += event.addrs

    events = []
    for person in main_people:
        events += person.getRelatedEvents(limit_depth=3)
    events = list(set(events))
    sim2event = {this_event: event2vec.similar_by_object(center_event, this_event)  for this_event in events}
    related_events = sorted(events , key=lambda this_event: -sim2event[this_event])[0:max_num]
    print(len(related_events), max_num)
    related_events.append(center_event)

    # related_events = event2vec.getRelatedObject(positive=positive, num=max_num*2)
    # related_events = [event for event in related_events if not isinstance(event, int) and event.type=='event'][:max_num]
    # related_events.append(event)

    # # 根据情况判断要不要加
    for person in main_people:
        related_events += person.event_array

    related_events = list(set(related_events))
    data = events2dict(related_events, need_infer = False)
    
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


def patch(objects):
    objects = list(set(objects))

    type2objects = {}
    type2objects['person'] = []
    type2objects['addr'] = [] 
    type2objects['event'] = []
    type2objects['time'] = []

    print(objects)
    for elm in objects:
        if isinstance (elm, str) :
            type2objects['time'].append(elm)
            continue
        elm_type = elm.type
        if elm_type not in type2objects:
            type2objects[elm_type] = []
            print(elm_type)
        type2objects[elm_type].append(elm.toDict())
    
    return {elm_type: type2objects[elm_type] for elm_type in type2objects.keys()}

def getRelatedObjects(request):
    positive = request.GET.get('positive')
    negative = request.GET.get('negative')
    num = int(request.GET.get('num'))

    positive = positive.split(',')
    negative = negative.split(',')
    positive = [elm for elm in positive if elm is not None and elm!='']
    negative = [elm for elm in negative if elm is not None and elm!='']
    print(positive, negative)
    objects = event2vec.getRelatedObjectById(negative_ids=negative, positive_ids=positive, num=num)
    # 分包
    return HttpResponse(json.dumps({'data': patch(objects), 'info': '查找相似内容'}))

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