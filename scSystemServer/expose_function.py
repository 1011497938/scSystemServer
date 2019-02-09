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
person_graph = PersonGraph(eventManager)


# 有一些数据会在最初全部加载(对应的vec还没有加)
# 宋代人物
song_people = {person.id: person.toDict() for person in personManager.person_array if person.isSong()}
#宋代地点
song_addrs = addrManager.toSongDict()
#所有触发词 
triggers = triggerManager.toDict()
# 转载
init_data = json.dumps({'people': song_people, 'addrs': song_addrs, 'triggers': triggers, 'info': '初始化数据'})
open('scSystemServer/data_model/temp_data/预加载数据/data', 'w', encoding='utf-8').write(init_data)


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


if __name__ == '__main__':
	print('测试')
	# event_extractor = EventExtractor()


