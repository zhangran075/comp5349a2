# -*- coding: utf-8 -*-
"""comp5349_a2_500615485_testdata.ipynb
Automatically generated by Colaboratory.
Original file is located at
    https://colab.research.google.com/drive/1aTPbt2QZJJ8NJZJg1T8eto9XIuqig13j
### Introduction
This notebook demonstrates a few useful methods for loading json file and for handling nested json objects. The example file is `test.json` in assignment 2.
"""



from pyspark.sql import SparkSession
spark = SparkSession \
    .builder \
    .appName("COMP5349 A2 Data Loading Example") \
    .getOrCreate()

"""### Load Json file as data frame"""

data = "s3://comp5349ranzhang/train_separate_questions.json"
init_df = spark.read.json(data)

# The original file will be loaded into a data frame with one row and two columns
init_df.show(1)

"""### Check the schema of a data frame
`printSchema` is a useful method to display the schema of a data frame
"""

init_df.printSchema()

"""### `select` and `explode`
The [`select`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.DataFrame.select.html) method is used to select one or more columns for the source dataframe. 
The [`explode`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.functions.explode.html) method is used to expand an array into multiple rows. The [`alias`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.Column.alias.html) method is used to specify a name for column storing the array element.
"""

from pyspark.sql.functions import explode
data_df= init_df.select((explode("data").alias('data')))

data_df.printSchema()

from pyspark.sql.functions import explode
data_df= init_df.select((explode("data").alias('data')))

data_df.printSchema()

#import lib 
from pyspark.sql.functions import explode
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql import Window, Row

"""take out the paragraph as new dataframe"""

data_df = data_df.select(explode("data.paragraphs").alias("paragraph"))
data_df.show(5)

"""take out the context and qas as new dataframe"""

data_df = data_df.select(col("paragraph.context").alias("paragraph_context"),explode("paragraph.qas").alias('qas'))
data_df.show(5)

"""flat the element in qas and combine with context"""

data_df = data_df.select(col("paragraph_context"),
col("qas.question").alias("qas_question"),
col("qas.is_impossible").alias("qas_is_impossible"),explode_outer("qas.answers").alias('answers'),
)
data_df.show(5)

"""flat element in answers and combine before column"""

data_df = data_df.select(col("paragraph_context"),
  col("answers.text").alias("answer_text"),
  col("answers.answer_start").alias("answer_start"),
  col("qas_is_impossible"),
  col("qas_question")
)
data_df.show(5)

#total number of test contracts are 102
total_num = data_df.count()

# convert the df into rdd
qas_context_rdd = data_df.rdd
qas_context_rdd.take(1)

#convert format from row to list
qas_context_rdd_li= qas_context_rdd.map(list)
qas_context_rdd_li.take(5)

#calculate the answer_end 

def cal_answer_end(input):
  res = []
  print(input[3])
  if input[3] is True:
    res.append([input[0],input[4],[0,0],0])
    
  else: 
    _start = input[2]
    text_len = len(input[1])
    _end = _start + text_len
    res.append([input[0],input[4],[_start,_end],1])
  
  return res

#get the answer_end to the rdd
qas_context_rdd_li= qas_context_rdd_li.flatMap(cal_answer_end)
qas_context_rdd_li.take(5)

# Creates segments for all contracts

def segment_context(input):
  res = []
  seg_res = []
  context_len = len(input[0])
  _start = 0
  _end = 4096
  while _start < context_len:
        if _end > context_len:
            _end = context_len
        seg_res.append([input[0][_start:_end], _start, _end])
        _start = _start + 2048
        _end = _end + 2048
  res.append(seg_res)
  res.append(input[1])
  res.append(input[2])
  res.append(input[3])
  return res

qas_context_rdd_li = qas_context_rdd_li.map(segment_context)
qas_context_rdd_li.take(2)

#count the number of possible nagetive samples
def count_po (input):
  if input[3] != 0:
    return [input[1],1]
  else:
    return [input[1],0]


count_po_rdd_li = qas_context_rdd_li.map(count_po)
count_po_rdd_li = count_po_rdd_li.reduceByKey(lambda a,b: a+b)
count_po_rdd_li.take(5)

#convert into dic
count_po_dict = count_po_rdd_li.collectAsMap()
count_po_dict

#slect the sample according to the negative samples(impossible negative&possible negative)

def sample_selection_ (input):
  res = []
  negative = 0

  #Creates impossible negative samples for all questions without answers in all contracts
  if input[3] == 0:
    try:
      impo_negative = int(total_num/count_po_dict[input[1]])
      negative = impo_negative
      for i in range(negative):
        res.append([input[0][i][0],input[1],0,0])
    except:
      negative = 0  
    
  #Creates positive samples for all questions with possible answers in all contracts
  else:
    negative = input[3]
    seg_len = len(input[0])
    negative_li = list(range(seg_len))

    # select the positive sample
    for j in range(len(input[0])):
        if input[2][0] in range(input[0][j][1],input[0][j][2]):
          if input[2][1] in range(input[0][j][1],input[0][j][2]):
            res.append([input[0][j][0],input[1],input[2][0]-input[0][j][1],input[2][1]-input[0][j][1]])
          else:
            res.append([input[0][j][0],input[1],input[2][0]-input[0][j][1],4096])
        else:
          if input[2][1] in range(input[0][j][1],input[0][j][2]):
            res.append([input[0][j][0],input[1],0,input[2][1]-input[0][j][1]]) 
          else:
            pass

    #Creates possible negative samples for all questions with possible answers in all contracts
    if len(negative_li) > 0:
      if negative < len(negative_li):
        for i in range(negative):         
          res.append([input[0][i][0],input[1],0,0])   
      elif negative >= len(negative_li):
        for i in range(len(negative_li)):
          res.append([input[0][i][0],input[1],0,0])
      else:
        for i in range(negative):
          res.append([input[0][i][0],input[1],0,0])  
    else:
      pass
  return res

qas_context_rdd_li.take(1)

#result
final_result = qas_context_rdd_li.flatMap(sample_selection_)

final_result.collect()

#create dataframe for the final result
result_df = spark.createDataFrame(final_result,['source', 'question', 'answer_start', 'answer_end'])
result_df.printSchema()

#transfer into Jason file
result_df.write.json('F_result_train.json')
