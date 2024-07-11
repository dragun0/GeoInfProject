from django.http import HttpResponse
from django.template import loader
from raster.models import RasterLayer
from .models import Article 

def mapView(request):
    # Get the two most recent RasterLayer entries by id
    risk_maps = RasterLayer.objects.order_by('-id')[:2]
    template = loader.get_template('HomePage.html')
    context = {
       'RiskMaps': risk_maps,
    }
    return HttpResponse(template.render(context, request))

def articleView (request, article_id):
    apparticle = Article.objects.get(id=article_id)
    template = loader.get_template('Article.html')
    context = {
        'appArticle': apparticle,
    }
    return HttpResponse(template.render(context, request))

def methodologyView (request, metho_id):
    methodology = Article.objects.get(id=metho_id)
    template = loader.get_template('Methodology.html')
    context = {
        'methoArticle': methodology,
    }
    return HttpResponse(template.render(context, request))

def weatherView (request):
    template = loader.get_template('Weather.html')
    return HttpResponse(template.render())