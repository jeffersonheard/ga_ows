from osgeo import osr
from django.contrib.gis.db import models as g
from ga_ows.utils import create_spatialref

class InvalidArgumentException(Exception):
    def __init__(self, arg, args):
        super(InvalidArgumentException, self).__init__(arg, args)
        self.arg=arg
        self.valid_args=args

    def __str__(self):
        "Invalid argument {arg}.  Valid are {args}".format(arg=self.arg, args=self.valid_args)

class NotMinimallyValid(Exception):
    def __init__(self, config, msg):
        super(NotMinimallyValid, self).__init__(config, msg)
        self.config = config
        self.msg = msg

    def __str__(self):
        return self.msg

def _fail_if_not_minimally_valid_config(cfg):
    if len(cfg['layers']) == 0:
        raise NotMinimallyValid(cfg, 'No layers in config')
    if len(cfg['serviceurl']) == 0:
        raise NotMinimallyValid(cfg, 'No service url defined in config')
    if len(cfg['ns']['name']) == 0:
        raise NotMinimallyValid(cfg, 'No namespace definition')

def _dict_from_valid(**valid_kwargs):
    def closure(**kwargs):
        ret = {}
        for arg in kwargs:
            if arg not in valid_kwargs:
                raise InvalidArgumentException(arg, valid_kwargs.keys())
        for arg in valid_kwargs:
            if arg in kwargs:
                ret[arg] = kwargs[arg]
            else:
                ret[arg] = valid_kwargs[arg]
        return ret

    if '__doc__' not in valid_kwargs or valid_kwargs['__doc__'] is None:
        __doc__ = str(valid_kwargs)
    else:
        __doc__ = valid_kwargs['__doc__']
    closure.__doc__ = __doc__
    return closure

contact_address = _dict_from_valid(
    type='', address='', city='', state='', postcode='', country='')

contact_description = _dict_from_valid(
    person='', organization='', position='', address='', phone='', fax='', email='')

service_description = _dict_from_valid(
    minx=-180.0, miny=-90.0, maxx=180.0, maxy=180.0)

style_description = _dict_from_valid(
    name='', title='', legendwidth='', legendheight='', legendurl='', legendformat='')

ns_description = _dict_from_valid(name='', url='', schemaurl='')

def layer_description(**kwargs):
    validate = _dict_from_valid(name='', title='', srs='', minx=-180.0, miny=-90.0, maxx=180.0, maxy=90.0, styles=[])
    cfg = validate(kwargs)

    if type(cfg['srs']) is int:
        kind='srid'
    elif cfg['srs'].upper().startswith('EPSG'):
        kind=None
    elif cfg['srs'].startswith('-') or cfg['srs'].startswith('+'):
        kind='proj'
    else:
        kind='wkt'

    s_srs = create_spatialref(cfg['srs'], srs_format=kind)
    t_srs = osr.SpatialReference()
    t_srs.ImportFromEPSG(4326)

    t = osr.CoordinateTransformation(s_srs, t_srs)
    cfg['ll_minx'], cfg['ll_miny'], _0 = t.TransformPoint(cfg['minx'], cfg['miny'])
    cfg['ll_maxx'], cfg['ll_maxy'], _0 = t.TransformPoint(cfg['maxx'], cfg['maxy'])
    return cfg


def config_from_model(**kwargs):
    validate = _dict_from_valid(
        model=None, 
        ns={}, 
        serviceurl=None, 
        addresses=[], 
        styles=[], 
        cache=True,
        layertitles={},
        expires=lambda x:None)
    cfg = validate(kwargs)

    cfg['ns'] = ns_description(cfg['ns'])
    cfg['addresses'] = [contact_address(a) for a in cfg['addresses']]
    cfg['styles'] = dict( [(k, style_description(s)) for k, s in cfg['styles'].items()] )
    
    cfg['layers'] = []
    minx,miny,maxx,maxy = 0,0,0,0
    for f in cfg['model']._meta.fields:
        if type(cfg['model']._meta.fields[f]) in [
                g.PointField, g.PolygonField, g.LineStringField, g.GeometryCollectionField,
                g.MultiPointField, g.MultiPolygonField, g.MultiLineStringField]:
            minx,miny,maxx,maxy = cfg['model'].nativebbox()
            if f not in cfg['layertitles']:
                cfg['layertitles'] = f
            cfg['layers'].append(
                layer_description(
                    name=f, 
                    title=cfg['layertitles'][f], 
                    srs='EPSG:{srs}'.format(srs=f.srid),
                    minx=minx, maxx=maxx, miny=miny, maxy=maxy, styles=cfg['styles'][f]))
    
    cfg['service'] = service_description(minx=minx, maxx=maxx, miny=miny, maxy=maxy)
    _fail_if_not_minimally_valid_config(cfg)

    return cfg

def config_from_document(**kwargs):
    validate = _dict_from_valid(
        ns={}, 
        serviceurl=None, 
        addresses=[], 
        styles=[], 
        service=service_description({}),
        layers=[],
        cache=True,
        expires=lambda x:None)
    cfg = validate(kwargs)

    cfg['ns'] = ns_description(cfg['ns'])
    cfg['addresses'] = [contact_address(a) for a in cfg['addresses']]
    cfg['styles'] = dict( [(k, style_description(s)) for k, s in cfg['styles'].items()] )
    cfg['service'] = service_description(cfg['service'])
    cfg['layers'] = [layer_description(**l) for l in cfg['layers']]
    _fail_if_not_minimally_valid_config(cfg)

    return cfg
