from django.views.generic import TemplateView, View
from ga_ows.models import wms

class WMSCacheClearView(TemplateView):
    template_name = 'ga_ows/wms/clear_cache.html'

    def post(self, *args, **kwargs):
        application = kwargs['app']
        wms.Cache.objects(application=application).delete()

    def get_context_data(self, **kwargs):
        return { 'apps' : wms.Cache.objects.distinct('application') }

class WMSCacheView(TemplateView):
    template_name = 'ga_ows/wms/cache_view.html'

    def get_context_data(self, **kwargs):
        apps = list( wms.Cache.objects.distinct('application'))
        counts = dict( [(a, wms.Cache.objects(application=a).count()) for a in apps] )
        return { 
            'apps' : apps,
            'counts' : counts
        }
