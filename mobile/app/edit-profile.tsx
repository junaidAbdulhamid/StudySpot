import { useState } from "react";
import { router } from "expo-router";
import {
  Button,
  Card,
  Screen,
  ScreenHeader,
  TextField,
} from "../components/common";
import { useApp } from "../store/AppStore";
export default function EditProfile() {
  const { user, updateProfile } = useApp();
  const [name, setName] = useState(user.name);
  const [busy, setBusy] = useState(false);
  const save = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      if (await updateProfile(name.trim())) router.back();
    } finally {
      setBusy(false);
    }
  };
  return (
    <Screen>
      <ScreenHeader title="Edit profile." back />
      <Card>
        <TextField
          label="Display name"
          value={name}
          onChangeText={setName}
          placeholder="Your name"
          returnKeyType="go"
          onSubmitEditing={() => void save()}
        />
        <Button
          label="Save"
          onPress={() => void save()}
          disabled={busy || !name.trim()}
          loading={busy}
        />
      </Card>
    </Screen>
  );
}
