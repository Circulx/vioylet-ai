"use client";

import { useEffect, useRef } from "react";

type WindowWithWebkitAudio = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

let sharedAudioContext: AudioContext | null = null;
let unlockListenersRegistered = false;

function getAudioContext() {
  if (typeof window === "undefined") {
    return null;
  }

  const AudioContextConstructor = window.AudioContext ?? (window as WindowWithWebkitAudio).webkitAudioContext;
  if (!AudioContextConstructor) {
    return null;
  }

  sharedAudioContext ??= new AudioContextConstructor();
  return sharedAudioContext;
}

async function unlockNotificationAudio() {
  const audioContext = getAudioContext();
  if (!audioContext || audioContext.state !== "suspended") {
    return;
  }

  try {
    await audioContext.resume();
  } catch {
    // Browser audio policies can reject until the next direct user gesture.
  }
}

async function playNotificationSound() {
  const audioContext = getAudioContext();
  if (!audioContext) {
    return;
  }

  try {
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }
    if (audioContext.state !== "running") {
      return;
    }

    const now = audioContext.currentTime;
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();

    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(880, now);
    oscillator.frequency.setValueAtTime(660, now + 0.08);

    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.08, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);

    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start(now);
    oscillator.stop(now + 0.22);

    oscillator.onended = () => {
      oscillator.disconnect();
      gain.disconnect();
    };
  } catch {
    // Notification sound should never break the notification UI.
  }
}

export function useNotificationSound(unreadCount: number, enabled = true, ready = true) {
  const previousUnreadCountRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || typeof window === "undefined" || unlockListenersRegistered) {
      return;
    }

    unlockListenersRegistered = true;
    const unlock = () => void unlockNotificationAudio();
    window.addEventListener("pointerdown", unlock, { passive: true });
    window.addEventListener("keydown", unlock);
    window.addEventListener("touchstart", unlock, { passive: true });

    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      window.removeEventListener("touchstart", unlock);
      unlockListenersRegistered = false;
    };
  }, [enabled]);

  useEffect(() => {
    if (!ready) {
      previousUnreadCountRef.current = null;
      return;
    }

    if (!enabled) {
      previousUnreadCountRef.current = unreadCount;
      return;
    }

    const previousUnreadCount = previousUnreadCountRef.current;
    previousUnreadCountRef.current = unreadCount;

    if (previousUnreadCount === null || unreadCount <= previousUnreadCount) {
      return;
    }

    void playNotificationSound();
  }, [enabled, ready, unreadCount]);
}


