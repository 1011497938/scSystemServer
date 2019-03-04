from re import match

from xml.dom.minidom import parse
import xml.dom.minidom
from opencc import OpenCC 
import json

from .db_manager import dbManager as db
from .neo4j_manager import graph
from .common_function import levenshtein,t2s

class AddrManager(object):
    """docstring for AddrManager"""
    def __init__(self):
        self.id2addr = {}
        self.addr_id_set = set()
        self.addr_array = []

        self.place2xy = self.xyParser()
        self.place2xy_set = set(self.place2xy.keys())
        self.all2vec = None

        # 加载CBDB上的所有地址
        addr_data = graph.run('MATCH (n:Addr_codes) RETURN id(n), n').data()
        for data in addr_data:
            addr_node = data['n']
            self.createAddr(addr_node)

        addr_belong_data = graph.run('MATCH (n1:Addr_codes)-->(:Addr_belongs_data)-->(n2:Addr_codes) RETURN n1.c_addr_id as son_id, n2.c_addr_id as parent_id').data()

        for data in addr_belong_data:
            son_id = data['son_id']
            parent_id = data['parent_id']
            son = self.getAddr(son_id)
            parent = self.getAddr(parent_id)

            parent.addSon(son)
            son.addParent(parent)

        for addr in self.addr_array:
            if addr.x != 'None' and addr.x is not None:   #如果原先已有纪录
                xy = [int(value)/1000000 for value in [addr.x, addr.y]]
                # for value in [addr.x, addr.y]:
                    # if len(value)<9:
                    #     for time in range(9-len(value)):
                    #         value += '0'
                    # value = int(value)/1000000
                    # xy.append(value)
                if xy[0]>0:
                    while xy[0]>180:
                        xy[0] /= 10
                    while xy[0]<6:
                        xy[0] *= 10

                if xy[1]>0:
                    while xy[1]>90:
                        xy[1] /= 10
                    while xy[1]<6:
                        xy[1] *= 10

                # print( [addr.x, addr.y], xy)
            else:
                # xy = [-1,-1]
                xy = self._getXY(addr.name)

            # print(addr.name,xy)
            addr.x = xy[0]
            addr.y = xy[1]
        # 加载所有的地点关系的树形结构

        print('加载地址管理器')

    def selfDestory(self):
        for addr in self.addr_array:
            addr.selfDestory()
        self.id2addr = None
        self.addr_id_set = None
        self.addr_array = None
        self.place2xy = None
        self.place2xy_set = None
        self.all2vec = None

    def _getXY(self, place_name):
        place2xy = self.place2xy
        place2xy_set = self.place2xy_set
        if place_name in place2xy_set:
            xy = place2xy[place_name]
            if len(xy)==0:
                return [-1,-1]
            else:
                return xy
        alter_chars = ['市', '省', '区', '县', '市县', '地区']

        for char in alter_chars:
            if place_name.replace(char, '') in place2xy_set:
                xy = place2xy[place_name.replace(char, '')]
                if len(xy)==0:
                    return [-1,-1]
                else:
                    return xy
            if place_name+char in place2xy_set:
                xy = place2xy[place_name+char]
                if len(xy)==0:
                    return xy
        return [-1,-1]

        # 这一部分有问题 
        minDiffer = 100
        minPlace = ''
        for place_name2 in place2xy:
            diff = levenshtein(place_name, place_name2)
            # diff = lst.ratio(place_name, place_name2)
            if diff < minDiffer:
                minDiffer = diff
                minPlace = place_name2
                if minDiffer == 1:
                    break
        if minDiffer>1:
            return [-1,-1]
        # print(place_name, minPlace, minDiffer, place2xy[minPlace])
        return  place2xy[minPlace]

    # 加载经纬度
    def xyParser(self):
        # 使用minidom解析器打开 XML 文档
        DOMTree = xml.dom.minidom.parse("scSystemServer/data_model/data/Buddhist_Studies_Place_Authority.xml")
        collection = DOMTree.documentElement
        places = collection.getElementsByTagName("place")

        place2xy = {}

        for place in places:
            # print(place)
            # print("*****地址*****")

            # if place.hasAttribute("xml:id"):
            #     print("Title: " + place.getAttribute("xml:id"))
            place_names = place.getElementsByTagName('placeName')
            geo = place.getElementsByTagName('geo')
            if len(geo)!=0:
                geo = geo[0].childNodes[0].data.split(' ')
                geo = [float(elm) for elm in geo]
                for place_name in place_names:
                    if place_name.hasAttribute("xml:lang"):
                        if place_name.getAttribute("xml:lang")!='zho-Hant':
                            continue
                    for node in place_name.childNodes:
                        place_name = node.data
                        place_name = t2s(place_name)
                        # print(place_name)
                        place2xy[place_name] = geo    
            else:
                geo = [-1,-1]

        # open('./temp_data/place2xy.json', 'w', encoding='utf-8').write(json.dumps(place2xy, indent=4, ensure_ascii = False))
        return place2xy

    def createAddr(self, addr_node):
        addr_id = 'addr_' + addr_node['c_addr_id']
        if addr_id not in self.addr_id_set:
            self.id2addr[addr_id] = Addr(addr_node)
            self.addr_id_set.add(addr_id)
            self.addr_array.append(self.id2addr[addr_id])
        return self.id2addr[addr_id]

    # def getXY(self, addr):
    #     return []

    def getAddr(self, addr):
        if 'addr_' not in addr:
            addr = 'addr_' + addr
        # addr = str(addr).replace('addr_', '')
        # if match('[0-9]+', str(addr)):  #如果是'c_addr_id'
        if addr in self.addr_id_set:
            return self.id2addr[addr]
        print('ERROR:没有找到地址', addr)
        return None
        # 如果是名字,需要遍历

    def toDict(self):
        addrs = {str(addr.id):addr.toDict() for addr in self.addr_array }
        return addrs

    def toSongDict(self):
        has = set()
        left = set()
        for addr in self.addr_array:
            # print(addr.name)
            if addr.isSong():
                left.add(addr)

        # print(left)
        while len(left)!=0:
            addr = left.pop()
            has.add(addr)
            for son in addr.sons:
                if son not in has:
                    left.add(son)

            for parent in addr.parents:
                if parent not in has:
                    left.add(parent)
        # print(has)
        addrs = {str(addr.id):addr.toDict() for addr in list(has)}
        return addrs

class Addr(object):
    """docstring for Addr"""
    def __init__(self, addr_node):
        self.id = addr_node['c_addr_id']
        self.name = addr_node['c_name_chn']

        self.first_year = addr_node['c_firstyear']
        self.last_year = addr_node['c_lastyear']

        self.x = addr_node['x_coord']
        self.y = addr_node['y_coord']

        self.notes = addr_node['c_notes']
        self.alt_names = addr_node['c_alt_names']

        self.parents = []
        self.sons = []

        self.time_range = [-9999,9999]

        if self.first_year is not None and self.first_year!=0 and self.first_year!='0' and self.first_year!='None':
            year = int(self.first_year)
            self.time_range[0] = year
        else:
            self.first_year = self.time_range[0]
        if self.last_year is not None and self.last_year!=0 and self.last_year!='0' and self.last_year!='None':
            year = int(self.last_year)
            self.time_range[1] = year
        else:
            self.last_year = self.time_range[1]
        
    def isSong(self):
        return (self.name=='宋朝' or (self.first_year<800 and self.last_year>1300))

    def selfDestory(self):
        self.id = None
        self.name = None
        self.first_year = None
        self.last_year = None
        self.x = None
        self.y = None
        self.notes = None
        self.alt_names = None
        self.parents = None
        self.sons = None


    # 输入是否为他的父节点
    def isParent(self, addr):
        isParent = False
        for son in self.sons:
            if son == addr:
                print(str(self) + '是' + str(addr) + '父节点')
                return True
            isParent = son.isParent(addr)
            if isParent:
                return isParent
        return isParent

    def addSon(self, addr):
        if addr not in self.sons:
            self.sons.append(addr)

    def addParent(self, addr):
        if addr not in self.parents:
            self.parents.append(addr)

    def getParent(self):
        return self.parents

    def getSons(self):
        return self.sons

    def __str__(self):
        return '[(地点) id:{}, 地名:{}, x:{}, y:{}]'.format(str(self.id), str(self.name), str(self.x), str(self.y))

    def __hash__(self):
        return hash(str(self))
    
    def toDict(self):
        return {
            'id':self.id,
            'name':self.name,
            'first_year':self.first_year,
            'last_year':self.last_year,
            'x':self.x,
            'y':self.y,
            'alt_names':self.alt_names,
            # 'time_range': self.time_range,
            'parents': [addr.id for addr in self.parents],
            'sons': [addr.id for addr in self.sons],
            'vec': addrManager.all2vec.addr2vec[self.id].tolist()
        }

    # 宋朝地点会直接预加载
    def toHttpDict(self):
        if self.isSong():
            return {
                'id': self.id
            }            
        else:
            return self.toDict()


addrManager = AddrManager()


if __name__ == '__main__':
    print('地点模块测试')
    print(addrManager.id2addr)