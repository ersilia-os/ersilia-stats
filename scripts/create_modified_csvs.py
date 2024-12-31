import dataset_references as ref
import calculate_stats as calc
import pandas as pd
from ast import literal_eval

other_community = ref.community_df
print(ref.community_df['Role'])

print(other_community['Role'])

other_community['Role'] = ref.community_df['Role'].apply(literal_eval)
other_community = other_community.explode('Role')

print(other_community['Role'])
print(other_community['Role'].value_counts())

