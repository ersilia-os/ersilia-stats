# Disease data from our world in data api
import pandas as pd
import requests
import os

# Function to download and process data
def process_data(url, metadata_url, output_file_name):
    df = pd.read_csv(url, storage_options={'User-Agent': 'Our World In Data data fetch/1.0'})

    # Fetch metadata
    metadata = requests.get(metadata_url).json()

    # Rename columns for consistency
    df.rename(columns={
        df.columns[0]: 'Entity',  
        df.columns[1]: 'Code',  
        df.columns[2]: 'Year',   
        df.columns[3]: 'Deaths'   # rate or number
    }, inplace=True)

    # Get the maximum year for each country
    max_years = df.groupby('Entity')['Year'].max()

    # Filter to keep rows where the year is the maximum for each country
    df = df[df.set_index(['Entity', 'Year']).index.isin(list(max_years.items()))]

    data_dir = 'external-data'
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    output_path = os.path.join(data_dir, output_file_name)
    df.to_csv(output_path, index=False)

    print(f"Saved data to {output_path}")


# Alzheimer's data
alzheimers_url = "https://ourworldindata.org/grapher/death-rate-from-alzheimers-other-dementias-ghe.csv?v=1&csvType=full&useColumnShortNames=true"
alzheimers_metadata_url = "https://ourworldindata.org/grapher/death-rate-from-alzheimers-other-dementias-ghe.metadata.json?v=1&csvType=full&useColumnShortNames=true"
process_data(alzheimers_url, alzheimers_metadata_url, 'alzheimers-deaths.csv')

# Meningitis data
meningitis_url = "https://ourworldindata.org/grapher/death-rate-from-meningitis-who.csv?v=1&csvType=full&useColumnShortNames=true"
meningitis_metadata_url = "https://ourworldindata.org/grapher/death-rate-from-meningitis-who.metadata.json?v=1&csvType=full&useColumnShortNames=true"
process_data(meningitis_url, meningitis_metadata_url, 'meningitis-deaths.csv')

# Pneumonia data
pneumonia_url = "https://ourworldindata.org/grapher/death-rate-from-pneumonia-ghe.csv?v=1&csvType=full&useColumnShortNames=true"
pneumonia_metadata_url = "https://ourworldindata.org/grapher/death-rate-from-pneumonia-ghe.metadata.json?v=1&csvType=full&useColumnShortNames=true"
process_data(pneumonia_url, pneumonia_metadata_url, 'pneumonia-deaths.csv')

# HIV/AIDS data
hivaids_url = "https://ourworldindata.org/grapher/number-of-deaths-from-hivaids-who.csv?v=1&csvType=full&useColumnShortNames=true"
hivaids_metadata_url = "https://ourworldindata.org/grapher/number-of-deaths-from-hivaids-who.metadata.json?v=1&csvType=full&useColumnShortNames=true"
process_data(hivaids_url, hivaids_metadata_url, 'hivaids-deaths.csv')

# Cardiovascular disease data
cardiovascular_url = "https://ourworldindata.org/grapher/death-rate-from-cardiovascular-disease-ghe.csv?v=1&csvType=full&useColumnShortNames=true"
cardiovascular_metadata_url = "https://ourworldindata.org/grapher/death-rate-from-cardiovascular-disease-ghe.metadata.json?v=1&csvType=full&useColumnShortNames=true"
process_data(cardiovascular_url, cardiovascular_metadata_url, 'cardiovascular-deaths.csv')

# Tuberculosis data
tuberculosis_url = "https://ourworldindata.org/grapher/number-of-deaths-from-tuberculosis-ghe.csv?v=1&csvType=full&useColumnShortNames=true"
tuberculosis_metadata_url = "https://ourworldindata.org/grapher/number-of-deaths-from-tuberculosis-ghe.metadata.json?v=1&csvType=full&useColumnShortNames=true"
process_data(tuberculosis_url, tuberculosis_metadata_url, 'tuberculosis-deaths.csv')
