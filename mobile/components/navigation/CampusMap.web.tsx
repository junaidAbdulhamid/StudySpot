import { memo, useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { Copy } from "../common";
import { CampusMapProps, mapGroups, mapToken } from "./mapModel";
import {
  getOccupancyColor,
  getOccupancyLevel,
  formatOccupancy,
} from "../../utils/occupancy";
export const CampusMap = memo(function CampusMap({
  locations,
  selectedId,
  onSelect,
  center,
  position,
  recenter = 0,
}: CampusMapProps) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  const initial = useRef(center);
  initial.current = center;
  const hasCenter = !!center;
  useEffect(() => {
    if (!mapToken || !element.current || !initial.current) return;
    try {
      const origin = initial.current;
      const instance = new mapboxgl.Map({
        container: element.current,
        accessToken: mapToken,
        style: "mapbox://styles/mapbox/dark-v11",
        center: [origin.longitude, origin.latitude],
        zoom: 15,
      });
      map.current = instance;
      instance.on("load", () => setReady(true));
      instance.on("error", () => setError(true));
      return () => {
        map.current = null;
        instance.remove();
      };
    } catch {
      setError(true);
    }
  }, [hasCenter]);
  useEffect(() => {
    if (center && ready)
      map.current?.flyTo({
        center: [center.longitude, center.latitude],
        zoom: 15,
      });
  }, [center, recenter, ready]);
  useEffect(() => {
    if (!map.current || !ready) return;
    const instance = map.current;
    const markers = mapGroups(locations).map((group) => {
      const button = document.createElement("button");
      const level = getOccupancyLevel(group.best.currentOccupancy);
      button.textContent = `${group.best.building} · ${formatOccupancy(group.best.currentOccupancy)} ${level}`;
      button.setAttribute(
        "aria-label",
        `${button.textContent}, ${group.locations.length} study zones`,
      );
      button.style.cssText = `background:#07110f;color:white;padding:8px;border-radius:12px;border:${group.locations.some((l) => l.id === selectedId) ? 3 : 1}px solid ${getOccupancyColor(level)}`;
      button.onclick = () => onSelect(group.best.id);
      return new mapboxgl.Marker({ element: button })
        .setLngLat([group.best.longitude, group.best.latitude])
        .addTo(instance);
    });
    if (position)
      markers.push(
        new mapboxgl.Marker({ color: "#5DAAFF" })
          .setLngLat([position.longitude, position.latitude])
          .addTo(instance),
      );
    return () => markers.forEach((marker) => marker.remove());
  }, [locations, selectedId, onSelect, position, ready]);
  if (!mapToken)
    return (
      <Copy>
        Map setup required: set EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN and restart.
        Browse spaces below while maps are unavailable.
      </Copy>
    );
  return (
    <>
      {!ready && !error && <Copy>Loading campus map…</Copy>}
      <div
        ref={element}
        aria-label="Interactive campus map"
        style={{ height: 400, borderRadius: 20, overflow: "hidden" }}
      />
      {error && (
        <Copy>
          Map unavailable. Check your connection and map token. Browse spaces
          below.
        </Copy>
      )}
    </>
  );
});
