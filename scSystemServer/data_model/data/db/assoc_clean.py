import sqlite3
import re
from opencc import OpenCC 
import json

cc = OpenCC('t2s')
print('加载繁体->简体转换器')
def t2s(string):
	return cc.convert(string)

conn = sqlite3.connect(r'./CBDB_aw_20180831_sqlite.db')
c = conn.cursor()

id2assoc_code = {}
rows = c.execute('SELECT c_assoc_code, c_assoc_desc_chn from assoc_codes')
for row in rows:
	id2assoc_code[row[0]] = re.sub("[\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+", '', t2s(row[1]))
	# print(row)

print(id2assoc_code[1])
rows = c.execute('SELECT c_assoc_code, c_assoc_pair from assoc_codes')
id_pair_set = set()
for row in rows:
	row = [int(column) for column in row if column is not None]
	row = sorted(row) 
	id_pair_set.add(','.join([str(column) for column in row]))

fs = open('./关系对.csv', 'w', encoding='utf-8')
for pair_text in id_pair_set:
	print(pair_text)
	pairs =pair_text.split(',')
	assoc_codes = [id2assoc_code[int(assoc_id)] for assoc_id in pairs]

	if len(assoc_codes[0])<len(assoc_codes[1]):
		main_index = 0
	else:
		main_index = 1
	fs.write(pair_text + ',' + str(main_index) + ',' + ','.join(assoc_codes) + '\n')
	 # 
fs.close()