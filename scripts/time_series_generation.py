import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.geometry import Polygon
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def rebin(a, shape):
    '''
    Resizes a numpy array to the desired shape.
    '''
    sh = shape[0], a.shape[0]//shape[0], shape[1], a.shape[1]//shape[1]
    return a.reshape(sh).mean(-1).mean(1)


def point_within_country(row, country_shp):
    '''
    Checks if the entered latitude and longitude are within the country of
    interest.
    '''
    point = Point(row['lon'], row['lat'])
    return country_shp.contains(point)


def sum_tile(tile, country_shp, topleftlat, topleftlon, canopy_threshold):
    '''
    Calculates total forest pixels and country pixels within the tile provided.

    Forest pixels are considered as those where canopy cover is greater than 
    or equal to the provided threshold. Typically, this is 30%.
    '''
    n = len(tile)

    tile_df = pd.DataFrame({'x': n * [x for x in range(n)],
                            'y': np.array([n * [y] for y in range(n)]).flatten()})

    tile_df['lat'] = topleftlat - (tile_df['y']/n) * 10
    tile_df['lon'] = topleftlon + (tile_df['x']/n) * 10

    tile_df['cover'] = tile.flatten()

    tile_df['country'] = tile_df.apply(
        point_within_country, axis=1, args=(country_shp,))

    forest_pixels = len(tile_df[(tile_df["country"] == True) & (
        tile_df["cover"] >= canopy_threshold)])
    country_pixels = len(tile_df[tile_df["country"] == True])

    return [forest_pixels, country_pixels, tile_df]


def sum_across_tiles(tiles, country_shp, topleftlats, topleftlons, canopy_threshold):
    '''
    Calculates total forest pixels and country pixels contained within the
    provided tiles. It is important to ensure that all tiles spanning the 
    country are provided.
    '''
    forest_total = 0
    country_total = 0
    tile_dfs = []
    for i, tile in enumerate(tiles):
        summary = sum_tile(tile, country_shp,
                           topleftlats[i], topleftlons[i], canopy_threshold)
        forest_total += summary[0]
        country_total += summary[1]
        tile_dfs.append(summary[2])
    return [forest_total, country_total, tile_dfs]


def cover_trajectory(forest_total, tile_dfs, loss_tiles):
    '''
    Given outputs of sum_across_tiles as well as loss_tiles, this provides the
    full annual forest loss trajectory for the dataset. 

    This function currently assumes that forest loss was calculated at the
    full 40,000 x 40,000 grid level, while the initial forest cover was only
    calculated at a 4,000 x 4,000 grid level. This would result in a 100 factor
    difference within the values obtained, which is accounted for here. 
    '''

    trajectory = dict()

    for i, df in enumerate(tile_dfs):

        df = df[df['country'] == True]
        df['loss'] = [loss_tiles[i][(y * 10):(y * 10 + 10), (x * 10):(x * 10 + 10)].flatten()
                      for (x, y) in zip(df['x'], df['y'])]

        unique, counts = np.unique(df['loss'].explode(), return_counts=True)
        tile_trajectory = dict(zip(unique, counts))
        trajectory = {key: trajectory.get(key, 0) + tile_trajectory.get(key, 0)
                      for key in set(trajectory) | set(tile_trajectory)}

    annual_loss = []

    for year in range(1, max(trajectory.keys()) + 1):
        # This is a percentage without multiplying by 100, since loss is at a 100 times higher resolution
        cover_loss = trajectory[year]/forest_total
        forest_total -= trajectory[year]/100
        annual_loss.append(cover_loss)

    return annual_loss


def generate_trajectory(country, tiles, loss_tiles,
                        topleftlats, topleftlons, canopy_threshold):
    '''
    Aggregates the process for generating a time series of annual forest loss.
    '''

    boundaries = gpd.read_file("../data/World_Countries__Generalized_.shp")
    country_shp = boundaries[boundaries['COUNTRY'] == country].geometry

    for i, tile in enumerate(tiles):
        tiles[i] = rebin(np.array(tile), [4000, 4000])

    for i, tile in enumerate(loss_tiles):
        loss_tiles[i] = np.array(tile)

    country_sum = sum_across_tiles(tiles, country_shp, topleftlats,
                                   topleftlons, canopy_threshold)

    time_series = cover_trajectory(country_sum[0], country_sum[2], loss_tiles)

    output = pd.DataFrame({'Country': country,
                           'Year': [x for x in range(2001, 2022)],
                           'Annual Tree Cover Loss': time_series})

    output.to_csv('../data/main.csv', mode='a', header=False)

    return output
