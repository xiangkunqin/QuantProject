#  -*- coding: utf-8 -*-
from pymongo import MongoClient

# 指定数据库的连接，quant_01是数据库名
DB_CONN = MongoClient('mongodb://127.0.0.1:27017')['quant_01']
