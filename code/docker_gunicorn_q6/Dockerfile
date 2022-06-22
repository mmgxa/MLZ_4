FROM agrigorev/zoomcamp-model:mlops-3.9.7-slim

RUN pip install -U pip
RUN pip install -U flask gunicorn scikit-learn==1.0.2

COPY ["starter6.py", "./"]

EXPOSE 9696

ENTRYPOINT [ "gunicorn", "--bind=0.0.0.0:9696", "starter6:app", "--timeout", "2000" ]

