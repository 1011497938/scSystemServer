import numpy as np
import networkx as nx
from gensim.models import Word2Vec,keyedvectors
import os
from .node2vec.node2vec import Graph
# from .meta_path2vec.dataset import Dataset
# from .meta_path2vec.skipgram import build_model,traning_op,train

import json

class Event2Vec(object):
    def __init__(self, personManager, eventManager, addrManager, triggerManager):
        print('构建event2vec')
        self.model = None
        self.eventManager = eventManager
        self.addrManager = addrManager
        self.personManager = personManager
        self.triggerManager = triggerManager

        self.model_path = 'scSystemServer/data_model/temp_data/event_model'

        self.id2object = {}
        for event in eventManager.event_array:
            if event.id not in self.id2object:
                self.id2object[event.id] = event
            else:
                print(event, '的id重复了')

        for person in personManager.person_array:
            if person.id not in self.id2object:
                self.id2object[person.id] = person
            else:
                print(person, '的id重复了')

        for addr in addrManager.addr_array:
            if addr.id not in self.id2object:
                self.id2object[addr.id] = addr
            else:
                print(addr, '的id重复了')

        for trigger in triggerManager.trigger_set:
            if trigger.id not in self.id2object:
                self.id2object[trigger.id] = trigger
            else:
                print(trigger, '的id重复了')

        for year in range(-9999, 10000):
            year_id = str(year)
            self.id2object[year_id] = year
        self.G = None

    def load(self):
        self.model = Word2Vec.load(self.model_path)
        print('加载完成')
        return self.model

    def generate_graph(self):
        if self.G is not None:
            return

        eventManager = self.eventManager
        addrManager = self.addrManager
        personManager = self.personManager
        triggerManager = self.triggerManager
        weighted_edges = []

        # 加载图
        self.G = nx.DiGraph()
        G = self.G
        for event in eventManager.event_array:
            G.add_node(event.id)

        for person in personManager.person_array:
            G.add_node(person.id)

        for addr in addrManager.addr_array:
            G.add_node(addr.id)

        for trigger in triggerManager.trigger_set:
            G.add_node(trigger.id)
            weighted_edges.append((trigger.id, trigger.type, 1))
            G.add_node(trigger.parent_type)
            weighted_edges.append((trigger.type, trigger.parent_type, 1))
            G.add_node(trigger.type)

        for year in range(-9999, 10000):
            year_id = str(year)
            G.add_node(year_id)


        for event in eventManager.event_array:
            trigger = event.trigger
            weighted_edges.append((event.id, trigger.id, 1))

            roles = event.roles
            for elm in roles:
                # 角色怎么办以后还要想一想
                # role = elm['role']
                person = elm['person']
                weighted_edges.append((event.id, person.id, 1))

            addrs = event.addrs
            for addr in addrs:
                weighted_edges.append((event.id, addr.id, 1))

            time_ranges = event.time_range
            if time_ranges[1]-time_ranges[0]<10:
                for year in range(time_ranges[0], time_ranges[1]+1):
                    year = str(year)
                    weighted_edges.append((event.id, year, time_ranges[1]-time_ranges[0]+1))  #/

        for addr in addrManager.addr_array:
            sons = addr.sons
            parents= addr.parents
            for son in sons:
                weighted_edges.append((addr.id, son.id, 1))
            for parent in parents:
                weighted_edges.append((addr.id, parent.id, 1))   

        for year in range(-9999, 9999):
            year1 = str(year)
            year2 = str(year+1)
            weighted_edges.append((year1, year2, 1))


        # 还要加上亲属关系
        G.add_weighted_edges_from(weighted_edges)
        
        G = Graph(G, False, 1, 1)
        G.preprocess_transition_probs()
        self.G = G
        
        return G

    def generate_data(self, walk_length, start_node):
        if self.G is None:
            print('还没有生成图了，怎么就生成数据了')
            self.G = self.generate_graph()

        walks = self.G.simulate_walks(walk_length, start_node)
        walks = [list(map(str, walk)) for walk in walks]
        return walks

    def train(self, TOTAL_TIMES=20):
        person_array = self.personManager.person_array

        model_path = self.model_path 
        for time in range(0, TOTAL_TIMES):
            print(time, '/', TOTAL_TIMES, '次训练')
            walks = self.generate_data(8,8)
            if not os.path.exists(model_path):
                print('创建新的model')
                model = Word2Vec(walks, size=32, window=10, min_count=0, sg =1, workers=8, iter=5)
            else:
                # if time==0:
                print('加载model')
                model = Word2Vec.load(model_path)
                model.train(walks, total_examples=len(walks), epochs=5)
                
                print('加载meta _path')
                walks = []
            for person in person_array:
                sort_events = person.getSortedEvents()
                year2events = person.getYear2event()
                for year in year2events:
                    walks.append([event.trigger.id  for event in year2events[year]])
                walks.append([event.trigger.id  for event in sort_events])
                addr_walk = []
                for event in sort_events:
                    addr_walk += [addr.id for addr in event.addrs]
                walks.append(addr_walk)
                person_walk = []
                for event in sort_events:
                    person_walk += [role['person'].id for role in event.roles]
                walks.append(person_walk)
            print('加载meta _path完成')  
            model.train(walks, total_examples=len(walks), epochs=2)

            print('保存model')
            model.save(model_path)
            self.model = model
        self.finish_train()
        self.G = None

    def finish_train(self):
        self.G = None

    def getVec(self, id):
        wv = self.model.wv
        # if key in model.wv.vocab:
        return wv[id]

    def getYear2Vec(self):
        year2vec = {}
        for year in range(0, 1900):
            year_id = str(year)
            vec = self.getVec(year_id)
            year2vec[year] = vec.tolist()
        for year in [-9999, 9999]:
            year_id = str(year)
            vec = self.getVec(year_id)
            year2vec[year] = vec.tolist()
        return year2vec

    def load2Manager(self):
        eventManager = self.eventManager
        addrManager = self.addrManager
        personManager = self.personManager
        triggerManager = self.triggerManager

        model = self.model
        open("scSystemServer/data_model/temp_data/object_id.json","w",encoding='utf-8').write(json.dumps({'data': [word for word in model.wv.vocab]}, indent=3, ensure_ascii = False))
        if model is None:
            self.load()

        wv = model.wv
        vocab = wv.vocab
        arrays = [eventManager.event_array, personManager.person_array,  triggerManager.trigger_set, addrManager.addr_array]
        for array in arrays:
            for elm in array:
                # print(elm)
                object_id = elm.id
                if object_id in vocab:
                    # print(elm, wv[object_id].tolist())
                    elm.vec = wv[object_id].tolist()
                else:
                    print(elm, '不存在向量')


    def getObjectById(self, id):
        # if isinstance (id, int) or id.isdigit():
        #     return str(id)
        # print(self.id2object.keys())
        id = str(id)

        if id in self.id2object:
            return self.id2object[id]
        elif 'event' in id:
            return self.eventManager.get(id)
        elif 'addr' in id:
            return self.addrManager.id2addr[id]
        elif 'person' in id:
            return self.personManager.getPerson(id)
        elif id.isdigit():
            return int(id)
        print(id, '找到不到啊')
        return None

    def getSimEvents(self ,event):
        if event.sim_events is not None:
            # print(event, '已存在')
            return event.sim_events

        main_people = event.getPeople()
        events = []
        for person in main_people:
            events += person.getRelatedEvents(limit_depth=2)

        event2sim = {}
        for event2 in events:
            event2sim[event2] = self.similar_by_object(event, event2)
        events = sorted(events, key=lambda elm: -event2sim[elm])
        event.sim_events = events
        # print(event, '相似事件')
        # for event in events[0:10]:
        #     print(event)
        # print('结束~\n') 
        # print(events)
        return events

    def getRelatedObject(self, positive = [], negative=[], num=100):
        model = self.model
        positive_ids = [elm.id for elm in positive]
        negative_ids = [elm.id for elm in negative]

        ids =  model.wv.most_similar(positive=positive_ids, negative=negative_ids, topn=num)
        objects = [self.getObjectById(id[0])  for id in ids] 
        objects = [elm for elm in objects if elm is not None]
        return objects

    def getRelatedObjectById(self, positive_ids = [], negative_ids = [], num=100):
        model = self.model
        ids =  model.wv.most_similar(positive=positive_ids, negative=negative_ids, topn=num)
        objects = [self.getObjectById(id[0])  for id in ids] 
        objects = [elm for elm in objects if elm is not None]
        return objects

    def getEventCertainty(self, event):
        if event.certainty is not None:
            return event.certainty
        model = self.model
        sim = model.wv.most_similar(positive=[event], negative=[], topn=2)[1][1]
        event.certainty = sim
        return sim

    def getEventProbYear(self, center_event):
        if center_event.prob_year is not None:
            return center_event.prob_year
        # print(center_event, 'getEventProbYear')
        events = self.getSimEvents(center_event)[0:100]
        year2prob = {}
        for event in events:
            if event.isCertain():
                sim = self.similar_by_object(event, center_event)
                year = event.time_range[0]
                if year in year2prob and year2prob[year]>sim:
                    pass
                else:
                    year2prob[year] = sim

        center_event.prob_year = year2prob
        # print(len(events), year2prob, len([event for event in events if event.isCertain()]))
        return year2prob

    def getEventProbAddr(self, center_event):
        if center_event.prob_addr is not None:
            return center_event.prob_addr
        # print(center_event, 'getEventProbAddr')
        events = self.getSimEvents(center_event)[0:100]
        center_people = center_event.getPeople()
        addr2prob = {}
        for event in events:
            people = event.getPeople()
            if len(event.addrs)>0 :
                for person in center_people:
                    if person in people:
                        for addr in event.addrs:
                            addr2prob[addr.id] = self.similar_by_object(event, center_event)
                        break
                if len(addr2prob.keys())>0:
                    break
        center_event.prob_addr = addr2prob
        return addr2prob

    def getEventProbPerson(self, center_event):
        if center_event.prob_person is not None:
            return center_event.prob_person
        events = self.getSimEvents(center_event)
        center_people = center_event.getPeople()
        person2prob = {}
        for event in events:
            people = event.getPeople()
            people = [person for person in people if person not in center_people]
            if len(people)>0:
                for person in people:
                    person2prob[person.id] = self.similar_by_object(event, center_event)
                break
        center_event.prob_person = person2prob
        return person2prob


    def similar_by_object(self, object1, object2):
        model = self.model
        if isinstance (object1, int):
            id1 = str(object1)
        else:
            id1 = object1.id

        if isinstance (object2, int):
            id2 = str(object2)
        else:
            id2 = object2.id
        id1 = str(id1)
        id2 = str(id2)

        if id1 not in model.wv.vocab or id2 not in model.wv.vocab:
            print(id1, id2, '中有一个不存在')
            return 0
        # print(id1, id2, object1, object2)
        return  float(model.wv.similarity(id2, id1))


    def saveToView(self):
        eventManager = self.eventManager
        wv = self.model.wv
        # vocabulary = self.model.vocabulary

        open("scSystemServer/data_model/temp_data/object_id.json","w",encoding='utf-8').write(json.dumps({'data': [word for word in wv.vocab]}, indent=3, ensure_ascii = False))
        
        person = self.personManager.getPerson('3767')
        events = person.getRelatedEvents(limit_depth=3)

        objects = set()
        for event in events:
            objects.add(event)
            people = event.getPeople()
            # print(people)
            for person in people:
                objects.add(person)
                # print(person)
            for addr in event.addrs:
                objects.add(addr)
                # print(addr)
            objects.add(event.trigger)
            
        has_len = 0
        dont_has_len = 0
        fvec = open("scSystemServer/data_model/temp_data/new_event_vec","w",encoding='utf-8')
        fmetia = open("scSystemServer/data_model/temp_data/new_event_meta","w",encoding='utf-8')
        for elm in objects:
            elm_id = elm.id
            if elm_id not in wv.vocab:
                # print(elm,  '不存在向量')
                dont_has_len += 1
                continue
            # print(event,  '存在向量!!!!!!!!!!')
            vec = wv[elm_id]
            fvec.writelines("\t".join([str(value) for value in vec])+"\n")
            fmetia.write(str(elm)+'\n')
            has_len += 1
        fvec.close()
        fmetia.close() 
        print(has_len, dont_has_len)
        return

    def saveToViewTrigger(self):
        triggerManager = self.triggerManager

        fvec = open("scSystemServer/data_model/temp_data/trigger_vec","w",encoding='utf-8')
        fmetia = open("scSystemServer/data_model/temp_data/trigger_meta","w",encoding='utf-8')
        fmetia.write('name\ttype\tparent type\n')
        for trigger in triggerManager.trigger_set:
            vec = self.getVec(trigger.id)
            fmetia.write('{}\t{}\t{}\n'.format(trigger.name, trigger.type, trigger.parent_type))
            fvec.writelines("\t".join([str(value) for value in vec])+"\n")
        fvec.close()
        fmetia.close()

# # 采用meta_path的graph2vec
# class Event2Vec2(object):
#     def __init__(self, personManager, eventManager, addrManager, triggerManager):
#         print('构建event2vec')
#         self.eventManager = eventManager
#         self.addrManager = addrManager
#         self.personManager = personManager
#         self.triggerManager = triggerManager

#     def train(self, epoch=10):
#         eventManager = self.eventManager
#         addrManager = self.addrManager
#         personManager = self.personManager
#         triggerManager = self.triggerManager

#         id_type = []
#         corups = []

#         for event in eventManager.event_array:
#             id_type.append([event.id, 'event'])
#             corups.append([event.id])

#         for person in personManager.person_array:
#             id_type.append([person.id, 'person'])
#             corups.append([person.id])

#         for addr in addrManager.addr_array:
#             id_type.append([addr.id, 'addr'])
#             corups.append([addr.id])

#         for trigger in triggerManager.trigger_set:
#             id_type.append([trigger.id, 'trigger'])
#             corups.append([trigger.id])

#         for year in range(-9999, 10000):
#             year = str(year)
#             id_type.append([year, 'year'])
#             corups.append([year])

#         for event in eventManager.event_array:
#             trigger = event.trigger
#             event_corups = [[event.id, trigger.id]]

#             # print(event_corups)
#             temp_event_corups = []
#             for event_corup in event_corups:
#                 for elm in event.roles:
#                     temp_event_corup = list( event_corup)
#                     # 角色怎么办以后还要想一想
#                     # role = elm['role']
#                     person = elm['person']
#                     temp_event_corup.append(person.id)
#                     # print(temp_event_corup, 'c')
#                     temp_event_corups.append(temp_event_corup)
#             event_corups = temp_event_corups
#             # print(event_corups, 'b')

#             if len(event.addrs)!=1:
#                 temp_event_corups = []
#                 for event_corup in event_corups:
#                     for addr in event.addrs:
#                         temp_event_corup = list(event_corup)
#                         temp_event_corup.append(addr.id)
#                         temp_event_corups.append(temp_event_corup)
#             event_corups = temp_event_corups

#             time_ranges = event.time_range
#             temp_event_corups = []
#             for event_corup in event_corups:
#                 for time in time_ranges:
#                     if time!=9999 or time!=-9999:
#                         temp_event_corup = list(event_corup)
#                         temp_event_corup.append(str(time))
#                         temp_event_corups.append(temp_event_corup)
#             event_corups = temp_event_corups
#             corups += event_corups
#             # print(corups, event_corups)
#             # for elm in event_corups:
#             #     corups.append(elm)
#             # print(corups)
#         # print(corups)

#         for addr in addrManager.addr_array:
#             sons = addr.sons
#             parents= addr.parents
#             for son in sons:
#                 corups.append([addr.id, son.id])
#             for parent in parents:
#                 corups.append([parent.id, addr.id])   

#         for year in range(-9999, 9999):
#             corups.append([str(year), str(year+1)])
            
#         # print(corups)
#         # print(random_walks[0:10])
#         dataset= Dataset(random_walks=corups,node_type_mapping=id_type,window_size=5)

#         # # 减少不必要的内存占用
#         # id2type = None
#         # self.origin_evnet2vec = None
#         # eventManager.selfDestory()
#         # addrManager.selfDestory()
#         # personManager.selfDestory()
#         # triggerManager.selfDestory()

#         center_node_placeholder,context_node_placeholder,negative_samples_placeholder,loss = build_model(BATCH_SIZE=1,VOCAB_SIZE=len(dataset.nodeid2index),EMBED_SIZE=128,NUM_SAMPLED=5)
#         optimizer = traning_op(loss,LEARNING_RATE=0.01)

#         LOG_DICT = 'scSystemServer\data_model\meta_path2vec\log'
#         train(center_node_placeholder,context_node_placeholder,negative_samples_placeholder,loss,dataset,optimizer,NUM_EPOCHS=10,BATCH_SIZE=1,NUM_SAMPLED=5,care_type=1,LOG_DIRECTORY=LOG_DICT,LOG_INTERVAL=-1,MAX_KEEP_MODEL=10)

#     def loadVec(self):
#         object2vec = {}
#         return object2vec