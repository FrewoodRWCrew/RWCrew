"use client";

// The actual Leaflet map for KarTracker's Kar Map screen. Kept in its own
// file so it can be loaded via next/dynamic with ssr:false from kar-map.tsx
// — Leaflet touches `window`/`document` at import time and breaks under
// Next's server-side rendering otherwise. Exposes its imperative "locate"
// handle via an onReady callback rather than a forwarded ref, since a ref
// passed through a dynamically-loaded component is unnecessary complexity
// here.

import "leaflet/dist/leaflet.css";

import { divIcon, latLngBounds, type Map as LeafletMap, type Marker as LeafletMarker } from "leaflet";
import { useEffect, useRef, type ReactNode } from "react";
import { ImageOverlay, MapContainer, Marker, Popup, TileLayer, useMapEvents } from "react-leaflet";

export interface KarMapPin {
  key: string;
  latitude: number;
  longitude: number;
  color: string;
  popup: ReactNode;
}

export interface KarMapLeafletHandle {
  /** Pan/zoom the map to the given pin and open its popup. */
  locate: (key: string) => void;
}

export interface GroundplanOverlay {
  key: number;
  url: string;
  bounds: [[number, number], [number, number]];
}

interface KarMapLeafletProps {
  pins: KarMapPin[];
  onReady: (handle: KarMapLeafletHandle) => void;
  showGroundplan: boolean;
  groundplanOverlays: GroundplanOverlay[];
  groundplanOpacity: number;
  /** Optional: whenever this value changes, the map re-frames itself around
   * the current pins and ground plans (e.g. after a different afleverlocatie
   * was picked). Without it, the map only ever shows the default extent it
   * opens on. */
  fitKey?: string;
  /** Optional: called with the clicked point's coordinates whenever the
   * user clicks on the map (e.g. to pick a location on "Manuele kar
   * beweging"). Without it, clicking the map does nothing. */
  onMapClick?: (latitude: number, longitude: number) => void;
}

// The area every map opens on (the Werchter festival site), copied as-is
// from QGIS's "Extent" panel in EPSG:3857 (Web Mercator metres) — paste new
// QGIS values here to move the default view.
const DEFAULT_EXTENT_3857 = {
  north: 6616715.9879,
  south: 6614407.5657,
  west: 519606.3831,
  east: 523820.1401,
};

/** Convert a Web Mercator (EPSG:3857) x/y in metres to a Leaflet [lat, lng]
 * in degrees, using the spherical Mercator formulas. */
function webMercatorToLatLng(x: number, y: number): [number, number] {
  const earthRadius = 6378137;
  const lng = (x / earthRadius) * (180 / Math.PI);
  const lat = Math.atan(Math.sinh(y / earthRadius)) * (180 / Math.PI);
  return [lat, lng];
}

// The same extent as lat/lng bounds: south-west corner, then north-east.
const DEFAULT_VIEW_BOUNDS = latLngBounds(
  webMercatorToLatLng(DEFAULT_EXTENT_3857.west, DEFAULT_EXTENT_3857.south),
  webMercatorToLatLng(DEFAULT_EXTENT_3857.east, DEFAULT_EXTENT_3857.north),
);

/** A small colored dot built from a plain div, used instead of Leaflet's
 * default marker image — sidesteps the well-known bundler broken-icon-path
 * problem entirely and lets each layer's pins carry their own accent color. */
function dotIcon(color: string) {
  return divIcon({
    className: "",
    html: `<span style="display:block;width:16px;height:16px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4)"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8],
  });
}

/** Frame the map around every given pin plus, when shown, every ground
 * plan's four corners. Does nothing when there's nothing to frame. */
function fitToContent(map: LeafletMap, pins: KarMapPin[], overlays: GroundplanOverlay[]) {
  const fitPoints = [
    ...pins.map((pin) => [pin.latitude, pin.longitude] as [number, number]),
    ...overlays.flatMap((overlay) => [
      overlay.bounds[0],
      [overlay.bounds[0][0], overlay.bounds[1][1]] as [number, number],
      [overlay.bounds[1][0], overlay.bounds[0][1]] as [number, number],
      overlay.bounds[1],
    ]),
  ];
  if (fitPoints.length === 0) return;
  // maxZoom caps how far fitBounds is allowed to zoom in, so a single
  // pin (or a tight cluster) settles at zoom 14 — the same zoom the
  // "Locate" button already uses — instead of snapping to street level.
  map.fitBounds(latLngBounds(fitPoints), { maxZoom: 14, padding: [24, 24] });
}

/** Forwards map clicks to the caller. Must live inside MapContainer, since
 * react-leaflet's useMapEvents reads the map from its context. */
function MapClickHandler({ onMapClick }: { onMapClick: (latitude: number, longitude: number) => void }) {
  useMapEvents({
    click(event) {
      onMapClick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

export function KarMapLeaflet({
  pins,
  onReady,
  showGroundplan,
  groundplanOverlays,
  groundplanOpacity,
  fitKey,
  onMapClick,
}: KarMapLeafletProps) {
  const mapRef = useRef<LeafletMap | null>(null);
  const markerRefsByKey = useRef<Map<string, LeafletMarker>>(new Map());
  // Read via a ref inside the handle so it always sees the latest pins
  // without onReady needing to fire again every time they change.
  const pinsRef = useRef(pins);
  useEffect(() => {
    pinsRef.current = pins;
  }, [pins]);

  useEffect(() => {
    onReady({
      locate(key: string) {
        const pin = pinsRef.current.find((candidate) => candidate.key === key);
        const map = mapRef.current;
        if (!pin || !map) return;
        map.flyTo([pin.latitude, pin.longitude], Math.max(map.getZoom(), 14));
        markerRefsByKey.current.get(key)?.openPopup();
      },
    });

    // Every map opens on the fixed default extent, not on its pins. The
    // MapContainer already starts there via its `bounds` prop; fitting once
    // more here corrects for the container's final size after layout.
    const map = mapRef.current;
    if (map) map.fitBounds(DEFAULT_VIEW_BOUNDS);
    // Only ever needs to fire once, when the map first mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-frame whenever the caller's fitKey changes. The value seen at mount
  // is remembered so this doesn't fit a second time right after the
  // mount-time fit above.
  const lastFitKeyRef = useRef(fitKey);
  useEffect(() => {
    if (fitKey === undefined || fitKey === lastFitKeyRef.current) return;
    lastFitKeyRef.current = fitKey;
    const map = mapRef.current;
    if (map) fitToContent(map, pins, showGroundplan ? groundplanOverlays : []);
    // Only a new fitKey should move the map — not toggling the ground plan
    // layer or any other re-render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);

  return (
    <MapContainer bounds={DEFAULT_VIEW_BOUNDS} ref={mapRef} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {onMapClick && <MapClickHandler onMapClick={onMapClick} />}
      {showGroundplan &&
        // Rendered above the OSM tiles but below the pins, so pin dots
        // stay visible on top of the ground plan images.
        groundplanOverlays.map((overlay) => (
          <ImageOverlay key={overlay.key} url={overlay.url} bounds={overlay.bounds} opacity={groundplanOpacity} />
        ))}
      {pins.map((pin) => (
        <Marker
          key={pin.key}
          position={[pin.latitude, pin.longitude]}
          icon={dotIcon(pin.color)}
          ref={(marker) => {
            if (marker) markerRefsByKey.current.set(pin.key, marker);
            else markerRefsByKey.current.delete(pin.key);
          }}
        >
          <Popup>{pin.popup}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
