/* global React */

// Cartographic backdrop — muted parcels, contour lines, coordinate grid.
// Rendered as inline SVG so it scales cleanly and colors track tokens.
function LRMapBackdrop() {
  // Hand-designed parcel shapes — irregular to feel like real plots
  const parcels = [
    'M 40 120 L 220 90 L 260 180 L 210 260 L 60 240 Z',
    'M 220 90 L 380 70 L 420 160 L 260 180 Z',
    'M 380 70 L 540 95 L 560 210 L 420 160 Z',
    'M 540 95 L 700 80 L 740 180 L 560 210 Z',
    'M 700 80 L 860 110 L 880 220 L 740 180 Z',
    'M 860 110 L 1010 130 L 1040 240 L 880 220 Z',
    'M 1010 130 L 1160 150 L 1180 270 L 1040 240 Z',
    'M 1160 150 L 1300 170 L 1320 290 L 1180 270 Z',
    'M 1300 170 L 1440 190 L 1460 300 L 1320 290 Z',
    'M 260 180 L 420 160 L 450 280 L 290 300 Z',
    'M 420 160 L 560 210 L 580 310 L 450 280 Z',
    'M 560 210 L 740 180 L 760 310 L 580 310 Z',
    'M 740 180 L 880 220 L 900 330 L 760 310 Z',
    'M 880 220 L 1040 240 L 1060 360 L 900 330 Z',
    'M 1040 240 L 1180 270 L 1200 380 L 1060 360 Z',
    'M 1180 270 L 1320 290 L 1340 400 L 1200 380 Z',
    'M 1320 290 L 1460 300 L 1480 410 L 1340 400 Z',
    'M 60 240 L 210 260 L 290 300 L 260 400 L 90 380 Z',
    'M 290 300 L 450 280 L 470 410 L 310 430 Z',
    'M 450 280 L 580 310 L 600 430 L 470 410 Z',
    'M 580 310 L 760 310 L 780 430 L 600 430 Z',
    'M 760 310 L 900 330 L 920 450 L 780 430 Z',
    'M 900 330 L 1060 360 L 1080 470 L 920 450 Z',
    'M 1060 360 L 1200 380 L 1220 490 L 1080 470 Z',
    'M 1200 380 L 1340 400 L 1360 510 L 1220 490 Z',
    'M 1340 400 L 1480 410 L 1500 520 L 1360 510 Z',
    'M 90 380 L 260 400 L 310 430 L 280 550 L 110 520 Z',
    'M 310 430 L 470 410 L 490 540 L 330 560 Z',
    'M 470 410 L 600 430 L 620 560 L 490 540 Z',
    'M 600 430 L 780 430 L 800 560 L 620 560 Z',
    'M 780 430 L 920 450 L 940 580 L 800 560 Z',
    'M 920 450 L 1080 470 L 1100 600 L 940 580 Z',
    'M 1080 470 L 1220 490 L 1240 620 L 1100 600 Z',
    'M 1220 490 L 1360 510 L 1380 640 L 1240 620 Z',
    'M 1360 510 L 1500 520 L 1520 650 L 1380 640 Z',
    'M 110 520 L 280 550 L 330 560 L 300 680 L 130 650 Z',
    'M 330 560 L 490 540 L 510 680 L 350 700 Z',
    'M 490 540 L 620 560 L 640 690 L 510 680 Z',
    'M 620 560 L 800 560 L 820 690 L 640 690 Z',
    'M 800 560 L 940 580 L 960 710 L 820 690 Z',
  ];

  // A couple of "highlighted" plots — subtle brand fill
  const highlights = [5, 13, 21, 30];

  // River / boundary curve running diagonally
  const river =
    'M -50 180 C 180 140, 360 260, 580 220 S 940 320, 1180 260 S 1460 380, 1600 340';

  // Contour lines — concentric soft curves suggesting topography
  const contours = [
    'M 200 580 Q 420 520, 620 560 T 1080 600 T 1500 580',
    'M 160 620 Q 400 560, 620 600 T 1100 640 T 1540 620',
    'M 120 660 Q 380 600, 620 640 T 1120 680 T 1580 660',
  ];

  return (
    <svg
      viewBox="0 0 1600 760"
      preserveAspectRatio="xMidYMid slice"
      style={{
        position:'absolute', inset:0, width:'100%', height:'100%',
        zIndex:1, pointerEvents:'none',
      }}
      aria-hidden="true"
    >
      <defs>
        {/* Paper wash so the map sinks into the page */}
        <radialGradient id="lr-map-vignette" cx="50%" cy="45%" r="75%">
          <stop offset="0%"  stopColor="#FAFAF5" stopOpacity="0"/>
          <stop offset="65%" stopColor="#FAFAF5" stopOpacity="0.35"/>
          <stop offset="100%" stopColor="#FAFAF5" stopOpacity="0.92"/>
        </radialGradient>

        {/* Dotted pattern for the coordinate grid */}
        <pattern id="lr-grid-dots" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
          <circle cx="0.5" cy="0.5" r="0.6" fill="#B8B3A2" opacity="0.55"/>
        </pattern>

        {/* Hatch for highlighted parcels */}
        <pattern id="lr-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" stroke="#1F5130" strokeWidth="0.8" opacity="0.32"/>
        </pattern>
      </defs>

      {/* Coordinate dot grid */}
      <rect x="0" y="0" width="1600" height="760" fill="url(#lr-grid-dots)"/>

      {/* Contour topography */}
      <g fill="none" stroke="#B8B3A2" strokeWidth="0.7" opacity="0.55">
        {contours.map((d, i) => <path key={i} d={d}/>)}
      </g>

      {/* River / district boundary */}
      <path
        d={river}
        fill="none"
        stroke="#1D4E66"
        strokeWidth="1.2"
        strokeDasharray="1 0"
        opacity="0.35"
      />
      <path
        d={river}
        fill="none"
        stroke="#1D4E66"
        strokeWidth="6"
        opacity="0.05"
      />

      {/* Parcels */}
      <g>
        {parcels.map((d, i) => (
          <path
            key={i}
            d={d}
            fill={highlights.includes(i) ? 'url(#lr-hatch)' : 'transparent'}
            stroke="#85897F"
            strokeWidth={highlights.includes(i) ? 1.1 : 0.7}
            opacity={highlights.includes(i) ? 0.9 : 0.55}
          />
        ))}
      </g>

      {/* Coordinate tick labels — sparse, editorial */}
      <g fontFamily="IBM Plex Mono, monospace" fontSize="9" fill="#85897F" opacity="0.7">
        <text x="40"   y="30">51°30′12″N</text>
        <text x="40"   y="745">0°07′39″W</text>
        <text x="1460" y="30" textAnchor="end">EPSG:27700</text>
        <text x="1460" y="745" textAnchor="end">OSGB36 · TQ 30 80</text>
        <text x="800"  y="30" textAnchor="middle">SHEET · EW-144</text>
      </g>

      {/* Compass rose — small, upper right */}
      <g transform="translate(1360 110)" opacity="0.75">
        <circle r="28" fill="none" stroke="#85897F" strokeWidth="0.6"/>
        <circle r="20" fill="none" stroke="#85897F" strokeWidth="0.4"/>
        <path d="M 0 -26 L 4 0 L 0 26 L -4 0 Z" fill="#1F5130" opacity="0.8"/>
        <path d="M -26 0 L 0 4 L 26 0 L 0 -4 Z" fill="#85897F" opacity="0.6"/>
        <text x="0" y="-32" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="9" fill="#1F5130" fontWeight="600">N</text>
      </g>

      {/* Vignette overlay */}
      <rect x="0" y="0" width="1600" height="760" fill="url(#lr-map-vignette)"/>
    </svg>
  );
}

window.LRMapBackdrop = LRMapBackdrop;
