from django.db import models
from django.contrib.gis.db import models as geomodels
#from raster import models as rastermodels

#class Maps(models.Model):
#  MapName = models.CharField(max_length=255)
#  Raster = geomodels.RasterField()

#class NewMaps(rastermodels.RasterLayer):
#  name = models.CharField(max_length=255)

class Article(models.Model):
  articleTitle = models.CharField(max_length=255)
  articleSubtitle = models.CharField(null=True, blank=True, max_length=255)
  articleContent = models.TextField()
  articleImage = models.ImageField(null=True, blank=True, upload_to="static/")
