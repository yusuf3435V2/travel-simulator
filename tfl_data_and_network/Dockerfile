FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/

RUN yum install -y gcc python3-devel
RUN pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}/

COPY api_utils.py ${LAMBDA_TASK_ROOT}/
COPY get_lines.py ${LAMBDA_TASK_ROOT}/
COPY get_travel_times.py ${LAMBDA_TASK_ROOT}/
COPY get_sequenced_stops.py ${LAMBDA_TASK_ROOT}/
COPY create_stations_network.py ${LAMBDA_TASK_ROOT}/

CMD ["create_stations_network.lambda_handler"]

# docker buildx build -t c23-travel_simulation_networkx_pipeline .

# docker run --env-file .env c23-travel_simulation_networkx_pipeline