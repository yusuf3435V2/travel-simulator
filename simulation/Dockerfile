FROM public.ecr.aws/lambda/python:latest


# install dependencies
COPY ../requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# Copy function code
COPY collect_passengers.py ${LAMBDA_TASK_ROOT}
COPY distance_maths.py ${LAMBDA_TASK_ROOT}
COPY run_sim_and_save.py ${LAMBDA_TASK_ROOT}
COPY result_analysis.py ${LAMBDA_TASK_ROOT}
COPY s3_utils_sim.py ${LAMBDA_TASK_ROOT}
COPY collect_passengers.py ${LAMBDA_TASK_ROOT}





# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)

CMD ["run_sim_and_save.lambda_handler"]