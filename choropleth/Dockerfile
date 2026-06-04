FROM public.ecr.aws/lambda/python:3.11

# Install build dependencies - need both gcc and g++ for packages like contourpy
RUN yum install -y gcc gcc-c++ python3-devel

COPY requirements.txt ${LAMBDA_TASK_ROOT}/

RUN pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}/

COPY choropleth_pipline.py ${LAMBDA_TASK_ROOT}/
COPY boundaryData.geojson ${LAMBDA_TASK_ROOT}/

CMD ["choropleth_pipeline.lambda_handler"]