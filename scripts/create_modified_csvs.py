import dataset_references as ref
import calculate_stats as calc
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


community_df['End Date'] = community_df['End Date'].fillna(pd.Timestamp.today().date())

community_df['Start Date'] = pd.to_datetime(community_df['Start Date'])
community_df['End Date'] = pd.to_datetime(community_df['End Date'])

#makes new column for contributed tim
community_df['Contributed_Time'] = (community_df['End Date'].dt.to_period('M').astype(int)- community_df['Start Date'].dt.to_period('M').astype(int))

    # place in time buckets
bins = [0, 3, 6, 7, 12,10000]

    # Create a new column for the buckets
community_df['time_bucket'] = pd.cut(community_df['Contributed_Time'], bins)
print(community_df['time_bucket'].value_counts())


