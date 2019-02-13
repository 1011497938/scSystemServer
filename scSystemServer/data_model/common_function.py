# 存储了常用的一些函数
from opencc import OpenCC 
import numpy as np
import math

# 繁体转简体
cc = OpenCC('t2s')
print('加载繁体->简体转换器')
def t2s(string):
	return cc.convert(string)


# 计算编辑距离
def levenshtein(string1,string2):
    if len(string1) > len(string2):
        string1,string2 = string2,string1
    if len(string1) == 0:
        return len(string2)
    if len(string2) == 0:
        return len(string1)
    str1_length = len(string1) + 1
    str2_length = len(string2) + 1
    distance_matrix = [list(range(str2_length)) for x in range(str1_length)]
    #print distance_matrix
    for i in range(1,str1_length):
        for j in range(1,str2_length):
            deletion = distance_matrix[i-1][j] + 1
            insertion = distance_matrix[i][j-1] + 1
            substitution = distance_matrix[i-1][j-1]
            if string1[i-1] != string2[j-1]:
                substitution += 1
            # print(min(insertion,deletion,substitution))
            distance_matrix[i][j] = min(insertion,deletion,substitution)
    #print distance_matrix
    return distance_matrix[str1_length-1][str2_length-1]


def cos_dif(vector_a, vector_b):
    vector_a = np.mat(vector_a)
    vector_b = np.mat(vector_b)
    num = float(vector_a * vector_b.T)
    denom = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    cos = num / denom
    sim = 0.5 + 0.5 * cos
    # print('sim'+ str(sim))
    return sim

def dist_dif(vector_a, vector_b):
	return np.linalg.norm(np.mat(vector_a) - np.mat(vector_b))