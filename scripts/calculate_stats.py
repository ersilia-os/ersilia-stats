import argparse
import pandas as pd

def sum_columns(df, columns):
    return df[columns].apply(pd.to_numeric, errors='coerce').sum()

def count_columns(df, columns):
    return df[columns].count()

def mean_columns(df, columns):
    return df[columns].apply(pd.to_numeric, errors='coerce').mean()

def median_columns(df, columns):
    return df[columns].apply(pd.to_numeric, errors='coerce').median()

def std_columns(df, columns):
    return df[columns].apply(pd.to_numeric, errors='coerce').std()

def min_columns(df, columns):
    return df[columns].apply(pd.to_numeric, errors='coerce').min()

def max_columns(df, columns):
    return df[columns].apply(pd.to_numeric, errors='coerce').max()

def mode_columns(df, columns):
    return df[columns].mode().iloc[0]

def main():
    parser = argparse.ArgumentParser(description='Perform statistical operations on specified columns in a CSV file.')
    parser.add_argument('csv_path', type=str, help='Path to the CSV file')
    parser.add_argument('--columns', type=str, nargs='+', required=True, help='List of columns to perform operations on')
    parser.add_argument('--operations', type=str, nargs='+', required=True, choices=['sum', 'count', 'mean', 'median', 'std', 'min', 'max', 'mode'], help='Statistical operations to perform')
    args = parser.parse_args()

    # Load CSV and check columns
    df = pd.read_csv(args.csv_path)
    missing_columns = [col for col in args.columns if col not in df.columns]
    if (missing_columns):
        print(f"Error: The following columns are not in the CSV file: {', '.join(missing_columns)}")
        return

    results = {}
    for operation in args.operations:
        if operation == 'sum':
            results['sum'] = sum_columns(df, args.columns)
        elif operation == 'count':
            results['count'] = count_columns(df, args.columns)
        elif operation == 'mean':
            results['mean'] = mean_columns(df, args.columns)
        elif operation == 'median':
            results['median'] = median_columns(df, args.columns)
        elif operation == 'std':
            results['std'] = std_columns(df, args.columns)
        elif operation == 'min':
            results['min'] = min_columns(df, args.columns)
        elif operation == 'max':
            results['max'] = max_columns(df, args.columns)
        elif operation == 'mode':
            results['mode'] = mode_columns(df, args.columns)

    # Print results
    for op, result in results.items():
        print(f"{op}:\n{result}\n")

if __name__ == "__main__":
    main()
