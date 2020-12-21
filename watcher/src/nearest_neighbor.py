from datetime import datetime, timedelta

import requests
from shapely.geometry import Polygon


PROVIDER = 'ASF'
COLLECTION_SHORT_NAMES = ['SENTINEL-1A_SLC', 'SENTINEL-1B_SLC']
SESSION = requests.Session()


def get_attribute_value(granule, attribute_name):
    for attribute in granule['umm']['AdditionalAttributes']:
        if attribute['Name'] == attribute_name:
            return attribute['Values'][0]
    raise Exception(f'no value for attribute {attribute_name}')


def get_polygon_string(granule):
    coords = []
    for point in granule['umm']['SpatialExtent']['HorizontalSpatialDomain']['Geometry']['GPolygons'][0]['Boundary']['Points']:
        coords.append(str(point['Longitude']))
        coords.append(str(point['Latitude']))
    return ','.join(coords)


def get_polygon(granule):
    points = []
    for point in granule['umm']['SpatialExtent']['HorizontalSpatialDomain']['Geometry']['GPolygons'][0]['Boundary']['Points']:
        points.append((point['Longitude'], point['Latitude']))
    return Polygon(points)


def get_orbit(granule):
    return granule['umm']['OrbitCalculatedSpatialDomains'][0]['OrbitNumber']


def get_beginning_date_time(granule):
    return datetime.strptime(granule['umm']['TemporalExtent']['RangeDateTime']['BeginningDateTime'][:-5], '%Y-%m-%dT%H:%M:%S')


def get_name(granule):
    return granule['umm']['DataGranule']['Identifiers'][0]['Identifier']


def get_granule_metadata(granule):
    return {
        'name': get_name(granule),
        'orbit_number': get_orbit(granule),
        'polygon_string': get_polygon_string(granule),
        'polygon': get_polygon(granule),
        'beginning_date_time': get_beginning_date_time(granule),
        'beam_mode': get_attribute_value(granule, 'BEAM_MODE'),
        'ascending_descending': get_attribute_value(granule, 'ASCENDING_DESCENDING'),
        'path_number': get_attribute_value(granule, 'PATH_NUMBER'),
        'polarization': get_attribute_value(granule, 'POLARIZATION'),
    }


def query_cmr(params):
    search_url = 'https://cmr.earthdata.nasa.gov/search/granules.umm_json'
    response = SESSION.post(search_url, data=params)
    response.raise_for_status()
    granules = [get_granule_metadata(item) for item in response.json()['items']]
    return granules


def get_search_polarization(polarization):
    for option in 'HH,HH+HV', 'VV,VV+VH':
        if polarization in option.split(','):
            return option
    raise Exception(f'unsupported polarization: {polarization}')


def get_secondary_scene_name(reference_scene):
    search_datetime = reference_scene['beginning_date_time'] - timedelta(days=1)
    search_polarization = get_search_polarization(reference_scene['polarization'])
    params = {
        'provider': PROVIDER,
        'short_name': COLLECTION_SHORT_NAMES,
        'attribute[]': [
            f'string,BEAM_MODE,{reference_scene["beam_mode"]}',
            f'string,ASCENDING_DESCENDING,{reference_scene["ascending_descending"]}',
            f'int,PATH_NUMBER,{reference_scene["path_number"]}',
            f'string,POLARIZATION,{search_polarization}',
        ],
        'temporal': f',{search_datetime.isoformat()}',
        'polygon': reference_scene['polygon_string'],
        'sort_key': '-start_date',
        'page_size': 10,
    }
    secondary_scenes = query_cmr(params)
    if not secondary_scenes:
        return None

    secondary_scenes = [item for item in secondary_scenes if
                        item['orbit_number'] == secondary_scenes[0]['orbit_number']]
    secondary_scenes.sort(key=lambda scene: scene['polygon'].intersection(reference_scene['polygon']).area, reverse=True)
    return secondary_scenes[0]['name']


def make_pairs(reference_scene_names):
    params = {
        'provider': PROVIDER,
        'short_name': COLLECTION_SHORT_NAMES,
        'producer_granule_id': reference_scene_names,
        'page_size': 2000,
    }
    reference_scenes = query_cmr(params)

    pairs = []
    for reference_scene in reference_scenes:
        secondary_scene_name = get_secondary_scene_name(reference_scene)
        pairs.append([reference_scene['name'], secondary_scene_name])
    return pairs
