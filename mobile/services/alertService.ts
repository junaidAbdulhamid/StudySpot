import { Alert } from "../types";
export const alertService = {
  async getAlerts(): Promise<Alert[]> {
    return [
      {
        id: "alert-1",
        locationId: "zone-1",
        title: "Your quiet corner is clearing up",
        message:
          "Fenwick Library · Floor 4 dropped to 28%. A good time to settle in.",
        timestamp: "3 min ago",
        percent: 28,
      },
      {
        id: "alert-2",
        locationId: "zone-10",
        title: "SUB I is getting busy",
        message: "Occupancy is now 78%. Explore a quieter spot nearby.",
        timestamp: "18 min ago",
        percent: 78,
      },
      {
        id: "alert-3",
        locationId: "zone-6",
        title: "Room for your next big idea",
        message: "Horizon Hall · Floor 2 has plenty of open seats.",
        timestamp: "42 min ago",
        percent: 32,
      },
    ];
  },
};
