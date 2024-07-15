from django.http import HttpResponse
from django.template import loader
from raster.models import RasterLayer
from django.templatetags.static import static
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
    article_content = methodology.articleContent
    template = loader.get_template('Methodology.html')
    placeholder_mappings = {
        '__THRESHOLDS_IMAGE__': static('thresholds.png'),
    }

    # Replace all placeholders with their actual values
    for placeholder, replacement in placeholder_mappings.items():
        article_content = article_content.replace(placeholder, replacement)

    context = {
        'methoArticle': methodology,
        'articleContent': article_content,
    }
    return HttpResponse(template.render(context, request))

#def weatherView (request):
#    template = loader.get_template('Weather.html')
#    return HttpResponse(template.render())