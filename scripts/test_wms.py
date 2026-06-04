import requests, json

url = ('https://image.discomap.eea.europa.eu/arcgis/rest/services/'
       'GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer/identify')

geom = '{"x":4.7005,"y":50.8798,"spatialReference":{"wkid":4326}}'

r = requests.get(url, params={
    'geometry':       geom,
    'geometryType':   'esriGeometryPoint',
    'returnGeometry': 'false',
    'f':              'json',
}, timeout=15)

print(f'Status : {r.status_code}')
d = r.json()
print(f'Value  : {d.get("value")}')
print(f'Full   : {json.dumps(d, indent=2)[:600]}')
