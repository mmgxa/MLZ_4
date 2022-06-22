FROM agrigorev/zoomcamp-model:mlops-3.9.7-slim

RUN pip install -U pip
RUN pip install -U scikit-learn==1.0.2
RUN pip install -U pandas
RUN pip install -U pyarrow fastparquet

RUN apt-get update -y \
 && apt-get install -y wget

COPY ["starter6_l.py", "./"]


ENTRYPOINT [ "python", "starter6_l.py", "--year", "2021", "--month",  "4" ]
