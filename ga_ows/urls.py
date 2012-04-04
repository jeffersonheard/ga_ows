from django.conf.urls.defaults import patterns, url
from ga_ows.views.wfs import WFS
from ga_ows.views.wms import WMS, GeoDjangoWMSAdapter
from ga_ows.models import test_models as m

#
# This file maps views to actual URL endpoints. 
#

urlpatterns = patterns('',
    url(r'^tests/wfs/?', WFS.as_view(
        models=[m.WFSPointTest, m.WFSLineStringTest],
        title='GeoDjango WFS Test',
        keywords=['some','keywords'],
        fees='one dollar',
        provider_name='RENCI',
        addr_street='100 Europa Dr. ste 529',
        addr_city='Chapel Hill',
        addr_admin_area='NC',
        addr_postcode='27515',
        addr_country='USA',
        addr_email='jeff@renci.org'
    )),
)
