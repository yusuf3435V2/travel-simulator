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
COPY lss_logo.png .
COPY Run_Simulations.py .


CMD ["streamlit", "run", "Run_Simulations.py"]
