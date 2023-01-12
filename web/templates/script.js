// https://wrightshq.com/playground/placing-multiple-markers-on-a-google-map-using-api-3/
// https://github.com/googlemaps/js-marker-clusterer
// https://developers.google.com/maps/documentation/javascript/marker-clustering

jQuery(function($) {
    // Asynchronously Load the map API
    var script = document.createElement('script');
    script.src = "//maps.googleapis.com/maps/api/js?key={{api_key}}&callback=initialize";
    document.body.appendChild(script);
});

let map;
let markers = [];
let markerCluster;



function draw_markers(locations) {
    const urlSearchParams = new URLSearchParams(window.location.search);
    const params = Object.fromEntries(urlSearchParams.entries())

    href = window.location.search;
    if ( params['name'] == undefined ) {
        if ( href.length > 0 ) {
            href += '&name='
        } else {
            href += '?name='
        }
    }

    const infoWindow = new google.maps.InfoWindow({
        content: "",
        disableAutoPan: true,
    });


   markers = locations.map((item, i) => {
    const color = item[10];

    const svgMarker = {
        path: "M-1.547 12l6.563-6.609-1.406-1.406-5.156 5.203-2.063-2.109-1.406 1.406zM0 0q2.906 0 4.945 2.039t2.039 4.945q0 1.453-0.727 3.328t-1.758 3.516-2.039 3.070-1.711 2.273l-0.75 0.797q-0.281-0.328-0.75-0.867t-1.688-2.156-2.133-3.141-1.664-3.445-0.75-3.375q0-2.906 2.039-4.945t4.945-2.039z",
        fillColor: color,
        fillOpacity: 1.0,
        strokeWeight: 0,
        rotation: 0,
        scale: 2,
        anchor: new google.maps.Point(0, 20),
    };

    const label = item[0];
    const marker = new google.maps.Marker({
      position: new google.maps.LatLng(item[1], item[2]),
      label,
      icon: svgMarker
    });

    const hwModel = item[3];
    const snr = item[4];
    const lastHeard = item[5];
    const batteryLevel = item[6];
    const altitude = item[7];
    // new in 1.3.35+ and 2.x
    const chUtil = item[8];
    const airUtil = item[9];
    // MQTT
    const MQTT = item[11];
    // markers can only be keyboard focusable when they have click listeners
    // open info window when marker is clicked
    marker.addListener("click", () => {
      infoWindow.setContent('<div><a href="' + href + label + '">' + label + '</a>' +
                            '<hr>' +
                            'Last heard: ' + lastHeard +
                            '<br>HW Model: ' + hwModel +
                            '<br>SNR: ' + snr +
                            '<br>ChUtil: ' + chUtil + '% ' +
                            '<br>AirUtil: ' + airUtil + '% ' +
                            '<br>Battery level: ' + batteryLevel + '% ' +
                            '<br>Altitude: ' + altitude + 'm ' +
                            '<br>MQTT: ' + MQTT +
      '</div>');
      infoWindow.open(map, marker);
    });
    return marker;
  });

}

function getMarkers() {
    console.log('(Re)drawing markers...');
    $.get('/data.json' + window.location.search, function(data) {
        // clear
        markerCluster.clearMarkers();
        markerCluster.setMap(null);
        markers = [];
        // (re)draw
        draw_markers(data);
        markerCluster.markers = markers;
        markerCluster.setMap(map);
    });
}


function initialize() {
    var center = new google.maps.LatLng({{center_latitude}}, {{center_longitude}});
    // global
    map = new google.maps.Map(document.getElementById('map'), {
          zoom: 10,
          center: center,
          scaleControl: true,
          mapTypeId: google.maps.MapTypeId.ROADMAP,
          mapTypeControl: true,
          mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
            mapTypeIds: ["roadmap", "satellite"],
          },
        });

    // global
    markerCluster = new markerClusterer.MarkerClusterer({ map, markers });
    getMarkers();
    setInterval(getMarkers, {{redraw_markers_every}}000);
}
