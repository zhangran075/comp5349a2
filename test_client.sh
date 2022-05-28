spark-submit \
    --master yarn \
    --deploy-mode client \
    test_.py \
    --output $1
