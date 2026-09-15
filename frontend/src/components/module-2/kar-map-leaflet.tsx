"use client";

// The actual Leaflet map for KarTracker's Kar Map screen. Kept in its own
// file so it can be loaded via next/dynamic with ssr:false from kar-map.tsx
// — Leaflet touches `window`/`document` at import time and breaks under
// Next's server-side rendering otherwise. Exposes its imperative "locate"
// handle via an onReady callback rather than a forwarded ref, since a ref
// passed through a dynamically-loaded component is unnecessary complexity
// here.

import "leaflet/dist/leaflet.css";

import { divIcon, type Map as LeafletMap, type Marker as LeafletMarker } from "leaflet";
import { useEffect, useRef, type ReactNode } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

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

interface KarMapLeafletProps {
  pins: KarMapPin[];
  center: [number, number];
  onReady: (handle: KarMapLeafletHandle) => void;
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

export function KarMapLeaflet({ pins, center, onReady }: KarMapLeafletProps) {
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
    // Only ever needs to fire once, when the map first mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MapContainer center={center} zoom={9} ref={mapRef} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
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
