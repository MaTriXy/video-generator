---
name: maps
description: Make map animations with Mapbox
metadata:
  tags: map, map animation, mapbox
---

Maps can be added to a Remotion video with Mapbox.  
The [Mapbox documentation](https://docs.mapbox.com/mapbox-gl-js/api/) has the API reference.

## Prerequisites

Required packages: `mapbox-gl`, `@turf/turf`, `@types/mapbox-gl`

The Mapbox access token is passed as a `mapboxToken` prop to each scene component. Use it directly instead of `process.env`.

## Adding a map

Here is a basic example of a map in Remotion.

```tsx
import {useEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, useDelayRender, useVideoConfig} from 'remotion';
import mapboxgl, {Map} from 'mapbox-gl';

export const lineCoordinates = [
  [6.56158447265625, 46.059891147620725],
  [6.5691375732421875, 46.05679376154153],
  [6.5842437744140625, 46.05059898938315],
  [6.594886779785156, 46.04702502069337],
  [6.601066589355469, 46.0460718554722],
  [6.6089630126953125, 46.0365370783104],
  [6.6185760498046875, 46.018420689207964],
];

mapboxgl.accessToken = mapboxToken;

export const MyComposition = () => {
  const ref = useRef<HTMLDivElement>(null);
  const {delayRender, continueRender} = useDelayRender();

  const {width, height} = useVideoConfig();
  const [handle] = useState(() => delayRender('Loading map...'));
  const [map, setMap] = useState<Map | null>(null);

  useEffect(() => {
    const _map = new Map({
      container: ref.current!,
      zoom: 11.53,
      center: [6.5615, 46.0598],
      pitch: 65,
      bearing: 0,
      style: '⁠mapbox://styles/mapbox/standard',
      interactive: false,
      fadeDuration: 0,
    });

    _map.on('style.load', () => {
      // Hide all features from the Mapbox Standard style
      const hideFeatures = [
        'showRoadsAndTransit',
        'showRoads',
        'showTransit',
        'showPedestrianRoads',
        'showRoadLabels',
        'showTransitLabels',
        'showPlaceLabels',
        'showPointOfInterestLabels',
        'showPointsOfInterest',
        'showAdminBoundaries',
        'showLandmarkIcons',
        'showLandmarkIconLabels',
        'show3dObjects',
        'show3dBuildings',
        'show3dTrees',
        'show3dLandmarks',
        'show3dFacades',
      ];
      for (const feature of hideFeatures) {
        _map.setConfigProperty('basemap', feature, false);
      }

      _map.setConfigProperty('basemap', 'colorTrunks', 'rgba(0, 0, 0, 0)');

      _map.addSource('trace', {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'LineString',
            coordinates: lineCoordinates,
          },
        },
      });
      _map.addLayer({
        type: 'line',
        source: 'trace',
        id: 'line',
        paint: {
          'line-color': 'black',
          'line-width': 5,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });
    });

    _map.on('load', () => {
      continueRender(handle);
      setMap(_map);
    });
  }, [handle, lineCoordinates]);

  const style: React.CSSProperties = useMemo(() => ({width, height, position: 'absolute'}), [width, height]);

  return <AbsoluteFill ref={ref} style={style} />;
};
```

The following is important in Remotion:

- Animations must be driven by `useCurrentFrame()` and animations that Mapbox brings itself should be disabled. For example, the `fadeDuration` prop should be set to `0`, `interactive` should be set to `false`, etc.
- Loading the map should be delayed using `useDelayRender()` and the map should be set to `null` until it is loaded.
- The element containing the ref MUST have an explicit width and height and `position: "absolute"`.
- Do not add a `_map.remove();` cleanup function.

## Drawing lines

Unless I request it, do not add a glow effect to the lines.
Unless I request it, do not add additional points to the lines.

## Map style

By default, use the `mapbox://styles/mapbox/satellite-v9` style.  
Hide the labels from the base map style.

Unless I request otherwise, remove all features from the Mapbox Standard style.

```tsx
// Hide all features from the Mapbox Standard style
const hideFeatures = [
  'showRoadsAndTransit',
  'showRoads',
  'showTransit',
  'showPedestrianRoads',
  'showRoadLabels',
  'showTransitLabels',
  'showPlaceLabels',
  'showPointOfInterestLabels',
  'showPointsOfInterest',
  'showAdminBoundaries',
  'showLandmarkIcons',
  'showLandmarkIconLabels',
  'show3dObjects',
  'show3dBuildings',
  'show3dTrees',
  'show3dLandmarks',
  'show3dFacades',
];
for (const feature of hideFeatures) {
  _map.setConfigProperty('basemap', feature, false);
}

_map.setConfigProperty('basemap', 'colorMotorways', 'transparent');
_map.setConfigProperty('basemap', 'colorRoads', 'transparent');
_map.setConfigProperty('basemap', 'colorTrunks', 'transparent');
```

## Animating the camera

You can animate the camera along the line by adding a `useEffect` hook that updates the camera position based on the current frame.

Unless I ask for it, do not jump between camera angles.

```tsx
import * as turf from '@turf/turf';
import {interpolate} from 'remotion';
import {Easing} from 'remotion';
import {useCurrentFrame, useVideoConfig, useDelayRender} from 'remotion';

const animationDuration = 20;
const cameraAltitude = 4000;
```

```tsx
const frame = useCurrentFrame();
const {fps} = useVideoConfig();
const {delayRender, continueRender} = useDelayRender();

useEffect(() => {
  if (!map) {
    return;
  }
  const handle = delayRender('Moving point...');

  const routeDistance = turf.length(turf.lineString(lineCoordinates));

  const progress = interpolate(frame / fps, [0.00001, animationDuration], [0, 1], {
    easing: Easing.inOut(Easing.sin),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const camera = map.getFreeCameraOptions();

  const alongRoute = turf.along(turf.lineString(lineCoordinates), routeDistance * progress).geometry.coordinates;

  camera.lookAtPoint({
    lng: alongRoute[0],
    lat: alongRoute[1],
  });

  map.setFreeCameraOptions(camera);
  map.once('idle', () => continueRender(handle));
}, [lineCoordinates, fps, frame, handle, map]);
```

Notes:

IMPORTANT: Keep the camera by default so north is up.
IMPORTANT: For multi-step animations, set all properties at all stages (zoom, position, line progress) to prevent jumps. Override initial values.

- The progress is clamped to a minimum value to avoid the line being empty, which can lead to turf errors
- See [Timing](./timing.md) for more options for timing.
- Consider the dimensions of the composition and make the lines thick enough and the label font size large enough to be legible for when the composition is scaled down.

## Animating lines

### Straight lines (linear interpolation)

To animate a line that appears straight on the map, use linear interpolation between coordinates. Do NOT use turf's `lineSliceAlong` or `along` functions, as they use geodesic (great circle) calculations which appear curved on a Mercator projection.

```tsx
const frame = useCurrentFrame();
const {durationInFrames} = useVideoConfig();

useEffect(() => {
  if (!map) return;

  const animationHandle = delayRender('Animating line...');

  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });

  // Linear interpolation for a straight line on the map
  const start = lineCoordinates[0];
  const end = lineCoordinates[1];
  const currentLng = start[0] + (end[0] - start[0]) * progress;
  const currentLat = start[1] + (end[1] - start[1]) * progress;

  const lineData: GeoJSON.Feature<GeoJSON.LineString> = {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'LineString',
      coordinates: [start, [currentLng, currentLat]],
    },
  };

  const source = map.getSource('trace') as mapboxgl.GeoJSONSource;
  if (source) {
    source.setData(lineData);
  }

  map.once('idle', () => continueRender(animationHandle));
}, [frame, map, durationInFrames]);
```

### Curved lines (geodesic/great circle)

To animate a line that follows the geodesic (great circle) path between two points, use turf's `lineSliceAlong`. This is useful for showing flight paths or the actual shortest distance on Earth.

```tsx
import * as turf from '@turf/turf';

const routeLine = turf.lineString(lineCoordinates);
const routeDistance = turf.length(routeLine);

const currentDistance = Math.max(0.001, routeDistance * progress);
const slicedLine = turf.lineSliceAlong(routeLine, 0, currentDistance);

const source = map.getSource('route') as mapboxgl.GeoJSONSource;
if (source) {
  source.setData(slicedLine);
}
```

## Markers and Labels

Add labels and markers where appropriate. There are two approaches: **layer-based markers** (using GeoJSON source + circle/symbol layers) and **DOM markers** (using `mapboxgl.Marker`). Use layer-based markers by default for better rendering in Remotion. Use DOM markers when you need fully custom HTML content (icons, images, complex layouts).

### Layer-based markers (default approach)

```tsx
_map.addSource('markers', {
  type: 'geojson',
  data: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {name: 'Point 1'},
        geometry: {type: 'Point', coordinates: [-118.2437, 34.0522]},
      },
    ],
  },
});

_map.addLayer({
  id: 'city-markers',
  type: 'circle',
  source: 'markers',
  paint: {
    'circle-radius': 40,
    'circle-color': '#FF4444',
    'circle-stroke-width': 4,
    'circle-stroke-color': '#FFFFFF',
  },
});

_map.addLayer({
  id: 'labels',
  type: 'symbol',
  source: 'markers',
  layout: {
    'text-field': ['get', 'name'],
    'text-font': ['DIN Pro Bold', 'Arial Unicode MS Bold'],
    'text-size': 50,
    'text-offset': [0, 0.5],
    'text-anchor': 'top',
  },
  paint: {
    'text-color': '#FFFFFF',
    'text-halo-color': '#000000',
    'text-halo-width': 2,
  },
});
```

Make sure they are big enough. Check the composition dimensions and scale the labels accordingly.
For a composition size of 1920x1080, the label font size should be at least 40px.

IMPORTANT: Keep the `text-offset` small enough so it is close to the marker. Consider the marker circle radius. For a circle radius of 40, this is a good offset:

```tsx
"text-offset": [0, 0.5],
```

### DOM markers with `mapboxgl.Marker`

Use `mapboxgl.Marker` when you need custom HTML elements as markers (e.g., images, SVG icons, styled divs). These are real DOM elements placed on the map.

#### Default colored marker

```tsx
const marker = new mapboxgl.Marker({ color: '#FF0000', scale: 1.5 })
  .setLngLat([-74.006, 40.7128])
  .addTo(_map);
```

#### Custom HTML marker with label

```tsx
const el = document.createElement('div');
el.style.display = 'flex';
el.style.flexDirection = 'column';
el.style.alignItems = 'center';

// Marker dot
const dot = document.createElement('div');
dot.style.width = '24px';
dot.style.height = '24px';
dot.style.borderRadius = '50%';
dot.style.backgroundColor = '#FF4444';
dot.style.border = '3px solid #FFFFFF';
el.appendChild(dot);

// Label
const label = document.createElement('div');
label.textContent = 'New York';
label.style.color = '#FFFFFF';
label.style.fontSize = '32px';
label.style.fontWeight = 'bold';
label.style.textShadow = '0 0 6px rgba(0,0,0,0.8)';
label.style.marginTop = '4px';
label.style.whiteSpace = 'nowrap';
el.appendChild(label);

const marker = new mapboxgl.Marker({ element: el, anchor: 'top' })
  .setLngLat([-74.006, 40.7128])
  .addTo(_map);
```

#### Multiple DOM markers from data

```tsx
const cities = [
  { name: 'New York', coordinates: [-74.006, 40.7128] as [number, number] },
  { name: 'Los Angeles', coordinates: [-118.2437, 34.0522] as [number, number] },
  { name: 'London', coordinates: [-0.1276, 51.5074] as [number, number] },
];

const markers = cities.map((city) => {
  const el = document.createElement('div');
  el.style.display = 'flex';
  el.style.flexDirection = 'column';
  el.style.alignItems = 'center';

  const dot = document.createElement('div');
  dot.style.width = '20px';
  dot.style.height = '20px';
  dot.style.borderRadius = '50%';
  dot.style.backgroundColor = '#FF4444';
  dot.style.border = '3px solid white';
  el.appendChild(dot);

  const label = document.createElement('div');
  label.textContent = city.name;
  label.style.color = '#FFFFFF';
  label.style.fontSize = '28px';
  label.style.fontWeight = 'bold';
  label.style.textShadow = '0 0 6px rgba(0,0,0,0.8)';
  label.style.marginTop = '4px';
  label.style.whiteSpace = 'nowrap';
  el.appendChild(label);

  return new mapboxgl.Marker({ element: el, anchor: 'top' })
    .setLngLat(city.coordinates)
    .addTo(_map);
});
```

#### Marker options reference

| Option | Type | Description |
|--------|------|-------------|
| `color` | string | Color of the default marker pin |
| `scale` | number | Scale factor for the default marker (1 = default size) |
| `element` | HTMLElement | Custom DOM element to use instead of the default pin |
| `anchor` | string | Part of the marker that sits on the coordinate: `center`, `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `offset` | [number, number] | Pixel offset from the anchor position |
| `rotation` | number | Rotation angle in degrees |
| `draggable` | boolean | Whether the marker can be dragged (not useful in Remotion) |

IMPORTANT: DOM markers are real HTML elements. In Remotion, they render correctly but do NOT use `marker.setPopup()` — popups require user interaction which doesn't exist in video. Instead, include any label text directly in the marker's HTML element.

IMPORTANT: When removing DOM markers (e.g., for animated sequences), call `marker.remove()` to clean up the DOM element.

## Highlighting Countries

Use the free `mapbox://mapbox.country-boundaries-v1` tileset to highlight countries. The source-layer is `country_boundaries`.

```tsx
_map.on('style.load', () => {
  // Add the country boundaries source
  _map.addSource('country-boundaries', {
    type: 'vector',
    url: 'mapbox://mapbox.country-boundaries-v1',
  });

  // Highlight specific countries with a fill layer
  _map.addLayer(
    {
      id: 'country-fills',
      type: 'fill',
      source: 'country-boundaries',
      'source-layer': 'country_boundaries',
      paint: {
        'fill-color': '#d2361e',
        'fill-opacity': 0.4,
      },
      filter: [
        'all',
        // Worldview filter (required to avoid disputed boundary overlaps)
        ['==', ['get', 'disputed'], 'false'],
        ['any', ['==', 'all', ['get', 'worldview']], ['in', 'US', ['get', 'worldview']]],
        // Filter to specific countries by ISO 3166-1 Alpha-3 code
        ['in', ['get', 'iso_3166_1_alpha_3'], ['literal', ['USA', 'IND', 'BRA']]],
      ],
    },
    'country-label' // Place below labels
  );

  // Optional: add country outlines
  _map.addLayer(
    {
      id: 'country-outlines',
      type: 'line',
      source: 'country-boundaries',
      'source-layer': 'country_boundaries',
      paint: {
        'line-color': '#d2361e',
        'line-width': 2,
      },
      filter: [
        'all',
        ['==', ['get', 'disputed'], 'false'],
        ['any', ['==', 'all', ['get', 'worldview']], ['in', 'US', ['get', 'worldview']]],
        ['in', ['get', 'iso_3166_1_alpha_3'], ['literal', ['USA', 'IND', 'BRA']]],
      ],
    },
    'country-label'
  );
});
```

### Different colors per country

Use a `match` expression for per-country colors:

```tsx
_map.addLayer({
  id: 'country-fills',
  type: 'fill',
  source: 'country-boundaries',
  'source-layer': 'country_boundaries',
  paint: {
    'fill-color': [
      'match',
      ['get', 'iso_3166_1_alpha_3'],
      'USA', '#1f78b4',
      'IND', '#33a02c',
      'BRA', '#e31a1c',
      'rgba(0, 0, 0, 0)', // default: transparent
    ],
    'fill-opacity': 0.5,
  },
  filter: [
    'all',
    ['==', ['get', 'disputed'], 'false'],
    ['any', ['==', 'all', ['get', 'worldview']], ['in', 'US', ['get', 'worldview']]],
  ],
});
```

### Key properties for `country_boundaries` source-layer

| Property | Example | Description |
|----------|---------|-------------|
| `iso_3166_1` | "US", "IN" | ISO Alpha-2 code |
| `iso_3166_1_alpha_3` | "USA", "IND" | ISO Alpha-3 code |
| `name_en` | "United States" | English name |
| `worldview` | "all", "US" | Boundary perspective |
| `disputed` | "true"/"false" | Disputed territory flag |

IMPORTANT: Always include the worldview filter to avoid overlapping boundaries in disputed areas. Change `'US'` to `'IN'` for India's worldview, `'CN'` for China's, etc.

## Highlighting States / Provinces (Admin-1 Regions)

The free `country-boundaries-v1` tileset does NOT include states/provinces. Use GeoJSON for state-level highlighting.

### Using GeoJSON for US states

```tsx
_map.on('style.load', () => {
  // Add GeoJSON source with state boundaries
  _map.addSource('states', {
    type: 'geojson',
    data: 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json',
    generateId: true,
  });

  // Fill layer for states
  _map.addLayer(
    {
      id: 'state-fills',
      type: 'fill',
      source: 'states',
      paint: {
        'fill-color': '#627BC1',
        'fill-opacity': 0.5,
      },
    },
    'country-label'
  );

  // Outline layer for states
  _map.addLayer(
    {
      id: 'state-borders',
      type: 'line',
      source: 'states',
      paint: {
        'line-color': '#627BC1',
        'line-width': 2,
      },
    },
    'country-label'
  );
});
```

### Highlighting specific states by name

Filter by the `name` property in the GeoJSON:

```tsx
_map.addLayer({
  id: 'state-fills',
  type: 'fill',
  source: 'states',
  paint: {
    'fill-color': '#627BC1',
    'fill-opacity': 0.5,
  },
  filter: ['in', ['get', 'name'], ['literal', ['California', 'Texas', 'New York']]],
});
```

### Different colors per state

```tsx
_map.addLayer({
  id: 'state-fills',
  type: 'fill',
  source: 'states',
  paint: {
    'fill-color': [
      'match',
      ['get', 'name'],
      'California', '#FF6B6B',
      'Texas', '#4ECDC4',
      'New York', '#45B7D1',
      'rgba(0, 0, 0, 0)', // default: transparent
    ],
    'fill-opacity': 0.6,
  },
});
```

### Using inline GeoJSON for custom regions

For non-US states or custom regions, provide GeoJSON polygon coordinates directly:

```tsx
_map.addSource('custom-region', {
  type: 'geojson',
  data: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { name: 'Region A' },
        geometry: {
          type: 'Polygon',
          coordinates: [[[lng1, lat1], [lng2, lat2], [lng3, lat3], [lng1, lat1]]],
        },
      },
    ],
  },
});

_map.addLayer({
  id: 'custom-region-fill',
  type: 'fill',
  source: 'custom-region',
  paint: {
    'fill-color': '#FF4444',
    'fill-opacity': 0.4,
  },
});
```

### GeoJSON sources for other countries' states/provinces

For states/provinces of countries other than the US, use Natural Earth GeoJSON data. Download admin-1 boundaries from Natural Earth (ne_10m_admin_1_states_provinces) and host the GeoJSON file, or use a public CDN URL. The property names vary but commonly include `name`, `admin`, `iso_a2`, and `iso_3166_2`.

## Animating region highlights

Animate fill-opacity or fill-color over frames using `setPaintProperty`:

```tsx
useEffect(() => {
  if (!map) return;

  const animHandle = delayRender('Animating highlights...');

  const progress = interpolate(frame, [0, 60], [0, 0.6], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  map.setPaintProperty('state-fills', 'fill-opacity', progress);
  map.once('idle', () => continueRender(animHandle));
}, [frame, map]);
```

## 3D buildings

To enable 3D buildings, use the following code:

```tsx
_map.setConfigProperty('basemap', 'show3dObjects', true);
_map.setConfigProperty('basemap', 'show3dLandmarks', true);
_map.setConfigProperty('basemap', 'show3dBuildings', true);
```

## Map Projection (Shape of the Map)

Control the shape/projection of the map using the `projection` option. This determines how the 3D Earth is displayed on a 2D surface.

### Available projections

| Projection | Description | Best for |
|-----------|-------------|----------|
| `globe` | 3D sphere representation | World views, dramatic reveals, space-to-earth zooms |
| `mercator` | Standard web map (default) | Navigation, street-level, zoomed-in views |
| `naturalEarth` | Balanced shape/size, curved edges | Classic world map aesthetics |
| `equirectangular` | Rectangular, straight lat/lng lines | Data visualization overlays |

### Setting projection in the Map constructor

```tsx
const _map = new Map({
  container: ref.current!,
  projection: 'globe',
  style: 'mapbox://styles/mapbox/satellite-v9',
  interactive: false,
  fadeDuration: 0,
  // ...other options
});
```

### Setting projection at runtime

```tsx
map.setProjection('naturalEarth');
```

### Important notes on projections

- **Globe is best for world-level views**: When showing the whole Earth or large regions, `globe` gives the most visually impressive result. Switch to `mercator` when zooming in to street/city level.
- **3D terrain and Free Camera**: Only work with `globe` and `mercator` projections. Other projections do not support `getFreeCameraOptions()`.
- **Adaptive zoom**: `naturalEarth` and `equirectangular` automatically transition to Mercator at higher zoom levels.
- **Default**: Use `globe` projection by default unless the direction specifies otherwise or the scene is zoomed in to street/city level.

## Rendering

When rendering a map animation, make sure to render with the following flags:

```
npx remotion render --gl=angle --concurrency=1
```
