import pandas as pd
from ast import literal_eval

blogposts_df = pd.read_csv('data/Blogposts.csv')
community_df = pd.read_csv('data/Community.csv')
countries_df = pd.read_csv('data/Countries.csv')
events_df = pd.read_csv('data/Events.csv')
models_df = pd.read_csv('data/Models.csv')
organisations_df = pd.read_csv('data/Organisations.csv')
publications_df = pd.read_csv('data/Publications.csv')
external_titles_df = pd.read_csv('external-data/titles_results.csv')
external_authors_df = pd.read_csv('external-data/authors_results.csv')



topics = ['source', 'infectious', 'AI ', 'global', 'malaria'] #list of topics, can change if needed

topic_counts = {
    topic: (
        blogposts_df['Title'].str.contains(topic, case=False, na=False) |
        blogposts_df['Intro'].str.contains(topic, case=False, na=False)
    ).sum()
    for topic in topics
}
topic_counts_series = pd.Series(topic_counts).sort_values(ascending=False)

print(topic_counts_series)

