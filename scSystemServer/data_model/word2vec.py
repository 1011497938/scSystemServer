# -*- coding: UTF-8 -*- 
import gensim
from multiprocessing import cpu_count
# import jieba
import re
# from snownlp import SnowNLP
import json
from sklearn.feature_extraction.text import TfidfTransformer  
from sklearn.feature_extraction.text import CountVectorizer  
from sklearn.preprocessing import StandardScaler

class All2vec(object):
    """docstring for AllToVec"""
    def __init__(self, personManager, addrManager, eventManager):
        self.vec_size = 20

        # self.personManager = personManager

        # self.allEvents2Vec(personManager)
        # self.allPerson2Vec(personManager)
        # self.relationEmbedding(personManager)
        self.addr_model, self.addr2vec = self.allAddr2vec(addrManager)
        self.trigger_model, self.trigger2vec = self.allEvents2Vec(personManager)
        self.event2idf = self.getEventIdf(eventManager, personManager)
        self.person_model, self.person2vec = self.allPerson2Vec(personManager)
        self.year_person_model, self.year_person2vec = self.yearPerson2vec(eventManager, personManager)

    def allAddr2vec(self, addrManager):
        print('地点embedding')
        addr_array = addrManager.addr_array
        corpus = []
        # 每次取一条关系列

        def _add2path(now_addr, now_path):
            # print(now_addr)
            if len(now_addr.parents)!=0:
                new_pathes = []
                for parent in now_addr.parents:
                    if parent not in now_path:
                        new_path = list(now_path)
                        new_path.append(parent)
                        pathes = _add2path(parent, new_path)
                        for path in pathes:
                            new_pathes.append([now_addr] + path)
                return new_pathes
            else:
                return [[now_addr]]

        # leaf_addrs = []
        all_pathes = []
        for addr in addr_array:
            all_pathes += _add2path(addr, [addr]) 
            if len(addr.sons)!=0:
                all_pathes.append(addr.sons)
            # else:
            #     all_pathes += _add2path(addr, [addr]) 
                
            if len(addr.parents)!=0:
                all_pathes.append(addr.parents)
        corpus = [ [str(addr.id) for addr in path]  for path in all_pathes]
        # print(len(all_pathes))
        # print(len(addr_array),len(leaf_addrs))

        model = gensim.models.Word2Vec(corpus, workers=cpu_count(), window=3, min_count=1, size=self.vec_size, sg=0)
        model.train(corpus, total_examples=len(corpus), epochs=30)




        # # 输出向量
        # fvec = open("./temp_data/addr_vec","w",encoding='utf-8')
        # for key in model.wv.vocab:
        #     fvec.writelines("\t".join([str(elm) for elm in model.wv[key] ])+"\n")
        # fvec.close()

        # fmetia = open("./temp_data/addr_meta","w",encoding='utf-8')
        # fmetia.writelines("word\tdesc\n")
        # for key in model.wv.vocab:
        #     addr = addrManager.getAddr(key)
        #     fmetia.writelines(addr.name + '\t' + str(addr) + '\n')
        # fmetia.close()

        id2vec = {}
        for key in model.wv.vocab:
            id2vec[key] = model.wv[key]
        return model,id2vec

    # 尝试使用word2vec做event2vec
    def allEvents2Vec(self, personManager):
        # print('开始训练模型')
        print('事件embedding')
        person_array = personManager.person_array
        # 还要按时间进行排序
        corpus = []

        # 换一种方法
        for person in person_array:
            #按照年分
            year2event = person.getYear2event()
            for year in year2event:
                year_events = []
                period_events = []

                events = year2event[year]
                for event in events:
                    for role in event.roles:
                        if role['person'] == person:
                            year_events.append(event.trigger.name + ' ' + role['role'])

                for year in range(year-2, year+3):
                    if year in year2event:
                        events = year2event[year]
                        for event in events:
                            for role in event.roles:
                                if role['person'] == person:
                                    period_events.append(event.trigger.name + ' ' + role['role'])   
                corpus.append(list(period_events))
                corpus.append(list(year_events))

            # 按人生分
            life_events = [] 
            events = person.getAllEvents()
            for event in events:
                for role in event.roles:
                    if role['person'] == person:
                        life_events.append(event.trigger.name + ' ' + role['role'])
            corpus.append(life_events)
        
        # 两两关系
        relation_set = {}
        def pairHash(person1, person2):
            return (person1, person2)
            if person1.id < person2.id:
                return (person1, person2)
            else:
                return (person2, person1)

        # 人生暂时注释掉了
        for person in person_array:
            events = person.getAllEvents()
            for event in events:
                roles  = event.roles
                if len(roles)!=2:
                    continue
                
                main_role = None
                opp_role = None
                opp_person = None
                for role in roles:
                    this_person = role['person']
                    role = role['role']
                    if this_person==person:
                        main_role = role
                    else:
                        opp_role = role
                        opp_person = this_person

                hash_pair = pairHash(person, opp_person)
                if hash_pair not in relation_set:
                    relation_set[hash_pair] = []
                relation_set[hash_pair].append(  event.trigger.name + ' ' + str(main_role) )

        for key in relation_set:
            events = relation_set[key]
            events = list(events)
            corpus.append(events)

        corpus = [corpu for corpu in corpus if len(corpu)>0]

        # print(corpus)
        print('数据加载完成')
        model = gensim.models.Word2Vec(corpus, workers=cpu_count(), window=5, size=self.vec_size, min_count=1)
        model.train(corpus, total_examples=len(corpus), epochs=30)

        # model.save("./temp_data/Word2Vec_event.model")

        # # 输出向量
        # fvec = open("scSystemServer/data_model/temp_data/event_vec","w",encoding='utf-8')
        # for key in model.wv.vocab:
        #     fvec.writelines("\t".join([str(elm) for elm in model.wv[key] ])+"\n")
        # fvec.close()


        # fmetia = open("scSystemServer/data_model/temp_data/event_meta","w",encoding='utf-8')
        # # fmetia.writelines("word\tcount\n")
        # for key in model.wv.vocab:
        #     fmetia.writelines(key + '\n')
        # fmetia.close()

        id2vec = {}
        json_text = {}
        for key in model.wv.vocab:
            id2vec[key] = model.wv[key]
            json_text[key] = str(model.wv[key])


        # open('./temp_data/event2vec.json', 'w', encoding='utf-8').write(json.dumps({'data': corpus}, indent=4, ensure_ascii = False))
        return model, id2vec

    # 计算事件的重要度
    def getEventIdf(self, eventManager, personManager):
        triggers = set()
        for event in eventManager.event_array:
            for role in event.roles:
                trigger_id = event.trigger.name + ' ' + role['role']
                triggers.add(trigger_id)

        triggers = list(triggers)
        trigger2index = { trigger: index for index, trigger in enumerate(triggers)}
        index2trigger = { index: trigger for index, trigger in enumerate(triggers)}

        counts = []
        for person in personManager.person_array:
            #按照年分
            year2event = person.getYear2event()
            for year in year2event:
                events = year2event[year]
                trigger_count = {}
                for event in events:
                    for role in event.roles:
                        if role['person'] == person:
                            trigger = event.trigger.name + ' ' + role['role']
                            if trigger in trigger_count:
                                trigger_count[trigger] += 1
                            else:
                                trigger_count[trigger] = 1
                count = [0]*len(triggers)
                for trigger in trigger_count:
                    count[trigger2index[trigger]] = trigger_count[trigger]
                counts.append(count)

        transformer = TfidfTransformer(smooth_idf=True)
        tfidf = transformer.fit_transform(counts)

        # 标准化
        idf = transformer.idf_
        idf = [[value] for value in idf]
        idf = StandardScaler().fit_transform(idf)
        idf = [value[0] for value in idf]

        event2idf = { index2trigger[index]: value for index,value in enumerate(idf)}
        open('scSystemServer/data_model/temp_data/event2idf.json', 'w', encoding='utf-8').write(json.dumps(event2idf, indent=4, ensure_ascii = False))
        return event2idf

    # 根本用不了，大概要换社交关系相关的算法，关系应该有个权重
    def allPerson2Vec(self, personManager):
        print('人物embedding')
        person_array = personManager.person_array
        # 还要按时间进行排序
        corpus = []
        all_events = []
        for person in person_array:
            if not person.isSong():
                continue
            events = person.getAllEvents()
            persons = []
            for event in events:
                roles = event.roles
                event_corup = []
                for role in roles:
                    persons.append(role['person'].id)
                    all_events.append(role['person'].id)
                    event_corup.append(role['person'].id)
                corpus.append(event_corup)
            # corpus.append(persons)
                
        # print(corpus)

        print('人物数据加载完成')
        model = gensim.models.Word2Vec(corpus, workers=cpu_count(), window=10, min_count=1, size=self.vec_size)
        model.train(corpus, total_examples=len(corpus), epochs=30)

        # 输出向量
        fvec = open("scSystemServer/data_model/temp_data/person_vec","w",encoding='utf-8')
        for key in model.wv.vocab:
            person = personManager.getPerson(key)
            if person.isSong():
                fvec.writelines("\t".join([str(elm) for elm in model.wv[key] ])+"\n")
        fvec.close()

        counts = {}
        for event in all_events:
            if event in counts.keys():
                counts[event] += 1
            else:
                counts[event] = 1

        fmetia = open("scSystemServer/data_model/temp_data/person_meta","w",encoding='utf-8')
        fmetia.writelines("word\tcount\tname\tbirth_year\tdeath_year\n")
        for key in model.wv.vocab:
            person = personManager.getPerson(key)
            if person.isSong():
                fmetia.writelines(key + '\t' + str(counts[key]) +  '\t' + str(person.name) + '\t' + str(person.birth_year) + '\t' + str(person.death_year) + '\n')
        fmetia.close()


        # event2vec = {}
        # for key in model.wv.vocab:
        #     event2vec[key] = str(model.wv[key][0])

        # open('./temp_data/person2vec.json', 'w', encoding='utf-8').write(json.dumps(event2vec, indent=4, ensure_ascii = False))

        id2vec = {}
        for key in model.wv.vocab:
            id2vec[key] = model.wv[key]
        return model, id2vec


    def yearPerson2vec(self, eventManager, personManager):
        print('人物 + 年份 embedding')
        person_array = personManager.person_array
        # 还要按时间进行排序
        corpus = []
        all_events = []
        for person in person_array:
            if not person.isSong():
                continue
            events = person.getAllEvents()
            persons = []
            this_persons = []
            for event in events:
                roles = event.roles
                event_corup = []
                year = str(event.time_range[0])
                this_persons.append(person.id + ',' + year)
                for role in roles:
                    persons.append(role['person'].id + ',' + year)
                    all_events.append(role['person'].id + ',' + year)
                    event_corup.append(role['person'].id + ',' + year)
                corpus.append(event_corup)
            corpus.append(persons)
            corpus.append(this_persons)

        # print(corpus)

        print('人物数据加载完成')
        model = gensim.models.Word2Vec(corpus, workers=cpu_count(), window=10, min_count=1, size=self.vec_size)
        model.train(corpus, total_examples=len(corpus), epochs=30)

        # 输出向量
        fvec = open("scSystemServer/data_model/temp_data/year_person_vec","w",encoding='utf-8')
        for key in model.wv.vocab:
            person_id = key.split(',')[0]
            year = key.split(',')[1]
            person = personManager.getPerson(person_id)
            if person.isSong():
                fvec.writelines("\t".join([str(elm) for elm in model.wv[key] ])+"\n")
        fvec.close()

        counts = {}
        for event in all_events:
            if event in counts.keys():
                counts[event] += 1
            else:
                counts[event] = 1

        fmetia = open("scSystemServer/data_model/temp_data/year_person_meta","w",encoding='utf-8')
        fmetia.writelines("year\tword\tcount\tname\tbirth_year\tdeath_year\n")
        for key in model.wv.vocab:
            person_id = key.split(',')[0]
            year = key.split(',')[1]
            person = personManager.getPerson(person_id)
            if person.isSong():
                fmetia.writelines(year + '\t' + key + '\t' + str(counts[key]) +  '\t' + str(person.name) + '\t' + str(person.birth_year) + '\t' + str(person.death_year) + '\n')
        fmetia.close()


        # event2vec = {}
        # for key in model.wv.vocab:
        #     event2vec[key] = str(model.wv[key][0])

        # open('./temp_data/person2vec.json', 'w', encoding='utf-8').write(json.dumps(event2vec, indent=4, ensure_ascii = False))

        id2vec = {}
        for key in model.wv.vocab:
            id2vec[key] = model.wv[key]
        return model, id2vec


    # 两两之间关系 以及关系对事件影响 的embedding
    def relationEmbedding(self, personManager):
        print('关系embedding')
        persons = personManager.person_array
        relation_set = {}
        def pairHash(person1, person2):
            return (person1, person2)
            if person1.id < person2.id:
                return (person1, person2)
            else:
                return (person2, person1)

        for person in persons:
            events = person.getAllEvents()
            for event in events:
                roles  = event.roles
                if len(roles)!=2:
                    continue
                
                main_role = None
                opp_role = None
                opp_person = None
                for role in roles:
                    this_person = role['person']
                    role = role['role']
                    if this_person==person:
                        main_role = role
                    else:
                        opp_role = role
                        opp_person = this_person

                hash_pair = pairHash(person, opp_person)
                if hash_pair not in relation_set:
                    relation_set[hash_pair] = []
                relation_set[hash_pair].append( str(main_role) + '/' + str(event.trigger.name) + '/' + str(opp_role) )

        # fs = open("./temp_data/data","w",encoding='utf-8')
        corpus = []
        for key in relation_set:
            events = relation_set[key]
            events = list(events)
            if len(events)>=2:
                corpus.append(events)
                # fs.write(',  '.join(events)+'\n')



        # print(corpus)

        print('数据加载完成')
        model = gensim.models.Word2Vec(corpus, workers=cpu_count(), window=3, min_count=100, size=self.vec_size, sg=0)
        model.train(corpus, total_examples=len(corpus), epochs=30)

        # # 输出向量
        # fvec = open("./temp_data/relation_vec","w",encoding='utf-8')
        # for key in model.wv.vocab:
        #     fvec.writelines("\t".join([str(elm) for elm in model.wv[key] ])+"\n")
        # fvec.close()

        # fmetia = open("./temp_data/relation_meta","w",encoding='utf-8')
        # # fmetia.writelines("word\n")
        # for key in model.wv.vocab:
        #     fmetia.writelines(key + '\n')
        # fmetia.close()


    #     event2vec = {}
    #     for key in model.wv.vocab:
    #         event2vec[key] = {
    #             'vec':str(model.wv[key]),
    #             'most_similars': getSim(key, model)
    #         }
    #     open('./temp_data/relationEmbedding.json', 'w', encoding='utf-8').write(json.dumps(event2vec, indent=4, ensure_ascii = False))
    #     print('训练完成')

        id2vec = {}
        for key in model.wv.vocab:
            id2vec[key] = model.wv[key]
        return id2vec

    def getSim(self, object, model, num = 5):
        most_similars = []
        for i in model.most_similar(object):
            # print(i[0],i[1])
            item = i[0].split('/')
            most_similars.append({
                'main_role': item[0],
                'events': item[1],
                'opp_role': item[2],
                'sim': float(i[1])
            })

        return sorted(most_similars, key=lambda item: item['sim'])[0:num]


