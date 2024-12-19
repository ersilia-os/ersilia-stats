# OpenAlex API fetch 
import requests
import pandas as pd
import os

API_BASE_URL = "https://api.openalex.org/"

# Authors listed in data/publications.csv
authors_set = {
    "Miquel Duran-Frigola", "Lydia Siragusa", "Eytan Ruppin", "Xavier Barril", "Gabriele Cruciani", "Patrick Aloy",
    "Adrià Fernández-Torras", "Quique Bassat", "Gemma Moncunill", "Anja Scholzen", "Maximillian Mpina", "Augusto Nhabomba",
    "Aurore Bouyoukou Hounkpatin", "Lourdes Osaba", "Raquel Valls", "Joseph J Campo", "Hèctor Sanz", "Chenjerai Jairoce",
    "Nana Aba Williams", "Jake M Pry", "Albert Manasyan", "Sharon Kapambwe", "Katayoun Taghavi", "Mulindi Mwanahamuntu",
    "Izukanji Sikazwe", "Jane Matambo", "Jack Mubita", "Kennedy Lishimpi", "Kennedy Malama", "Carolyn Bolton Moore",
    "David Rossell", "Ashleigh van Heerden", "Gemma Turon", "Nelisha Pillay", "Lyn-Marié Birkholtz", "Fidele Ntie-Kang",
    "Erez Persi", "Mehdi Damaghi", "William R Roush", "John L Cleveland", "Robert J Gillies", "Francesco Raimondi",
    "Pierluigi Di Chiaro", "Mariangela Morelli", "Chakit Arora", "Luisa Bisceglia", "Natalia De Oliveira Rosa",
    "Alice Cortesi", "Sara Franceschi", "Francesca Lessi", "Anna Luisa Di Stefano", "Orazio Raimondi", "Michael J. Vinikoor",
    "Monika Roy", "Aaloke Mody", "Anjali Sharma", "Belinda Chihota", "Harriet Daultrey", "Jacob Mutale", "Andrew D. Kerkhoff",
    "Martino Bertoni", "Pau Badia-i-Mompel", "Eduardo Pauls", "Modesto Orozco-Ruiz", "Oriol Guitart-Pla", "Víctor Alcalde",
    "Víctor M Diaz", "Antoni Berenguer-Llergo", "Isabelle Brun-Heath", "Núria Villegas", "Marko Cigler", "Georg Winter",
    "Teresa Juan-Blanco", "Martina Locatelli", "Takaomi C Saido", "Takashi Saito", "Camille Stephan-Otto Attolini",
    "Marina Gay", "Eliandre de Oliveira", "Fabian Offensperger", "Gary Tin", "Jürgen Bajorath", "Ana L. Chávez-Hernández",
    "Eli Fernández-de Gortari", "Johann Gasteiger", "Edgar López-López", "José L. Medina-Franco", "Oscar Méndez-Lucio",
    "Jordi Mestres", "Adria Fernandez-Torras", "Arnau Comajuncosa-Creus", "Helene J Smith", "Theodora Savory",
    "Michael E Herce", "Mathew Njoroge", "Mwila Mulubwa", "Kelly Chibale", "Albert Gris-Oliver", "Marta Palafox",
    "Maurizio Scaltriti", "Pedram Razavi", "Sarat Chandarlapaty", "Joaquin Arribas", "Meritxell Bellet", "Violeta Serra",
    "Eugene F Douglass", "Robert J Allaway", "Bence Szalai", "Wenyu Wang", "Tingzhong Tian", "Ron Realubit", "Charles Karan",
    "Shuyu Zheng", "Alberto Pessia", "Ziaurrehman Tanoli", "Mohieddin Jafari", "Catalina Tovar Acero", "Javier Ramírez-Montoya",
    "María Camila Velasco", "Paula Avilés", "Dina Ricardo-Caldera", "Gustavo Quintero", "Myriam Elena Cantero",
    "Juan Rivera-Correa", "Ana Rodriguez", "David Amat", "Dhanshree Arora", "Roi Blanco", "Víctor Martínez", "Carles Pons",
    "Núria Villegas", "Adrià Fernández-Torras", "Roberto Mosca", "Edwin Tse", "Xin Qiu", "Matthew Todd", "Jude Y. Betow",
    "Clovis S. Metuge", "Simeon Akame", "Vanessa A. Shu", "Oyere T. Ebob"
}

def get_author_data(search_name):
    url = f"{API_BASE_URL}authors?search={search_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['results']
    return []

def fetch_and_structure_data():
    institutions_data = []
    authors_data = []

    for author_name in authors_set:
        author_data = get_author_data(author_name)
        for author in author_data:
            author_info = {
                'author_id': author['id'],
                'author_name': author['display_name'],
                'works_count': author['works_count'],
                'cited_by_count': author['cited_by_count'],
                'summary_stats_2yr_mean_citedness': author['summary_stats']['2yr_mean_citedness'] if 'summary_stats' in author else None,
            }
            authors_data.append(author_info)

            for affiliation in author.get('affiliations', []):
                institution = affiliation.get('institution', {})
                institution_info = {
                    'author_id': author['id'],
                    'institution_display_name': institution.get('display_name'),
                    'institution_country_code': institution.get('country_code'),
                    'institution_ror': institution.get('ror'),
                    'affiliation_years': affiliation.get('years')
                }
                institutions_data.append(institution_info)

            for last_institution in author.get('last_known_institutions', []):
                last_institution_info = {
                    'author_id': author['id'],
                    'institution_display_name': last_institution.get('display_name'),
                    'institution_country_code': last_institution.get('country_code'),
                    'institution_ror': last_institution.get('ror')
                }
                institutions_data.append(last_institution_info)
    
    return pd.DataFrame(authors_data), pd.DataFrame(institutions_data)

authors_df, institutions_df = fetch_and_structure_data()

data_dir = 'external-data'
if not os.path.isdir(data_dir):
    os.makedirs(data_dir)

authors_outpath = os.path.join(data_dir, 'ersilia_authors.csv')
authors_df.to_csv(authors_outpath, index=False)

institutions_outpath = os.path.join(data_dir, 'ersilia_institutions.csv')
institutions_df.to_csv(institutions_outpath, index=False)

print(f"Saved authors data to {authors_outpath}")
print(f"Saved institutions data to {institutions_outpath}")
