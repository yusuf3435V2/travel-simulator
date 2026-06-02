FROM python:latest

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY coverage_context.py .
COPY analysis.py .
COPY kml_export.py .
COPY pages/ pages/
COPY stations_choropleth.py .
COPY folium_functions.py .
COPY s3_utils.py .
COPY df_analysis.py .
COPY dashboard.py .


CMD ["streamlit", "run", "dashboard.py"]


# docker buildx build -t c23-travel_simulation_dashboard . 

# docker run -p 8501:8501 --env-file .env c23-travel_simulation_dashboard