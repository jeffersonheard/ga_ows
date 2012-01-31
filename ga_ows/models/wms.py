import mongoengine as mgo
import datetime

class Cache(mgo.Document):
    item = mgo.BinaryField()
    cache_key = mgo.StringField(required=True)
    when = mgo.DateTimeField()
    access = mgo.DateTimeField()
    expires = mgo.DateTimeField()
    application = mgo.StringField()
    bbox = mgo.ListField(mgo.FloatField())

    __meta__ = { 'indexes' : ['access', 'expires', 'application', ('application', 'cache_key')], }
   
    @classmethod
    def retrieve(cls, application, cache_key):
        r = cls.objects(application=application, cache_key=cache_key).first()
        if r:
            now = datetime.datetime.now()
            if r.expires and r.expires < now:
                r.delete()
                r = None
            else:
                r.access = now
                r.save()
            return r.item
        else:
            return None

    @classmethod
    def add(cls, application, item, cache_key, expires=None, bbox=None):
        now = datetime.datetime.now()
        cls(
            application=application,
            item=item,
            cache_key = cache_key,
            when = now,
            access = now,
            expires = expires,
            bbox=bbox
        ).save()
    
    @classmethod
    def clean(cls, limit=None):
        cls.objects(expires__lt=datetime.datetime.now()).delete()
        if limit and cls.objects().count() > limit:
            e = cls.objects().order_by('+access').limit(limit).delete()

    @classmethod
    def clear(cls, application, **q):
        cls.objects(application=application, **q).delete()

