import json

data = open('relation_code2type.csv', 'r', encoding='utf-8').read().strip('\n').split('\n')

trigger2score = {}
for row in data[1:]:
	row = row.split(',')
	trigger2score[row[0]] = row[3]

open('relation_code2type.json','w', encoding='utf-8').write(json.dumps(trigger2score, indent=4, ensure_ascii = False))