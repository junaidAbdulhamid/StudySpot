import { TextStyle } from "react-native";
export const typography = {
  hero: {
    fontSize: 42,
    fontWeight: "700",
    letterSpacing: -1.6,
    lineHeight: 48,
  },
  title: {
    fontSize: 30,
    fontWeight: "700",
    letterSpacing: -0.8,
    lineHeight: 36,
  },
  heading: {
    fontSize: 21,
    fontWeight: "600",
    letterSpacing: -0.4,
    lineHeight: 28,
  },
  body: { fontSize: 15, lineHeight: 23 },
  caption: { fontSize: 12, lineHeight: 18 },
  label: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1.8,
    lineHeight: 17,
  },
} satisfies Record<string, TextStyle>;
