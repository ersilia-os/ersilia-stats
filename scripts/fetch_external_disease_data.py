import os
import pandas as pd

# Directory for storing external data
DATA_DIR = "external-data"
os.makedirs(DATA_DIR, exist_ok=True)

# OWID datasets
owid_datasets = {
    "alzheimers-deaths.csv": "https://ourworldindata.org/grapher/death-rate-from-alzheimers-other-dementias-ghe.csv?v=1&csvType=full&useColumnShortNames=true",
    "meningitis-deaths.csv": "https://ourworldindata.org/grapher/death-rate-from-meningitis-who.csv?v=1&csvType=full&useColumnShortNames=true",
    "pneumonia-deaths.csv": "https://ourworldindata.org/grapher/death-rate-from-pneumonia-ghe.csv?v=1&csvType=full&useColumnShortNames=true",
    "hivaids-deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-hivaids-who.csv?v=1&csvType=full&useColumnShortNames=true",
    "cardiovascular-deaths.csv": "https://ourworldindata.org/grapher/death-rate-from-cardiovascular-disease-ghe.csv?v=1&csvType=full&useColumnShortNames=true",
    "tuberculosis-deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-tuberculosis-ghe.csv?v=1&csvType=full&useColumnShortNames=true",
    "life-expectancy-vs-health-expenditure.csv": "https://ourworldindata.org/grapher/life-expectancy-vs-health-expenditure.csv?v=1&csvType=full&useColumnShortNames=true",
    "community-health-workers.csv": "https://ourworldindata.org/grapher/community-health-workers.csv?v=1&csvType=full&useColumnShortNames=true",
    "covid-cases-and-deaths.csv": "https://ourworldindata.org/grapher/cumulative-deaths-and-cases-covid-19.csv?v=1&csvType=full&useColumnShortNames=true",
    "malaria-deaths.csv": "https://ourworldindata.org/grapher/number-of-deaths-from-malaria-who.csv?v=1&csvType=full&useColumnShortNames=true",
    "hivaids-deaths.csv": "https://ourworldindata.org/grapher/deaths-from-aids-un.csv?v=1&csvType=full&useColumnShortNames=true",
    "world-population.csv": "https://ourworldindata.org/grapher/population.csv?v=1&csvType=full&useColumnShortNames=true"
}

# Function to fetch OWID datasets
def fetch_owid_data(file_name, url):
    try:
        print(f"Fetching OWID dataset: {file_name}")
        df = pd.read_csv(url, storage_options={"User-Agent": "OWID Data Fetch/1.0"})
        output_path = os.path.join(DATA_DIR, file_name)
        df.to_csv(output_path, index=False)
        print(f"Saved OWID dataset: {file_name}")
    except Exception as e:
        print(f"Error fetching {file_name}: {e}")

# Main function to download all datasets
def main():
    for file_name, url in owid_datasets.items():
        fetch_owid_data(file_name, url)

if __name__ == "__main__":
    main()
