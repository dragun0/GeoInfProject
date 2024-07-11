/*

var osm = new ol.layer.Tile({ 
    visible: true,
    source: new ol.source.OSM()
    });

var riskMap = new ol.layer.TMS({
    source: new ol.source.TileImage ({
        url:'/raster/tiles/6/{z}/{x}/{y}.png'
    })
});

var map = new ol.Map({
    target: document.getElementById('map'), 
    layers: [osm, riskMap
    ],
 
    view: new ol.View({ 
        center: [0, 0], 
        zoom: 2
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

    */