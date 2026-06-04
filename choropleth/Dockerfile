FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/

RUN pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}/

COPY choropleth_pipeline.py ${LAMBDA_TASK_ROOT}/
COPY boundaryData.geojson ${LAMBDA_TASK_ROOT}/

CMD ["choropleth_pipeline.lambda_handler"]

# docker buildx build -t c23-travel_simulation_choropleth_pipeline .

# docker run --env-file .env c23-travel_simulation_choropleth_pipeline