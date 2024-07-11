
var map = new ol.Map({
    target: document.getElementById('map'), 
    layers: [
        new ol.layer.Tile({
            visible: true,
            source: new ol.source.OSM()
        }) 
    ],
    view: new ol.View({ 
        center: [23, 13], 
        zoom: 3
    }),
    controls: ol.control.defaults.defaults().extend([ 
        new ol.control.ScaleLine(),
        new ol.control.FullScreen(),
        new ol.control.OverviewMap(),
        new ol.control.MousePosition({
            coordinateFormat: ol.coordinate.createStringXY(4), 
            projection: 'EPSG:4326'
        }) 
    ])
});