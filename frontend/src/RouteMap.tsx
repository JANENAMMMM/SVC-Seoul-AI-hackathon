import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Day, Place } from "./types";

type Point = {
  id: string;
  lat: number;
  lng: number;
  name: string;
  grade: string | null;
  cautions: string[];
};
export function RouteMap({
  day,
  before,
  places,
  selected,
  onSelect,
}: {
  day: Day;
  before?: Day;
  places: Place[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null),
    mapRef = useRef<L.Map | null>(null),
    markers = useRef<L.LayerGroup | null>(null),
    bounds = useRef<L.LatLngBounds | null>(null),
    previousKey = useRef(""),
    selectRef = useRef(onSelect);
  const [background, setBackground] = useState<
      "loading" | "ready" | "unavailable"
    >("loading"),
    [retry, setRetry] = useState(0);
  selectRef.current = onSelect;
  const pointsOf = (d: Day): Point[] =>
    d.stops
      .filter((s) => s.type === "attraction")
      .flatMap((s) => {
        const p = places.find((p) => p.place_id === s.place_id);
        if (!p) return [];
        const v = p.modes[s.mode || "standard"];
        return [
          {
            id: p.place_id,
            lat: p.lat,
            lng: p.lng,
            name: p.name_ko,
            grade: v.grade,
            cautions: v.cautions,
          },
        ];
      });
  const current = pointsOf(day),
    old = before ? pointsOf(before) : [],
    key = JSON.stringify([current, old]);
  useEffect(() => {
    if (!host.current) return;
    let alive = true;
    setBackground("loading");
    previousKey.current = "";
    const map = L.map(host.current, {
      zoomControl: false,
      scrollWheelZoom: false,
      attributionControl: true,
    });
    mapRef.current = map;
    markers.current = L.layerGroup().addTo(map);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);
    // Browser image policy sends only the origin, never shared-link tokens. No server setting change.
    const tiles = L.tileLayer(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 18,
        referrerPolicy: "origin",
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    );
    function failed() {
      if (!alive) return;
      if (map.hasLayer(tiles)) map.removeLayer(tiles);
      setBackground("unavailable");
    }
    const timer = setTimeout(failed, 8000);
    tiles.on("tileload", () => {
      clearTimeout(timer);
      if (alive && map.hasLayer(tiles)) setBackground("ready");
    });
    tiles.on("tileerror", () => {
      clearTimeout(timer);
      failed();
    });
    tiles.addTo(map);
    const observer = new ResizeObserver(() => {
      if (host.current && host.current.clientWidth > 0) {
        map.invalidateSize({ pan: false });
        if (bounds.current)
          map.fitBounds(bounds.current, { padding: [55, 50], maxZoom: 13 });
      }
    });
    observer.observe(host.current);
    return () => {
      alive = false;
      clearTimeout(timer);
      observer.disconnect();
      tiles.off();
      map.remove();
      mapRef.current = null;
      markers.current = null;
    };
  }, [retry]);
  useEffect(() => {
    const map = mapRef.current,
      layer = markers.current;
    if (!map || !layer) return;
    layer.clearLayers();
    if (old.length > 1)
      L.polyline(
        old.map((p) => [p.lat, p.lng]),
        { color: "#999", weight: 4, dashArray: "7 8", opacity: 0.7 },
      ).addTo(layer);
    if (current.length > 1)
      L.polyline(
        current.map((p) => [p.lat, p.lng]),
        { color: "#5e2bb8", weight: 4, opacity: 0.85 },
      ).addTo(layer);
    current.forEach((p, i) => {
      const icon = L.divIcon({
        className: "route-marker",
        html: `<span class="map-dot ${selected === p.id ? "selected" : ""}">${i + 1}<small class="marker-grade-${["하", "중", "상"].includes(p.grade || "") ? p.grade : "unknown"}">${["하", "중", "상"].includes(p.grade || "") ? p.grade : "?"}</small></span>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      const marker = L.marker([p.lat, p.lng], {
        icon,
        zIndexOffset: selected === p.id ? 1000 : 0,
      })
        .addTo(layer)
        .on("click", () => selectRef.current(p.id));
      const label = document.createElement("div"),
        title = document.createElement("strong"),
        detail = document.createElement("div");
      title.textContent = p.name + " · " + (p.grade || "미확인");
      detail.textContent = p.cautions.join(" · ");
      label.append(title);
      if (p.cautions.length) label.append(detail);
      marker.bindTooltip(label, {
        permanent: selected === p.id,
        direction: "top",
        offset: [0, -20],
        className: "place-tooltip",
      });
    });
    const all = [...current, ...old];
    bounds.current = all.length
      ? L.latLngBounds(all.map((p) => [p.lat, p.lng]))
      : null;
    if (previousKey.current !== key) {
      if (bounds.current)
        map.fitBounds(bounds.current, { padding: [60, 55], maxZoom: 13 });
      else map.setView([16.05, 108.2], 12);
      previousKey.current = key;
    }
  }, [key, selected, retry]);
  return (
    <div className="map-wrap" data-background={background}>
      <div
        ref={host}
        className="route-map"
        aria-label="관광지 위치와 방문 순서 지도"
      />
      {background === "unavailable" && (
        <div className="map-failure" role="status">
          <span>
            배경 지도를 불러오지 못했습니다. 위치와 방문 순서는 표시됩니다.
          </span>
          <button onClick={() => setRetry((n) => n + 1)}>다시 불러오기</button>
        </div>
      )}
      <span className="map-caption">관광지 위치 · 방문 순서 표시</span>
      {before && (
        <span className="map-key">
          ● 변경안　<span>┄ 변경 전</span>
        </span>
      )}
      <span className="map-disclaimer">실제 도로 경로와 다를 수 있습니다</span>
    </div>
  );
}
