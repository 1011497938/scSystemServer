import sqlite3
import re
from opencc import OpenCC 
# from py2neo import Graph,Node,Relationship,cypher
import json
from .common_function import t2s

class DbManager(object):
	"""docstring for DbManager"""
	def __init__(self):
		conn = sqlite3.connect(r'scSystemServer/data_model/data/db/CBDB_aw_20180831_sqlite.db')
		print("Opened database successfully")
		self.c = conn.cursor()

		self.year2range = json.loads(open(r'scSystemServer/data_model/data/db/db_info/year2range.json', 'r', encoding='utf-8').read())

		self.foreign_key = json.loads(open(r'scSystemServer/data_model/data/db/db_info/foreignkey5.json', 'r', encoding='utf-8').read())
		# print(self.foreign_key)

		# 加载所有键值名
		ignore_fields = ['check','c_created_by', 'c_self_bio', 'c_created_date', 'c_modified_by', 'c_modified_date','c_db_contact person']
		
		self.table2fields = {}
		# 获取表名
		cur = conn.cursor()   
		cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
		tables = cur.fetchall()                     # Tables 为元组列表
		# print(tables)
		tables = [table[0] for table in tables]
		for table_name  in tables:
		    cur.execute("SELECT * FROM {}".format(table_name))
		    col_name_list = [column[0] for column in cur.description if column[0] not in ignore_fields and  ' ' not in  column[0]]
		    if len(col_name_list)>0:
		        self.table2fields[table_name] = col_name_list

		self._t2s_dict = {}

	# 	self.event_db =  sqlite3.connect('db/event_db.db')
	# 	print("打开事件数据库")


	# def insertEvent(self, event):
	# 	return


	def runSelect(self, query):
		rows = self.c.execute(query)
		new_rows = []
		for row in rows:
			new_row = []
			for column in row:
				# print(column)
				if  re.match('[0-9]+',str(column)):
					new_row.append(column)
				else:
					new_row.append(self.t2s(str(column)))
			new_rows.append(new_row)
		return new_rows


	def t2s(self,text):
		if  re.match('-{0,1}[0-9]+',str(text)):
			return text
		else:
			return t2s(str(text))
		

		if len(text)<5:
			if text in self._t2s_dict.keys():
				return self._t2s_dict[text]
			else:
				new_text = t2s(text)
				self._t2s_dict[text] = new_text
				# print(len(self._t2s_dict.keys()))
				return new_text
		else:
			return self.cc.convert(text)

	# 转换数据库为简体,还是有问题的
	def updateSqlite2s(self):
		def row2Obj(fields, row):
			index = 0
			new_object = {}
			for field in fields:
				string = str(row[index]) 
				if not re.match('-{0,1}[0-9]+', string) and string!='None' and string!=None:
					print(row[index], str(row[index]) )
					row[index] = "'" + row[index] + "'"
				new_object[field] = row[index]
				index += 1
			return new_object
		table2fields = self.table2fields
		for table in table2fields:
			fields = table2fields[table]
			query = 'SELECT {} FROM {}'.format(','.join(fields), table)
			rows = self.c.execute(query)
			for row in rows:
				t_columns = row
				s_columns = [self.t2s(column) for column in t_columns]

				t_object = row2Obj(fields, t_columns)
				s_object = row2Obj(fields, s_columns)

				set_part = ','.join([ field+'='+ str(s_object[field]) for field in fields if str(s_object[field])!=''])
				where_part = ' AND '.join([ field+'='+str(t_object[field]) for field in fields if str(t_object[field])!=''])
				query = 'UPDATE {} SET {} WHERE {}'.format( table, set_part, where_part )
				print(query)
				self.c.execute(query)

	def row2Obj(self, fields, row):
		index = 0
		new_object = {}
		for field in fields:
			new_object[field] = row[index]
			index += 1
		return new_object

	def getRelatedTable(self,table):
		related_table = []
		for key in self.foreign_key.keys():
		    elm = self.foreign_key[key]

		    table1 = elm['table1']
		    key1 = elm['key']
		    table2 = elm['table2']
		    key2 = elm['foreignkey']

		    if table1 == table:
		    	related_table.append({ 'table1':table1, 'key1':key1, 'table2':table2, 'key2':key2, 'name':elm['name'] })
		    elif table2 == table:
		    	related_table.append({ 'table1':table2, 'key1':key2, 'table2':table1, 'key2':key1, 'name':elm['name'] })  

		return related_table

	def  is_Valid(self, table, value):
		return True

	def getTableKeys(self, table):
		if table in self.table2fields.keys():
			return self.table2fields[table]
		else:
			return []



dbManager = DbManager()

if __name__ == '__main__':
	print('测试数据库管理模块')
	db = dbManager
	# db.updateSqlite2s()

	# print( json.dumps({'data':db.getRelatedTable('biog_main')}, indent=4, ensure_ascii = False))


