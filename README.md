# scSystemServer
宋词可视化后端

## 步骤：

### 安装包
>pip install -r requirement.txt

### 下载数据文件
从我的百度盘上下载下面几个文件，并且放到正确的位置

1. CBDB_aw_20180831_sqlite.db放在 scSystemServer/scSystemServer/data_model/data/db
中

2. model文件中三个文件都放到scSystemServer\scSystemServer\data_model\temp_data 中(temp_data文件夹需要创建一下)

3. graph.db.dump 文件：先下载安装neo4j，桌面版的就好了，创建一个数据库，在数据的bin文件目录中加载数据库
>neo4j-admin load --from=F:/graph.db.dump --database=graph.db --force 

### 开启
1. 开启neo4j中的数据库
2. 运行
>python manage.py runserver 0.0.0.0:8000
