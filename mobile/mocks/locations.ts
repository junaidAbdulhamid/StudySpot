import { Amenity, Campus, StudyLocation } from "../types";
export const campus: Campus = {
  id: "gmu-fairfax",
  name: "George Mason University",
  latitude: 38.8303,
  longitude: -77.3075,
};
export const amenities: Amenity[] = [
  "Outlets",
  "Whiteboards",
  "Large tables",
  "Food nearby",
  "Printers",
  "Natural light",
  "Group rooms",
];
const zones: [
  string,
  string,
  number,
  StudyLocation["noiseLevel"],
  number,
  Amenity[],
][] = [
  [
    "Fenwick Library",
    "Floor 4",
    28,
    "quiet",
    7,
    ["Outlets", "Natural light", "Printers"],
  ],
  [
    "Fenwick Library",
    "Floor 1",
    72,
    "social",
    7,
    ["Outlets", "Large tables", "Food nearby", "Printers"],
  ],
  [
    "Fenwick Library",
    "Floor 2",
    53,
    "moderate",
    7,
    ["Outlets", "Whiteboards", "Group rooms", "Printers"],
  ],
  [
    "Fenwick Library",
    "Floor 3",
    36,
    "quiet",
    7,
    ["Outlets", "Large tables", "Natural light"],
  ],
  [
    "Horizon Hall",
    "Floor 1",
    46,
    "moderate",
    4,
    ["Outlets", "Large tables", "Food nearby", "Natural light"],
  ],
  [
    "Horizon Hall",
    "Floor 2",
    32,
    "quiet",
    4,
    ["Outlets", "Whiteboards", "Natural light", "Group rooms"],
  ],
  [
    "Johnson Center",
    "Floor 1",
    89,
    "social",
    3,
    ["Food nearby", "Large tables", "Outlets"],
  ],
  [
    "Johnson Center",
    "Floor 2",
    62,
    "moderate",
    3,
    ["Outlets", "Printers", "Large tables"],
  ],
  [
    "Johnson Center",
    "Floor 3",
    41,
    "quiet",
    3,
    ["Outlets", "Natural light", "Group rooms"],
  ],
  [
    "SUB I",
    "Student lounge",
    78,
    "social",
    6,
    ["Food nearby", "Large tables", "Outlets"],
  ],
  [
    "Peterson Hall",
    "Floor 1",
    22,
    "quiet",
    12,
    ["Outlets", "Whiteboards", "Natural light", "Large tables"],
  ],
  [
    "Peterson Hall",
    "Floor 2",
    18,
    "quiet",
    12,
    ["Outlets", "Group rooms", "Whiteboards"],
  ],
];
export const mockLocations: StudyLocation[] = zones.map(
  (
    [name, floor, currentOccupancy, noiseLevel, walkingMinutes, amenities],
    i,
  ) => ({
    id: `zone-${i + 1}`,
    name,
    building: name,
    floor,
    currentOccupancy,
    noiseLevel,
    walkingMinutes,
    amenities,
    latitude: 38.8303 + (Math.floor(i / 2) - 2) * 0.0007,
    longitude: -77.3075 + ((i % 3) - 1) * 0.001,
    capacity: 40 + i * 8,
    occupancyConfidence: i % 4 === 0 ? "high" : "medium",
    isFavorite: i === 0 || i === 5,
    image: name.includes("Library")
      ? "library"
      : name.includes("Johnson") || name === "SUB I"
        ? "commons"
        : "hall",
    description:
      noiseLevel === "quiet"
        ? "A calm corner of campus with comfortable desks and room to focus. Settle in, find your rhythm, and make progress on what matters."
        : "An inviting shared space for exchanging ideas, catching up on coursework, and studying with friends between classes.",
    hours: {
      open: "07:00",
      close: name.includes("Library") ? "00:00" : "22:00",
    },
    predictions: [0, 1, 2, 3, 4].map((hoursAhead) => ({
      hoursAhead,
      label: hoursAhead === 0 ? "Now" : `+${hoursAhead}h`,
      percent: Math.min(
        98,
        Math.max(8, currentOccupancy + [0, 11, 33, 51, 39][hoursAhead]!),
      ),
    })),
    historical: [18, 26, 42, 67, 78, 65, 44, 23],
  }),
);
