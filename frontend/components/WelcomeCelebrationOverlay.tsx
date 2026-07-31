"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import type { InAppNotificationResponse, UiUser } from "@/lib/api/contracts";

const CELEBRATION_STORAGE_PREFIX = "violyt:welcome-celebration-shown";
const WELCOME_TITLE = "welcome to violyt";
const ELIGIBLE_ROLES = new Set(["TENANT_ADMIN", "TENANT_USER", "BRAND_USER"]);
const AUTO_DISMISS_MS = 10000;
const EXIT_ANIMATION_MS = 360;

type WelcomeCelebrationOverlayProps = {
  user: UiUser;
};

type WindowWithWebkitAudio = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

function storageKeyFor(userId: string) {
  return `${CELEBRATION_STORAGE_PREFIX}:${userId}`;
}

function hasStoredCelebration(userId: string) {
  if (typeof window === "undefined") {
    return true;
  }
  return window.localStorage.getItem(storageKeyFor(userId)) === "true";
}

function storeCelebrationShown(userId: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKeyFor(userId), "true");
}

function isWelcomeNotification(notification: InAppNotificationResponse) {
  return notification.unread && notification.title.toLowerCase().includes(WELCOME_TITLE);
}

function playWelcomeSound(enabled: boolean) {
  if (!enabled || typeof window === "undefined") {
    return;
  }

  try {
    const AudioContextConstructor = window.AudioContext ?? (window as WindowWithWebkitAudio).webkitAudioContext;
    if (!AudioContextConstructor) {
      return;
    }

    const audioContext = new AudioContextConstructor();
    if (audioContext.state !== "running") {
      void audioContext.resume();
    }

    const notes = [523.25, 659.25, 783.99];
    const now = audioContext.currentTime;
    notes.forEach((frequency, index) => {
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      const start = now + index * 0.11;
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, start);
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.06, start + 0.025);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.22);
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start(start);
      oscillator.stop(start + 0.24);
      oscillator.onended = () => {
        oscillator.disconnect();
        gain.disconnect();
        if (index === notes.length - 1) {
          void audioContext.close();
        }
      };
    });
  } catch {
    // Celebration sound should never interrupt the application.
  }
}

export function WelcomeCelebrationOverlay({ user }: WelcomeCelebrationOverlayProps) {
  const [visible, setVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [storageChecked, setStorageChecked] = useState(false);
  const [alreadyShown, setAlreadyShown] = useState(true);
  const isEligibleRole = ELIGIBLE_ROLES.has(user.role);

  useEffect(() => {
    setAlreadyShown(hasStoredCelebration(user.id));
    setStorageChecked(true);
  }, [user.id]);

  const shouldCheckNotifications = storageChecked && isEligibleRole && !alreadyShown;
  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications", user.id, "welcome-celebration"],
    enabled: shouldCheckNotifications,
    queryFn: () => request(API.NOTIFICATIONS.LIST),
    staleTime: 0,
  });

  const welcomeNotification = useMemo(
    () => notifications.find(isWelcomeNotification),
    [notifications],
  );

  useEffect(() => {
    if (!welcomeNotification || visible || alreadyShown) {
      return;
    }

    storeCelebrationShown(user.id);
    setAlreadyShown(true);
    setIsExiting(false);
    setVisible(true);
    playWelcomeSound(user.notificationsEnabled !== false);
  }, [alreadyShown, user.id, user.notificationsEnabled, visible, welcomeNotification]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    let removeTimeout: number | undefined;
    const exitTimeout = window.setTimeout(() => {
      setIsExiting(true);
      removeTimeout = window.setTimeout(() => {
        setVisible(false);
        setIsExiting(false);
      }, EXIT_ANIMATION_MS);
    }, AUTO_DISMISS_MS);

    return () => {
      window.clearTimeout(exitTimeout);
      if (removeTimeout) {
        window.clearTimeout(removeTimeout);
      }
    };
  }, [visible]);

  if (!visible) {
    return null;
  }

  return (
    <div className="welcome-celebration-overlay" data-exiting={isExiting} role="dialog" aria-modal="true" aria-labelledby="welcome-celebration-title">
      <div className="welcome-celebration-backdrop" />
      <div className="welcome-sparkles" aria-hidden="true" />
      <div className="welcome-firework welcome-firework-a" aria-hidden="true" />
      <div className="welcome-firework welcome-firework-b" aria-hidden="true" />
      <div className="welcome-firework welcome-firework-c" aria-hidden="true" />
      <div className="welcome-firework welcome-firework-d" aria-hidden="true" />
      <div className="welcome-card">
        <div className="welcome-card-icon" aria-hidden="true">{"\uD83C\uDF89"}</div>
        <h1 id="welcome-celebration-title" className="welcome-card-title">Welcome to Violyt!</h1>
        <p className="welcome-card-message">
          Your account has been activated successfully.
          <br />
          We're excited to have you as part of the Violyt community.
          <br />
          Let's start creating amazing content together!
        </p>
        <Button
          type="button"
          onClick={() => setVisible(false)}
          className="mt-6 h-11 rounded-none bg-primary px-8 text-base font-semibold text-white hover:bg-primary/90"
        >
          Continue
        </Button>
      </div>
    </div>
  );
}