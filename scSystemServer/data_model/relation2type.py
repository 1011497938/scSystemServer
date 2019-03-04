from .db_manager import dbManager as db
import json

assoc_codes_fields = db.getTableKeys('assoc_codes')
assoc_type_rel_fields = db.getTableKeys('assoc_code_type_rel')
assoc_type_fields = db.getTableKeys('assoc_types')

assoc_codes = db.runSelect('SELECT {} from assoc_codes'.format(','.join(assoc_codes_fields)))
assoc_type_rel = db.runSelect('SELECT {} from assoc_code_type_rel'.format(','.join(assoc_type_rel_fields)))
assoc_type = db.runSelect('SELECT {} from assoc_types'.format(', '.join(assoc_type_fields)))

temp = {}
for row in assoc_codes:
	temp[row[0]] = db.row2Obj(assoc_codes_fields, row)
assoc_codes = temp

temp = {}
for row in assoc_type_rel:
	temp[row[0]] = row[1]
	# temp.append(db.row2Obj(assoc_type_rel_fields, row))
assoc_type_rel = temp

temp = {}
# parentid2type = {}
for row in assoc_type:
	temp[row[0]] = db.row2Obj(assoc_type_fields, row)
	# parentid2type[row[3]] = db.row2Obj(assoc_type_fields, row)
assoc_type = temp


code2rel = {}
for assoc_id in assoc_codes.keys():
	assoc_code = assoc_codes[assoc_id]
	code_name = assoc_code['c_assoc_desc_chn']

	# pair = assoc_code['c_assoc_pair']
	# pair = assoc_code[pair]['c_assoc_desc_chn']
	# print(pair)
	# if pair in :
	# 	pass

	if assoc_code['c_assoc_code'] not in assoc_type_rel.keys():
		code2rel[code_name] = {
			'type': '未知',
			'parent_type': '未知'
		}
		continue
	
	# assoc_type_rel[assoc_code['c_assoc_code']]
	type = assoc_type[assoc_type_rel[assoc_code['c_assoc_code']]]
	parent_type = assoc_type[type['c_assoc_type_parent_id']]
	code2rel[code_name] = {
		'type': type['c_assoc_type_desc_chn'],
		'parent_type': parent_type['c_assoc_type_desc_chn'].replace('关系类', '')
	}

code2rel['升职'] = {
	'type': '职务变迁',
	'parent_type': '政治' 
}

code2rel['就任'] = {
	'type': '职务变迁',
	'parent_type': '政治'
}

addr_codes = db.runSelect('SELECT * from biog_addr_codes')
for addr_code in addr_codes:
	addr_type = addr_code[2]
	code2rel[addr_type] = {
		'type' : '迁徙',
		'parent_type': '迁徙'
	}

entry_codes = db.runSelect('SELECT * from entry_codes')
for entry_code in entry_codes:
	entry_type = entry_code[2]
	code2rel[entry_type] = {
		'type': '入仕',
		'parent_type': '政治'
	}


# open('scSystemServer/data_model/temp_data/relation_code2type.json', 'w', encoding='utf-8').write(json.dumps(code2rel, indent=5, ensure_ascii = False) )

data = open('scSystemServer/data_model/data/relation_code2type.csv', 'r', encoding='utf-8').read().strip('\n').split('\n')
trigger2score = {}
for row in data[1:]:
	row = row.split(',')
	name = row[0].replace('||',',')
	trigger2score[name] = {
		'type': code2rel[name]['type'],
		'parent_type': code2rel[name]['parent_type'],
		'score': int(row[3])
	}
# open('scSystemServer/data_model/data/relation_code2type.json','w', encoding='utf-8').write(json.dumps(trigger2score, indent=4, ensure_ascii = False))


# fs = open('scSystemServer/data_model/temp_data/relation_code2type.csv', 'w', encoding='utf-8')
# fs.write('事件,类型,总类,评价,注释\n')
# for elm in code2rel.keys():
# 	fs.write('{},{},{},,\n'.format(elm.replace(',','||'), code2rel[elm]['type'], code2rel[elm]['parent_type'] ))

# print(code2rel)

# 找到成对的关系
# assoc_code_pairs = []

def getRelTypes(relation):
	if relation in code2rel.keys():
		return code2rel[relation]
	return '未知'


def getEventScore(event):
	relation = event.trigger.name
	if relation in trigger2score.keys():
		return trigger2score[relation]['score']
	return 0