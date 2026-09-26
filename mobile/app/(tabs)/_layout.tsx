import { Tabs } from "expo-router";
import { Icon, IconName } from "../../components/common";
import { colors } from "../../theme";
const tabs: { name: string; title: string; icon: IconName }[] = [
  { name: "index", title: "Home", icon: "home-outline" },
  { name: "explore", title: "Explore", icon: "compass-outline" },
  { name: "map", title: "Map", icon: "map-outline" },
  { name: "alerts", title: "Alerts", icon: "notifications-outline" },
  { name: "profile", title: "Profile", icon: "person-outline" },
];
export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.background,
          borderTopColor: colors.border,
        },
        tabBarLabelStyle: { fontSize: 10, fontWeight: "600" },
        sceneStyle: { backgroundColor: colors.background },
      }}
    >
      {tabs.map((t) => (
        <Tabs.Screen
          key={t.name}
          name={t.name}
          options={{
            title: t.title,
            tabBarIcon: ({ color }) => <Icon name={t.icon} color={color} />,
          }}
        />
      ))}
    </Tabs>
  );
}
