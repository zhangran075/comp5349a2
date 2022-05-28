spark-submit \
    --master yarn \
    --deploy-mode client \
    test_new.py \
    --output $1
