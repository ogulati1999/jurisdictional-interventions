
import numpy as np
import pandas as pd


def match_covariate(row, cov_df):
    '''
    Given a row from a pandas DataFrame as well as the relevant covariate
    DataFrame, this function matches the country in the row to its appropriate
    statistic in the covariate DataFrame.
    '''
    country = row['Country']
    year = row['Year']

    if country == 'Congo':
        country = 'Congo, Rep.'

    elif country == 'Congo DRC':
        country = 'Congo, Dem. Rep.'

    if str(year) in cov_df:
        if (cov_df[cov_df['Country Name'] == country][str(year)] != '..').iloc(0)[0]:
            return float(cov_df[cov_df['Country Name'] == country][str(year)])

def import_covariates(df, cov_dfs, cov_names):
    '''
    When matching multiple covariates, this function automatically matches and
    imports all of them into a provided DataFrame, df. It requires each of the
    covariate DataFrames as a list, cov_dfs, as well as the intended column
    names for the covariates as a list, cov_names. 
    '''
    for i, cov_df in enumerate(cov_dfs):
        df[cov_names[i]] = df.apply(
            match_covariate, axis=1, args=(cov_df,))
    
    return df