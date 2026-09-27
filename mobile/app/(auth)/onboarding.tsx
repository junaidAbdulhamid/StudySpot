import { useAuth } from "../../store/AuthProvider";
import { useState } from "react";
import { ImageBackground, View } from "react-native";
import Animated, { FadeIn, ReduceMotion } from "react-native-reanimated";
import { router } from "expo-router";
import {
  Button,
  Copy,
  Icon,
  Screen,
  styles,
  Chip,
} from "../../components/common";
import { colors as c, spacing as s, radius as r } from "../../theme";
const slides = [
  {
    eyebrow: "LESS SEARCHING. MORE FOCUS.",
    title: "Find your perfect place to study.",
    body: "Your campus. Your kind of quiet. Discover a space that helps you do your best work.",
    icon: "leaf-outline" as const,
    benefit: "Live crowd updates",
  },
  {
    eyebrow: "A LITTLE FORESIGHT GOES A LONG WAY.",
    title: "Know before you go.",
    body: "See crowd levels and look ahead. Make room for a productive afternoon, without the guesswork.",
    icon: "pulse-outline" as const,
    benefit: "ML-powered predictions",
  },
  {
    eyebrow: "MAKE YOURSELF AT HOME.",
    title: "Built around how you study.",
    body: "Solo deep work or your next group project. Find a spot that feels just right for you.",
    icon: "sparkles-outline" as const,
    benefit: "Personalized recommendations",
  },
];
export default function Onboarding() {
  const { finishIntro } = useAuth();
  const finish = async () => {
    await finishIntro();
    router.replace("/(auth)/login");
  };
  const [index, setIndex] = useState(0);
  const slide = slides[index]!;
  return (
    <Screen>
      <View
        style={[
          styles.row,
          { justifyContent: "space-between", marginBottom: s.xl },
        ]}
      >
        <View style={styles.row}>
          <Icon name="leaf" color={c.primary} />
          <Copy variant="heading">studyspot</Copy>
        </View>
        <Chip label="Skip" onPress={() => void finish()} />
      </View>
      <Animated.View
        key={index}
        entering={FadeIn.duration(350).reduceMotion(ReduceMotion.System)}
      >
        <View
          style={{
            borderRadius: r.xl,
            overflow: "hidden",
            marginBottom: s["2xl"],
          }}
        >
          <ImageBackground
            source={require("../../assets/library.jpg")}
            style={{ height: 280 }}
          >
            <View
              style={{
                flex: 1,
                backgroundColor: c.scrim,
                padding: s.xl,
                justifyContent: "space-between",
              }}
            >
              <Chip label="MADE FOR MASON" icon="school-outline" />
              <View style={[styles.card, { backgroundColor: c.background }]}>
                <View style={styles.row}>
                  <Icon name={slide.icon} color={c.primary} />
                  <Copy>{slide.benefit}</Copy>
                </View>
                <Copy muted variant="caption">
                  Your next great study session starts here.
                </Copy>
              </View>
            </View>
          </ImageBackground>
        </View>
        <Copy variant="label" color={c.primary}>
          {slide.eyebrow}
        </Copy>
        <Copy variant="hero" style={{ marginVertical: s.lg }}>
          {slide.title}
        </Copy>
        <Copy muted>{slide.body}</Copy>
      </Animated.View>
      <View style={[styles.row, { marginVertical: s["2xl"] }]}>
        {slides.map((_, i) => (
          <View
            key={i}
            style={{
              height: 5,
              width: i === index ? 32 : 8,
              borderRadius: r.pill,
              backgroundColor: i === index ? c.primary : c.border,
            }}
          />
        ))}
      </View>
      <Button
        label={index === 2 ? "Get Started" : "Continue"}
        icon="arrow-forward"
        onPress={() => (index < 2 ? setIndex(index + 1) : void finish())}
      />
      <Copy
        muted
        variant="caption"
        style={{ textAlign: "center", marginTop: s.lg }}
      >
        A little less wandering. A lot more focus.
      </Copy>
    </Screen>
  );
}
