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
import { ImageOverlay, MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

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
  center: [number, number];
  onReady: (handle: KarMapLeafletHandle) => void;
  showGroundplan: boolean;
  groundplanOverlays: GroundplanOverlay[];
  groundplanOpacity: number;
}

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

export function KarMapLeaflet({
  pins,
  center,
  onReady,
  showGroundplan,
  groundplanOverlays,
  groundplanOpacity,
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

    // Frame the map around whatever pins exist at initial load, once — later
    // pin-set changes (layer toggles, search) must NOT re-trigger this, so
    // this reads pinsRef.current only here rather than depending on `pins`.
    const map = mapRef.current;
    const initialPins = pinsRef.current;
    // Every shown ground plan's four corners count too, so all plans fit.
    const overlayBounds = showGroundplan ? groundplanOverlays.map((overlay) => overlay.bounds) : [];
    const fitPoints = [
      ...initialPins.map((pin) => [pin.latitude, pin.longitude] as [number, number]),
      ...overlayBounds.flatMap((bounds) => [
        bounds[0],
        [bounds[0][0], bounds[1][1]] as [number, number],
        [bounds[1][0], bounds[0][1]] as [number, number],
        bounds[1],
      ]),
    ];
    if (map && fitPoints.length > 0) {
      // maxZoom caps how far fitBounds is allowed to zoom in, so a single
      // pin (or a tight cluster) settles at zoom 14 — the same zoom the
      // "Locate" button already uses — instead of snapping to street level.
      const bounds = latLngBounds(fitPoints);
      map.fitBounds(bounds, { maxZoom: 14, padding: [24, 24] });
    }
    // No pins at all: nothing to fit to, so the map just keeps the fallback
    // center/zoom passed in via the `center` prop at mount time.
    // Only ever needs to fire once, when the map first mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MapContainer center={center} zoom={9} ref={mapRef} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
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
