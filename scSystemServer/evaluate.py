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


def evaluateAccuracy():
    max_num = 15
    num_true = {i+1: 0 for i in range(max_num)}
    num_count = {i+1: 0 for i in range(max_num)}

    for event in eventManager.event_array:
        if event.isCertain():
            year = event.time_range[0]

            prob_year = eventManager.event2vec.getEventProbYear(event)
            prob_year = {year: prob_year[year] for year in prob_year.keys()}
            # prob_year = [(year, prob_year[year]) for year in prob_year]
            prob_year = sorted(prob_year.items(), key = lambda _item: _item[1], reverse = True)
            prob_year = [y[0] for y in prob_year]

            for i in range(max_num):
                if len(prob_year) < i:
                    continue
                i = i + 1
                num_count[i] += 1
                s_y = prob_year[:i+1]
                if year in s_y:
                    num_true[i] += 1

    num_acc = {i+1: num_true[i+1]/num_count[i+1] for i in range(max_num)}
    print(num_true, num_count, num_acc)


# {1: 38304, 2: 41576, 3: 39795, 4: 35284, 5: 31170, 6: 28578, 7: 26464, 8: 24012, 9: 21600, 10: 19183, 11: 16627, 12: 14103, 13: 11620, 14: 9394, 15: 7688} {1: 299229, 2: 183242, 3: 99436, 4: 73842, 5: 58331, 6: 50249, 7: 44286, 8: 38736, 9: 33741, 10: 29148, 11: 24624, 12: 20465, 13: 16726, 14: 13426, 15: 10875} {0.12800898308653239, 0.22689121489614827, 0.47783104466292897, 0.4002071684299449, 0.5343642317121257, 0.5687277358753408, 0.5975703382558822, 0.6198884758364313, 0.6401707121899173, 0.6581240565390422, 0.6996871741397289, 0.675235542560104, 0.6891277791351087, 0.6947267726892263, 0.7069425287356322}

# {1: 38304, 2: 41576, 3: 39795, 4: 35284, 5: 31170, 6: 28578, 7: 26464, 8: 24012, 9: 21600, 10: 19183, 11: 16627, 12: 14103, 13: 11620, 14: 9394, 15: 7688} 
# {1: 299229, 2: 183242, 3: 99436, 4: 73842, 5: 58331, 6: 50249, 7: 44286, 8: 38736, 9: 33741, 10: 29148, 11: 24624, 12: 20465, 13: 16726, 14: 13426, 15: 10875} 
# {1: 0.12800898308653239, 2: 0.22689121489614827, 3: 0.4002071684299449, 4: 0.47783104466292897, 5: 0.5343642317121257, 6: 0.5687277358753408, 7: 0.5975703382558822, 8: 0.6198884758364313, 9: 0.6401707121899173, 10: 0.6581240565390422, 11: 0.675235542560104, 12: 0.6891277791351087, 13: 0.6947267726892263, 14: 0.6996871741397289, 15: 0.7069425287356322}


def evalueForUsers():
    events = eventManager.event_array[: 100]
    e_ids = [e.id for e in events]
    # print(eventManager.event_array)
    del_time_es = e_ids
    del_addr_es = e_ids

    for e_id in del_time_es:
        event = eventManager.get(e_id)
        event.time_range = [-9999, 9999]
        # print(e_id, event)
    
    for e_id in del_addr_es:
        event = eventManager.get(e_id)
        print(e_id, event,  [addr.name for addr in event.addrs])
        event.addr = []