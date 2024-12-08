import pandas as pd
import numpy as np
import csv

#Calculating number of publications per month
def pubs_per_month():
    df = pd.read_csv("data/Publications.csv")
    print(df.head)

def main():
    pubs_per_month()

main()