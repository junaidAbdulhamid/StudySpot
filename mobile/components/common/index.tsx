import { useApp } from "../../store/AppStore";
import React from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  ViewStyle,
  StyleProp,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Ionicons from "@expo/vector-icons/Ionicons";
import { router } from "expo-router";
import {
  colors as c,
  radius as r,
  spacing as s,
  typography as t,
} from "../../theme";
export type IconName = React.ComponentProps<typeof Ionicons>["name"];
export function Icon({
  name,
  size = 22,
  color = c.textPrimary,
}: {
  name: IconName;
  size?: number;
  color?: import("react-native").ColorValue;
}) {
  return (
    <Ionicons
      name={name}
      size={size}
      color={color}
      accessible={false}
      aria-hidden={true}
    />
  );
}
export function Copy({
  children,
  variant = "body",
  muted = false,
  color,
  style,
}: React.PropsWithChildren<{
  variant?: keyof typeof t;
  muted?: boolean;
  color?: string;
  style?: StyleProp<import("react-native").TextStyle>;
}>) {
  return (
    <Text
      style={[
        t[variant],
        { color: color ?? (muted ? c.textSecondary : c.textPrimary) },
        style,
      ]}
    >
      {children}
    </Text>
  );
}
export function Screen({
  children,
  scroll = true,
}: React.PropsWithChildren<{ scroll?: boolean }>) {
  const { mutationError, clearMutationError } = useApp();
  const notice = mutationError ? (
    <View
      accessibilityRole="alert"
      style={{ padding: s.md, backgroundColor: c.surfaceElevated }}
    >
      <Copy color={c.warning}>{mutationError}</Copy>
      <Chip label="Dismiss" onPress={clearMutationError} />
    </View>
  ) : null;
  return (
    <SafeAreaView edges={["top", "left", "right"]} style={styles.screen}>
      {notice}
      {scroll ? (
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.content}
        >
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.content, { flex: 1, paddingBottom: 0 }]}>
          {children}
        </View>
      )}
    </SafeAreaView>
  );
}
export function Button({
  label,
  onPress,
  secondary = false,
  icon,
  disabled = false,
  loading = false,
}: {
  label: string;
  onPress: () => void;
  secondary?: boolean;
  icon?: IconName;
  disabled?: boolean;
  loading?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: disabled || loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: secondary ? c.surfaceElevated : c.primary,
          opacity: disabled ? 0.45 : pressed ? 0.8 : 1,
          transform: [{ scale: pressed ? 0.98 : 1 }],
        },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={secondary ? c.primary : c.background} />
      ) : icon ? (
        <Icon name={icon} color={secondary ? c.primary : c.background} />
      ) : null}
      <Copy
        style={{ fontWeight: "700" }}
        color={secondary ? c.textPrimary : c.background}
      >
        {label}
      </Copy>
    </Pressable>
  );
}
export function IconButton({
  icon,
  label,
  onPress,
  active = false,
}: {
  icon: IconName;
  label: string;
  onPress: () => void;
  active?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.iconButton,
        { opacity: pressed ? 0.65 : 1 },
      ]}
    >
      <Icon name={icon} color={active ? c.primary : c.textPrimary} />
    </Pressable>
  );
}
export function Card({
  children,
  style,
}: React.PropsWithChildren<{ style?: StyleProp<ViewStyle> }>) {
  return <View style={[styles.card, style]}>{children}</View>;
}
export function Chip({
  label,
  selected = false,
  onPress,
  icon,
}: {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  icon?: IconName;
}) {
  const contents = (
    <>
      {icon && (
        <Icon
          name={icon}
          size={16}
          color={selected ? c.primary : c.textSecondary}
        />
      )}
      <Copy
        variant="caption"
        color={selected ? c.primary : c.textSecondary}
        style={{ fontWeight: "600" }}
      >
        {label}
      </Copy>
    </>
  );
  return onPress ? (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        selected && styles.selected,
        { opacity: pressed ? 0.7 : 1 },
      ]}
    >
      {contents}
    </Pressable>
  ) : (
    <View style={[styles.chip, selected && styles.selected]}>{contents}</View>
  );
}
export const FilterChip = Chip;
export function TextField({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry = false,
  autoCapitalize = "none",
  keyboardType = "default",
  returnKeyType,
  onSubmitEditing,
  error,
}: {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  keyboardType?: "default" | "email-address";
  returnKeyType?: "done" | "next" | "go";
  onSubmitEditing?: () => void;
  error?: string;
}) {
  const [masked, setMasked] = React.useState(secureTextEntry);
  return (
    <View style={{ gap: s.xs }}>
      <Copy variant="caption" muted>
        {label}
      </Copy>
      <View style={[styles.search, error ? { borderColor: c.danger } : null]}>
        <TextInput
          accessibilityLabel={label}
          placeholder={placeholder}
          placeholderTextColor={c.textMuted}
          value={value}
          onChangeText={onChangeText}
          secureTextEntry={masked}
          autoCapitalize={autoCapitalize}
          autoCorrect={false}
          keyboardType={keyboardType}
          returnKeyType={returnKeyType}
          onSubmitEditing={onSubmitEditing}
          style={styles.input}
        />
        {secureTextEntry && (
          <IconButton
            icon={masked ? "eye-outline" : "eye-off-outline"}
            label={
              masked
                ? `Show ${label.toLowerCase()}`
                : `Hide ${label.toLowerCase()}`
            }
            onPress={() => setMasked((value) => !value)}
          />
        )}
      </View>
      {error && (
        <Copy color={c.danger} variant="caption">
          {error}
        </Copy>
      )}
    </View>
  );
}
export function SearchBar({
  value,
  onChangeText,
  placeholder = "Where do you want to study?",
  onSubmit,
}: {
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  onSubmit?: () => void;
}) {
  return (
    <View style={styles.search}>
      <Icon name="search-outline" color={c.textMuted} />
      <TextInput
        accessibilityLabel={placeholder}
        placeholder={placeholder}
        value={value}
        onChangeText={onChangeText}
        placeholderTextColor={c.textMuted}
        style={styles.input}
        autoCapitalize="none"
        returnKeyType="search"
        onSubmitEditing={onSubmit}
      />
      {value.length > 0 && (
        <IconButton
          icon="close"
          label="Clear search"
          onPress={() => onChangeText("")}
        />
      )}
    </View>
  );
}
export function SectionHeader({
  title,
  action,
  onPress,
}: {
  title: string;
  action?: string;
  onPress?: () => void;
}) {
  return (
    <View style={styles.section}>
      <Copy variant="heading">{title}</Copy>
      {action && (
        <Pressable
          accessibilityRole="button"
          onPress={onPress}
          style={{ minHeight: 44, justifyContent: "center" }}
        >
          <Copy variant="caption" color={c.primary}>
            {action} ↗
          </Copy>
        </Pressable>
      )}
    </View>
  );
}
export function ScreenHeader({
  title,
  subtitle,
  back = false,
  right,
}: {
  title: string;
  subtitle?: string;
  back?: boolean;
  right?: React.ReactNode;
}) {
  return (
    <View style={{ gap: s.md, marginBottom: s.xl }}>
      {back && (
        <View style={styles.row}>
          <IconButton
            icon="arrow-back"
            label="Go back"
            onPress={() =>
              router.canGoBack() ? router.back() : router.replace("/(tabs)")
            }
          />
          <View style={{ flex: 1 }} />
          {right}
        </View>
      )}
      <View style={styles.row}>
        <View style={{ flex: 1, gap: s.xs }}>
          <Copy variant="title">{title}</Copy>
          {subtitle && <Copy muted>{subtitle}</Copy>}
        </View>
        {!back && right}
      </View>
    </View>
  );
}
export function EmptyState({
  title = "Nothing here yet",
  message,
  icon = "leaf-outline",
  action,
  onAction,
}: {
  title?: string;
  message: string;
  icon?: IconName;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <Card
      style={{ alignItems: "center", paddingVertical: s["2xl"], gap: s.lg }}
    >
      <Icon name={icon} size={38} color={c.primary} />
      <Copy variant="heading">{title}</Copy>
      <Copy muted style={{ textAlign: "center" }}>
        {message}
      </Copy>
      {action && onAction && (
        <Button label={action} onPress={onAction} secondary />
      )}
    </Card>
  );
}
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <EmptyState
      title="A little interruption"
      message={message}
      icon="cloud-offline-outline"
      action="Try again"
      onAction={onRetry}
    />
  );
}
export function LoadingSkeleton() {
  return (
    <View
      accessibilityLabel="Loading study spaces"
      style={{ gap: s.lg, paddingVertical: s.xl }}
    >
      <ActivityIndicator color={c.primary} />
      {[1, 2, 3].map((i) => (
        <View
          key={i}
          style={{
            height: 120,
            borderRadius: r.lg,
            backgroundColor: c.surfaceElevated,
          }}
        />
      ))}
    </View>
  );
}
export function Divider() {
  return (
    <View
      style={{ height: 1, backgroundColor: c.border, marginVertical: s.lg }}
    />
  );
}
export function Avatar({ name = "Alex" }: { name?: string }) {
  return (
    <View accessibilityLabel={`${name}'s avatar`} style={styles.avatar}>
      <Copy color={c.primary} style={{ fontSize: 20, fontWeight: "700" }}>
        {name.slice(0, 1)}
      </Copy>
    </View>
  );
}
export function DemoNote({
  text = "Database seed data · not live",
}: {
  text?: string;
}) {
  return (
    <Copy variant="caption" muted style={{ marginVertical: s.md }}>
      {text}
    </Copy>
  );
}
export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: c.background },
  content: {
    padding: s.xl,
    paddingBottom: s["3xl"],
    width: "100%",
    maxWidth: 760,
    alignSelf: "center",
  },
  row: { flexDirection: "row", alignItems: "center", gap: s.md },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: s.sm },
  card: {
    backgroundColor: c.surface,
    borderColor: c.border,
    borderWidth: 1,
    borderRadius: r.lg,
    padding: s.lg,
    gap: s.md,
  },
  button: {
    minHeight: 54,
    borderRadius: r.md,
    paddingHorizontal: s.xl,
    paddingVertical: s.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: s.sm,
  },
  iconButton: {
    width: 44,
    height: 44,
    borderRadius: r.pill,
    backgroundColor: c.surfaceElevated,
    alignItems: "center",
    justifyContent: "center",
  },
  chip: {
    minHeight: 44,
    borderRadius: r.pill,
    paddingHorizontal: s.lg,
    paddingVertical: s.sm,
    backgroundColor: c.surface,
    flexDirection: "row",
    gap: s.sm,
    alignItems: "center",
    borderWidth: 1,
    borderColor: c.border,
  },
  selected: { backgroundColor: c.surfaceElevated, borderColor: c.primary },
  search: {
    minHeight: 56,
    borderRadius: r.md,
    backgroundColor: c.surface,
    borderWidth: 1,
    borderColor: c.border,
    paddingHorizontal: s.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: s.sm,
  },
  input: { flex: 1, color: c.textPrimary, fontSize: 14, minHeight: 54 },
  section: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: s["2xl"],
    marginBottom: s.lg,
    gap: s.sm,
  },
  avatar: {
    height: 48,
    width: 48,
    borderRadius: r.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: c.surfaceElevated,
    borderWidth: 1,
    borderColor: c.border,
  },
});
