spark-submit \
    --master yarn \
    --deploy-mode client \
    test.py \
    --output $1
