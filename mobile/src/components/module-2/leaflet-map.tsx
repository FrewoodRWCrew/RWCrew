// The Kar Map's map: Leaflet + OpenStreetMap inside a WebView, the same map
// library, tiles, pin style and default view as the web's kar-map-leaflet.tsx
// (no map API keys needed). The app drives the page by injecting calls to the
// small `RW` API defined in MAP_HTML below: set the pins, set the ground-plan
// overlays (as data: URIs, so the page never needs the login token) and fly
// to a pin. The page answers "ready" once Leaflet is loaded, or "error" when
// it couldn't be (e.g. offline).

import { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { WebView, type WebViewMessageEvent } from "react-native-webview";

import { useT } from "../../i18n";
import { useColors } from "../../lib/theme";

export type MapPin = {
  key: string;
  latitude: number;
  longitude: number;
  color: string;
  // Ready-made (escaped) HTML for the pin's popup.
  popupHtml: string;
};

export type GroundplanOverlay = {
  key: number;
  uri: string;
  // [[south, west], [north, east]]
  bounds: [[number, number], [number, number]];
};

type Props = {
  pins: MapPin[];
  groundplans: GroundplanOverlay[];
  showGroundplan: boolean;
  // Fly to this pin and open its popup; `token` changes on every request so
  // asking twice for the same pin works too.
  focus: { key: string; token: number } | null;
};

// The HTML page: Leaflet 1.9.4 (the web's version) from cdnjs, OSM tiles,
// opening on the web's fixed default extent (the festival site, EPSG:3857
// values from QGIS in kar-map-leaflet.tsx).
const MAP_HTML = `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
<style>html, body, #map { margin: 0; padding: 0; height: 100%; width: 100%; } .leaflet-popup-content { font: 14px -apple-system, Roboto, sans-serif; }</style>
</head>
<body>
<div id="map"></div>
<script>
  function send(message) { window.ReactNativeWebView.postMessage(message); }
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" onerror="send('error')"></script>
<script>
  (function () {
    if (!window.L) return;
    // Web Mercator metres -> [lat, lng], the same formulas as the web.
    function toLatLng(x, y) {
      var r = 6378137;
      return [Math.atan(Math.sinh(y / r)) * 180 / Math.PI, (x / r) * 180 / Math.PI];
    }
    var map = L.map("map");
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    map.fitBounds([toLatLng(519606.3831, 6614407.5657), toLatLng(523820.1401, 6616715.9879)]);

    var overlays = L.layerGroup();
    var pins = L.layerGroup().addTo(map);
    var markersByKey = {};

    window.RW = {
      // Replace every pin: a round dot in the layer's colour, white border.
      setPins: function (list) {
        pins.clearLayers();
        markersByKey = {};
        list.forEach(function (pin) {
          var icon = L.divIcon({
            className: "",
            html: '<span style="display:block;width:16px;height:16px;border-radius:9999px;background:' + pin.color +
              ';border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4)"></span>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          });
          var marker = L.marker([pin.latitude, pin.longitude], { icon: icon }).bindPopup(pin.popupHtml);
          pins.addLayer(marker);
          markersByKey[pin.key] = marker;
        });
      },
      // Replace the ground-plan images and show/hide them (under the pins).
      setGroundplans: function (list, visible) {
        overlays.clearLayers();
        list.forEach(function (plan) { overlays.addLayer(L.imageOverlay(plan.uri, plan.bounds)); });
        if (visible) overlays.addTo(map); else map.removeLayer(overlays);
      },
      // Fly to a pin (at least zoom 14, like the web) and open its popup.
      locate: function (key) {
        var marker = markersByKey[key];
        if (!marker) return;
        map.flyTo(marker.getLatLng(), Math.max(map.getZoom(), 14));
        marker.openPopup();
      }
    };
    send("ready");
  })();
</script>
</body>
</html>`;

export function LeafletMap({ pins, groundplans, showGroundplan, focus }: Props) {
  const t = useT();
  const colors = useColors();
  const webViewRef = useRef<WebView>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  // Run one RW call inside the page (only once Leaflet is ready).
  function run(script: string) {
    webViewRef.current?.injectJavaScript(`${script}; true;`);
  }

  // Keep the page's pins in sync with the chosen layers/search.
  useEffect(() => {
    if (ready) run(`window.RW.setPins(${JSON.stringify(pins)})`);
  }, [ready, pins]);

  // Ground plans: the images and whether they are shown.
  useEffect(() => {
    if (ready) run(`window.RW.setGroundplans(${JSON.stringify(groundplans)}, ${showGroundplan})`);
  }, [ready, groundplans, showGroundplan]);

  // Fly to a pin when asked (after the pins above are in place).
  useEffect(() => {
    if (ready && focus) run(`window.RW.locate(${JSON.stringify(focus.key)})`);
  }, [ready, focus]);

  function handleMessage(event: WebViewMessageEvent) {
    if (event.nativeEvent.data === "ready") setReady(true);
    if (event.nativeEvent.data === "error") setFailed(true);
  }

  if (failed) {
    return (
      <View style={styles.failed}>
        <Text style={{ color: colors.danger, textAlign: "center" }}>{t("karTracker.map.mapError")}</Text>
      </View>
    );
  }

  return (
    <WebView
      ref={webViewRef}
      // The page loads Leaflet and the tiles over https from the internet.
      source={{ html: MAP_HTML, baseUrl: "https://rwcrew.eu" }}
      originWhitelist={["*"]}
      onMessage={handleMessage}
      onError={() => setFailed(true)}
      style={styles.map}
    />
  );
}

const styles = StyleSheet.create({
  map: { flex: 1 },
  failed: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
});
